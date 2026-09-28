import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, Sequence, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OrderStatus


# رقم الطلب من SEQUENCE في قاعدة البيانات: ذرّي تحت التزامن (COUNT كان يتصادم).
order_number_seq = Sequence("order_number_seq", metadata=Base.metadata)


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    طلب (Order). Backend هو Source of Truth الوحيد لحساب الأسعار (القاعدة 19) —
    كل مبالغ subtotal/discount/shipping/total تُحسب وتُحفظ هنا من خدمة OrderPricingService،
    ولا يُعاد حسابها في الواجهة الأمامية بشكل مستقل.

    idempotency_key: يمنع إنشاء Order مكرر عند الضغط المتكرر على Save (القاعدة 20) — فريد على مستوى الجدول.
    """

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    shipping_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.PENDING
    )
    order_source: Mapped[str] = mapped_column(String(32), nullable=False, default="crm")
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """
    بند داخل الطلب. يحتفظ بلقطة (snapshot) من السعر وقت البيع (unit_price) — حتى لو تغيّر
    سعر المنتج لاحقًا، تاريخ الطلبات القديمة لا يتأثر.
    """

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=True
    )
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bundles.id", ondelete="RESTRICT"), nullable=True
    )
    name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
