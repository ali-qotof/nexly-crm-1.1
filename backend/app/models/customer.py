import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    قاعدة العملاء — مصممة لتحمّل 100,000+ سجل (القاعدة 9 و40).
    فهارس على الحقول المستخدمة في البحث (name, phone, customer_id, source_customer_id).
    """

    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_name", "name"),
        Index("ix_customers_phone", "phone"),
        Index("ix_customers_whatsapp", "whatsapp"),
        Index("ix_customers_source_customer_id", "source_customer_id"),
    )

    customer_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    # معرّف العميل القادم من النظام القديم/مصدر خارجي (يُستخدم في Matching أثناء Import — القاعدة 15)
    source_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    governorate: Mapped[str | None] = mapped_column(String(64), nullable=True)

    assignments: Mapped[list["CustomerAssignment"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    segments: Mapped[list["CustomerSegment"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Segment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """شرائح العملاء: A1, A2, B1, B2, C, D ... قابلة للتوسعة (القاعدة 25) — بيانات وليست Enum ثابت."""

    __tablename__ = "segments"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    label_ar: Mapped[str] = mapped_column(String(64), nullable=False)


class CustomerSegment(TimestampMixin, Base):
    """ربط عميل بشريحة (علاقة متعددة إلى متعددة صريحة حتى تحمل created_at)."""

    __tablename__ = "customer_segments"
    __table_args__ = (UniqueConstraint("customer_id", "segment_id", name="uq_customer_segment"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="segments")
    segment: Mapped["Segment"] = relationship()


class CustomerAssignment(TimestampMixin, Base):
    """
    توزيع العملاء على الموظفات (القاعدة 13).

    قيد فريد على (customer_id) مع is_active=True يمنع Duplicate assignment فعليًا على مستوى
    قاعدة البيانات (partial unique index)، وليس فقط على مستوى Application logic — هذا يمنع
    race conditions عند التوزيع المتزامن.

    employee_order: ترتيب العميل ضمن قائمة الموظفة (القاعدة 67) — لا يُعاد ترتيبه عشوائيًا بعد Save.
    """

    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    employee_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Partial unique index: عميل واحد لا يمكن أن يكون له أكثر من تخصيص نشط واحد في نفس الوقت.
        # هذا يمنع Duplicate assignment و race conditions على مستوى قاعدة البيانات (القاعدة 13).
        Index(
            "uq_active_customer_assignment",
            "customer_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    customer: Mapped["Customer"] = relationship(back_populates="assignments")
    employee: Mapped["User"] = relationship(foreign_keys=[employee_id], back_populates="assigned_customers")
