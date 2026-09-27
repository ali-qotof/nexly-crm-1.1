"""
القاعدة 8: Dashboard سريع، لا يحمّل كل العملاء إلى المتصفح — كل شيء هنا Aggregated SQL
(COUNT/SUM/GROUP BY) يُنفَّذ في قاعدة البيانات، ولا يُرجع صفوفًا خامة للعميل غير المطلوبة.

اصطلاح موثّق: "العملاء الذين يحتاجون إعادة محاولة" (القاعدة 8) يُحتسب هنا كعملاء آخر تفاعل لهم
بكود حالة 'retry_call' — وهو الكود الذي يُتوقع أن يُنشئه المدير ضمن status_configurations
لحالة "إعادة محاولة الاتصال" (القاعدة 11 تسرد هذه الحالة صراحة). إذا اختار المدير كودًا مختلفًا
لهذه الحالة، يجب تحديث هذا الثابت — هذا قيد بسيط موثّق، وليس منطقًا مخفيًا.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerAssignment, FollowUp, Interaction, Order, User
from app.models.enums import OrderStatus, UserRole

RETRY_STATUS_CODE = "retry_call"


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min, tzinfo=timezone.utc)
    end = datetime.combine(d, time.max, tzinfo=timezone.utc)
    return start, end


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def manager_dashboard(self, date_from: date | None, date_to: date | None) -> dict:
        now = datetime.now(timezone.utc)
        today_start, today_end = _day_bounds(now.date())
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        period_start = datetime.combine(date_from, time.min, tzinfo=timezone.utc) if date_from else None
        period_end = datetime.combine(date_to, time.max, tzinfo=timezone.utc) if date_to else None

        total_customers = self.db.execute(
            select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
        ).scalar_one()

        assigned_customers = self.db.execute(
            select(func.count(func.distinct(CustomerAssignment.customer_id))).where(
                CustomerAssignment.is_active.is_(True)
            )
        ).scalar_one()

        unassigned_customers = total_customers - assigned_customers

        total_employees = self.db.execute(
            select(func.count(User.id)).where(User.role == UserRole.EMPLOYEE, User.deleted_at.is_(None))
        ).scalar_one()

        orders_today = self.db.execute(
            select(func.count(Order.id)).where(Order.created_at.between(today_start, today_end))
        ).scalar_one()

        orders_this_week = self.db.execute(
            select(func.count(Order.id)).where(Order.created_at >= week_start)
        ).scalar_one()

        orders_this_month = self.db.execute(
            select(func.count(Order.id)).where(Order.created_at >= month_start)
        ).scalar_one()

        sales_query = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.status != OrderStatus.CANCELLED
        )
        if period_start:
            sales_query = sales_query.where(Order.created_at >= period_start)
        if period_end:
            sales_query = sales_query.where(Order.created_at <= period_end)
        sales_total_period = float(self.db.execute(sales_query).scalar_one())

        # عملاء مخصصون بلا أي تفاعل مسجَّل إطلاقًا
        contacted_customer_ids = select(Interaction.customer_id).distinct()
        customers_not_contacted = self.db.execute(
            select(func.count(func.distinct(CustomerAssignment.customer_id))).where(
                CustomerAssignment.is_active.is_(True),
                CustomerAssignment.customer_id.notin_(contacted_customer_ids),
            )
        ).scalar_one()

        followups_due = self.db.execute(
            select(func.count(FollowUp.id)).where(
                FollowUp.is_done.is_(False), FollowUp.due_at <= today_end
            )
        ).scalar_one()

        latest_interaction_sq = (
            select(Interaction.customer_id, func.max(Interaction.created_at).label("latest_at"))
            .group_by(Interaction.customer_id)
            .subquery()
        )
        retry_alias = Interaction
        customers_needing_retry = self.db.execute(
            select(func.count(func.distinct(retry_alias.customer_id)))
            .select_from(retry_alias)
            .join(
                latest_interaction_sq,
                and_(
                    latest_interaction_sq.c.customer_id == retry_alias.customer_id,
                    latest_interaction_sq.c.latest_at == retry_alias.created_at,
                ),
            )
            .where(retry_alias.status_code == RETRY_STATUS_CODE)
        ).scalar_one()

        return {
            "total_customers": total_customers,
            "assigned_customers": assigned_customers,
            "unassigned_customers": unassigned_customers,
            "total_employees": total_employees,
            "orders_today": orders_today,
            "orders_this_week": orders_this_week,
            "orders_this_month": orders_this_month,
            "sales_total_period": sales_total_period,
            "customers_not_contacted": customers_not_contacted,
            "followups_due": followups_due,
            "customers_needing_retry": customers_needing_retry,
        }

    def employee_performance(self, date_from: date | None, date_to: date | None) -> list[dict]:
        """القاعدة 30: أداء الموظفين — استعلام واحد مجمّع لكل مؤشر، بدون Rankings/Gamification."""
        period_start = datetime.combine(date_from, time.min, tzinfo=timezone.utc) if date_from else None
        period_end = datetime.combine(date_to, time.max, tzinfo=timezone.utc) if date_to else None

        employees = list(
            self.db.execute(
                select(User).where(User.role == UserRole.EMPLOYEE, User.deleted_at.is_(None))
            ).scalars()
        )

        rows = []
        for emp in employees:
            assigned_count = self.db.execute(
                select(func.count(CustomerAssignment.id)).where(
                    CustomerAssignment.employee_id == emp.id, CustomerAssignment.is_active.is_(True)
                )
            ).scalar_one()

            contacted_ids_stmt = select(Interaction.customer_id).where(Interaction.employee_id == emp.id)
            if period_start:
                contacted_ids_stmt = contacted_ids_stmt.where(Interaction.created_at >= period_start)
            if period_end:
                contacted_ids_stmt = contacted_ids_stmt.where(Interaction.created_at <= period_end)
            contacted = self.db.execute(
                select(func.count(func.distinct(contacted_ids_stmt.subquery().c.customer_id)))
            ).scalar_one()

            orders_stmt = select(func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.employee_id == emp.id, Order.status != OrderStatus.CANCELLED
            )
            if period_start:
                orders_stmt = orders_stmt.where(Order.created_at >= period_start)
            if period_end:
                orders_stmt = orders_stmt.where(Order.created_at <= period_end)
            orders_count, sales_total = self.db.execute(orders_stmt).one()

            followups_pending = self.db.execute(
                select(func.count(FollowUp.id)).where(
                    FollowUp.employee_id == emp.id, FollowUp.is_done.is_(False)
                )
            ).scalar_one()

            conversion_rate = round((orders_count / assigned_count) * 100, 1) if assigned_count else 0.0

            rows.append(
                {
                    "employee_id": emp.id,
                    "employee_name": emp.full_name,
                    "assigned_customers": assigned_count,
                    "contacted": contacted,
                    "not_contacted": max(assigned_count - contacted, 0),
                    "orders_count": orders_count,
                    "sales_total": float(sales_total),
                    "conversion_rate": conversion_rate,
                    "followups_pending": followups_pending,
                }
            )
        return rows

    def employee_workspace(self, employee_id: uuid.UUID) -> dict:
        """القاعدة 29: مساحة عمل الموظفة اليومية."""
        now = datetime.now(timezone.utc)
        today_start, today_end = _day_bounds(now.date())

        assigned_customers = self.db.execute(
            select(func.count(CustomerAssignment.id)).where(
                CustomerAssignment.employee_id == employee_id, CustomerAssignment.is_active.is_(True)
            )
        ).scalar_one()

        contacted_today = self.db.execute(
            select(func.count(func.distinct(Interaction.customer_id))).where(
                Interaction.employee_id == employee_id, Interaction.created_at.between(today_start, today_end)
            )
        ).scalar_one()

        followups_due_today = self.db.execute(
            select(func.count(FollowUp.id)).where(
                FollowUp.employee_id == employee_id,
                FollowUp.is_done.is_(False),
                FollowUp.due_at <= today_end,
            )
        ).scalar_one()

        orders_today_stmt = select(
            func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0)
        ).where(
            Order.employee_id == employee_id,
            Order.created_at.between(today_start, today_end),
            Order.status != OrderStatus.CANCELLED,
        )
        orders_today, sales_today = self.db.execute(orders_today_stmt).one()

        return {
            "assigned_customers": assigned_customers,
            "contacted_today": contacted_today,
            "not_contacted_today": max(assigned_customers - contacted_today, 0),
            "followups_due_today": followups_due_today,
            "orders_today": orders_today,
            "sales_today": float(sales_today),
        }
