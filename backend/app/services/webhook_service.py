import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IntegrationEvent
from app.models.enums import IntegrationEventStatus


class WebhookError(Exception):
    pass


class WebhookService:
    """
    القاعدة 34: event_id, event_type, entity_type, entity_id, payload, status, attempts,
    last_attempt, next_retry, response, error, latency — Deduplication إلزامي على event_id.
    """

    def __init__(self, db: Session):
        self.db = db

    def ingest(self, integration_id: uuid.UUID, data) -> tuple[IntegrationEvent, bool]:
        """يُرجع (event, is_new). إذا event_id مكرر، يُرجع السجل الموجود دون إنشاء جديد."""
        existing_stmt = select(IntegrationEvent).where(IntegrationEvent.event_id == data.event_id)
        existing = self.db.execute(existing_stmt).scalar_one_or_none()
        if existing is not None:
            return existing, False

        start = time.monotonic()
        event = IntegrationEvent(
            integration_id=integration_id,
            event_id=data.event_id,
            event_type=data.event_type,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            payload=data.payload,
            status=IntegrationEventStatus.SUCCESS,  # الاستقبال والتخزين نفسه هو "النجاح" في هذه المرحلة
            attempts=1,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event, True

    def list_events(self, integration_id: uuid.UUID | None = None) -> list[IntegrationEvent]:
        stmt = select(IntegrationEvent).order_by(IntegrationEvent.created_at.desc())
        if integration_id:
            stmt = stmt.where(IntegrationEvent.integration_id == integration_id)
        return list(self.db.execute(stmt).scalars())
