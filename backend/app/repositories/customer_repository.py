import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import Customer, CustomerAssignment, Interaction, Order, User


class CustomerRepository:
    """
    القاعدة 9/40: لا تحميل كل العملاء دفعة واحدة أبدًا. كل استعلام هنا Server-side بالكامل
    (Pagination + Filtering + Search على مستوى قاعدة البيانات)، ويعتمد على Subqueries مجمّعة
    (aggregated) لآخر تفاعل وآخر أوردر بدل N+1 queries لكل صف.
    """

    def __init__(self, db: Session):
        self.db = db

    def _base_query(self, employee_id: uuid.UUID | None = None):
        latest_interaction_sq = (
            select(
                Interaction.customer_id,
                func.max(Interaction.created_at).label("latest_interaction_at"),
            )
            .group_by(Interaction.customer_id)
            .subquery()
        )
        latest_order_sq = (
            select(
                Order.customer_id,
                func.max(Order.created_at).label("latest_order_at"),
            )
            .group_by(Order.customer_id)
            .subquery()
        )
        latest_order_alias = aliased(Order)
        latest_interaction_alias = aliased(Interaction)
        employee_alias = aliased(User)

        query = (
            select(
                Customer,
                CustomerAssignment.employee_id,
                employee_alias.full_name,
                latest_interaction_sq.c.latest_interaction_at,
                latest_interaction_alias.status_code,
                latest_order_alias.created_at,
                latest_order_alias.total_amount,
            )
            .outerjoin(
                CustomerAssignment,
                (CustomerAssignment.customer_id == Customer.id)
                & (CustomerAssignment.is_active.is_(True)),
            )
            .outerjoin(employee_alias, employee_alias.id == CustomerAssignment.employee_id)
            .outerjoin(
                latest_interaction_sq, latest_interaction_sq.c.customer_id == Customer.id
            )
            .outerjoin(
                latest_interaction_alias,
                (latest_interaction_alias.customer_id == Customer.id)
                & (latest_interaction_alias.created_at == latest_interaction_sq.c.latest_interaction_at),
            )
            .outerjoin(
                latest_order_sq, latest_order_sq.c.customer_id == Customer.id
            )
            .outerjoin(
                latest_order_alias,
                (latest_order_alias.customer_id == Customer.id)
                & (latest_order_alias.created_at == latest_order_sq.c.latest_order_at),
            )
        )

        if employee_id is not None:
            query = query.where(
                CustomerAssignment.employee_id == employee_id,
                CustomerAssignment.is_active.is_(True),
            )

        return query

    def search(
        self,
        *,
        q: str | None = None,
        employee_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list, int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)  # سقف لحماية الأداء

        query = self._base_query(employee_id=employee_id)

        if unassigned_only:
            query = query.where(CustomerAssignment.id.is_(None))

        if q:
            like = f"%{q.strip()}%"
            query = query.where(
                (Customer.name.ilike(like))
                | (Customer.phone.ilike(like))
                | (Customer.customer_code.ilike(like))
                | (Customer.source_customer_id.ilike(like))
                | (Customer.whatsapp.ilike(like))
            )

        query = query.where(Customer.deleted_at.is_(None))

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        query = query.order_by(Customer.created_at.desc()).offset((page - 1) * page_size).limit(
            page_size
        )
        rows = self.db.execute(query).all()
        return rows, total

    def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_by_code(self, customer_code: str) -> Customer | None:
        stmt = select(Customer).where(Customer.customer_code == customer_code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_assignment(self, customer_id: uuid.UUID) -> CustomerAssignment | None:
        stmt = select(CustomerAssignment).where(
            CustomerAssignment.customer_id == customer_id,
            CustomerAssignment.is_active.is_(True),
        )
        return self.db.execute(stmt).scalar_one_or_none()
