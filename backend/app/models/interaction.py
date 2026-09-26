import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Interaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    سجل تواصل مع عميل (مكالمة/واتساب/ملاحظة عامة) — منفصل تمامًا عن "حالة التواصل الحالية"
    للعميل (القاعدة 11: Communication Status منفصل عن آخر تفاعل ومنفصل عن آخر أوردر).

    status_code يشير إلى قيمة من StatusConfiguration (جدول قابل للإدارة من المدير)، وليس Enum ثابت.
    """

    __tablename__ = "interactions"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # call | whatsapp | note
    status_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class FollowUp(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """متابعة مجدولة لعميل (القاعدة 26)."""

    __tablename__ = "followups"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_done: Mapped[bool] = mapped_column(default=False, nullable=False)


class Attachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """مرفق عام (صورة شكوى، مرفق ملاحظة) — القاعدة 27 و28."""

    __tablename__ = "attachments"

    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    complaint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=True
    )
