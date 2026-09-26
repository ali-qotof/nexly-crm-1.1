import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IntegrationEventStatus, IntegrationType


class Integration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    تكامل خارجي (Google Sheets، WhatsApp provider، Shipping provider، ...) — القاعدة 32/33.
    secret_hash يُخزَّن كـ hash فقط، لا كنص صريح (القاعدة 38: لا أسرار في القاعدة كنص واضح).
    """

    __tablename__ = "integrations"

    type: Mapped[IntegrationType] = mapped_column(
        SAEnum(IntegrationType, name="integration_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    secret_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["IntegrationEvent"]] = relationship(back_populates="integration")


class IntegrationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    سجل أحداث Webhook الواردة/الصادرة (القاعدة 34).
    event_id فريد لمنع المعالجة المكررة (Deduplication) للأحداث الواردة من نفس المصدر.
    """

    __tablename__ = "integration_events"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[IntegrationEventStatus] = mapped_column(
        SAEnum(IntegrationEventStatus, name="integration_event_status"),
        nullable=False,
        default=IntegrationEventStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    integration: Mapped["Integration"] = relationship(back_populates="events")
