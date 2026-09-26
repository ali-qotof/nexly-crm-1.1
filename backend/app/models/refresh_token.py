import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Refresh token معارض بجلسة تسجيل دخول واحدة (القاعدة 6: Session persistence، Refresh لا يخرج
    المستخدم بدون سبب). نخزّن hash للتوكن فقط، وليس التوكن نفسه، بنفس منطق كلمات المرور.

    يُستبدل التوكن بآخر جديد عند كل استخدام (Rotation) ويُلغى القديم — يمنع إعادة استخدام توكن مسروق
    بعد أن يُستخدم مرة من قبل صاحبه الفعلي.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replaced_by_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
