import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Customer, Order, OrderItem, User
from app.models.enums import OrderStatus
from app.services.access_control import CustomerAccessError, ensure_customer_access
from app.services.audit_service import write_audit_log
from app.services.pricing_service import OrderPricingService, PricingError


class OrderError(Exception):
    pass


def _generate_order_number(db: Session) -> str:
    """رقم طلب تسلسلي بسيط وقابل للقراءة البشرية (ORD-000001)."""
    count = db.execute(select(Order)).scalars().all()
    return f"ORD-{len(count) + 1:06d}"


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, data, actor: User) -> Order:
        """
        القاعدة 20: Idempotency. إذا وصل نفس idempotency_key مرة أخرى (ضغط Save مكرر)، تُرجَع
        نفس الطلب الأصلي بدل إنشاء طلب جديد — لا خطأ يُعرض للمستخدم، والنتيجة النهائية متطابقة
        سواء ضغط مرة أو خمس مرات.
        """
        existing_stmt = select(Order).options(selectinload(Order.items)).where(
            Order.idempotency_key == data.idempotency_key
        )
        existing = self.db.execute(existing_stmt).scalar_one_or_none()
        if existing is not None:
            return existing

        customer = self.db.get(Customer, data.customer_id)
        if customer is None:
            raise OrderError("العميل غير موجود")
        try:
            ensure_customer_access(self.db, data.customer_id, actor)
        except CustomerAccessError as exc:
            raise OrderError(str(exc))

        pricing = OrderPricingService(self.db)
        try:
            result = pricing.price_order(
                customer=customer,
                items=data.items,
                discount_type=data.discount_type,
                discount_value=data.discount_value,
            )
        except PricingError as exc:
            raise OrderError(str(exc))

        order = Order(
            order_number=_generate_order_number(self.db),
            idempotency_key=data.idempotency_key,
            customer_id=customer.id,
            employee_id=actor.id,
            subtotal=result.subtotal,
            discount_amount=result.discount_amount,
            shipping_amount=result.shipping_amount,
            total_amount=result.total_amount,
            status=OrderStatus.PENDING,
            order_source=data.order_source,
            notes=data.notes,
        )
        for line in result.lines:
            order.items.append(
                OrderItem(
                    product_variant_id=line.product_variant_id,
                    bundle_id=line.bundle_id,
                    name_snapshot=line.name_snapshot,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    line_total=line.line_total,
                )
            )

        self.db.add(order)
        try:
            self.db.flush()
        except IntegrityError:
            # حالة نادرة: نفس idempotency_key وصل في نفس اللحظة تمامًا من طلبين متزامنين
            # (Race condition حقيقي). القيد الفريد على مستوى DB يمنع الازدواج بأي حال.
            self.db.rollback()
            existing = self.db.execute(existing_stmt).scalar_one_or_none()
            if existing is not None:
                return existing
            raise

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="order_created",
            entity_type="order",
            entity_id=str(order.id),
            meta={"total_amount": result.total_amount, "customer_id": str(customer.id)},
        )
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_order(self, order_id: uuid.UUID) -> Order | None:
        stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_orders(
        self,
        *,
        employee_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status_filter: OrderStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Order], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        conditions = []
        if employee_id:
            conditions.append(Order.employee_id == employee_id)
        if customer_id:
            conditions.append(Order.customer_id == customer_id)
        if status_filter:
            conditions.append(Order.status == status_filter)
        if date_from:
            conditions.append(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conditions.append(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

        count_stmt = select(func.count(Order.id)).where(*conditions)
        total = self.db.execute(count_stmt).scalar_one()

        items_stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(*conditions)
            .order_by(Order.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(items_stmt).scalars())
        return items, total

    def cancel_order(self, order_id: uuid.UUID, actor: User) -> Order:
        order = self.get_order(order_id)
        if order is None:
            raise OrderError("الطلب غير موجود")
        if order.status == OrderStatus.CANCELLED:
            return order

        order.status = OrderStatus.CANCELLED
        write_audit_log(
            self.db, user_id=actor.id, action="order_cancelled", entity_type="order", entity_id=str(order.id)
        )
        self.db.commit()
        self.db.refresh(order)
        return order
