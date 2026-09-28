import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationEventStatus, IntegrationType


class IntegrationCreate(BaseModel):
    type: IntegrationType
    name: str = Field(min_length=1, max_length=100)
    config: dict = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    is_enabled: bool | None = None
    config: dict | None = None


class IntegrationOut(BaseModel):
    id: uuid.UUID
    type: IntegrationType
    name: str
    is_enabled: bool
    config: dict
    last_sync_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IntegrationSecretOut(BaseModel):
    """يُرجَع مرة واحدة فقط عند الإنشاء/التدوير — لا يُخزَّن أو يُعرض لاحقًا كنص صريح."""

    plain_secret: str


class IntegrationCreateOut(IntegrationOut):
    plain_secret_shown_once: str


class WebhookEventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=64)
    entity_type: str | None = None
    entity_id: str | None = None
    payload: dict = Field(default_factory=dict)


class IntegrationEventOut(BaseModel):
    id: uuid.UUID
    integration_id: uuid.UUID
    event_id: str
    event_type: str
    entity_type: str | None
    entity_id: str | None
    status: IntegrationEventStatus
    attempts: int
    last_attempt_at: datetime | None
    next_retry_at: datetime | None
    error: str | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
