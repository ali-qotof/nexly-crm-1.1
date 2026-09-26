"""
القاعدة المشتركة لكل الـ Models، مع Mixins للحقول المتكررة (id, timestamps, soft delete).

القاعدة 39 (Database): Schema منظّم (Normalized)، لا نستخدم JSON كبديل عن العلاقات
إلا عند الحاجة الفعلية (payloads الخاصة بـ Webhooks مثلًا).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """مفتاح أساسي UUID — آمن للاستخدام في مسارات API العامة دون كشف تسلسل الصفوف."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """أعمدة created_at / updated_at موحّدة لكل الجداول."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Soft delete موحّد. يُستخدم في users (القاعدة 16: لا نحذف الموظفة فعليًا)
    والعملاء والمنتجات عند الحاجة، بدل DELETE فعلي يفقد التاريخ.
    """

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
