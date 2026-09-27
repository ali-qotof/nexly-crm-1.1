import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ComplaintStatus


class InteractionCreate(BaseModel):
    customer_id: uuid.UUID
    channel: str = Field(pattern="^(call|whatsapp|note)$")
    status_code: str | None = None
    note: str | None = Field(default=None, max_length=2000)


class InteractionOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    employee_id: uuid.UUID
    channel: str
    status_code: str | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowUpCreate(BaseModel):
    customer_id: uuid.UUID
    due_at: datetime
    note: str | None = Field(default=None, max_length=1000)


class FollowUpUpdate(BaseModel):
    is_done: bool | None = None
    due_at: datetime | None = None
    note: str | None = None


class FollowUpOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    employee_id: uuid.UUID
    due_at: datetime
    note: str | None
    is_done: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplaintCreate(BaseModel):
    customer_id: uuid.UUID
    order_id: uuid.UUID | None = None
    complaint_type: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2000)


class ComplaintUpdate(BaseModel):
    status: ComplaintStatus | None = None
    description: str | None = None


class AttachmentOut(BaseModel):
    id: uuid.UUID
    file_url: str
    file_name: str

    model_config = {"from_attributes": True}


class ComplaintOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    employee_id: uuid.UUID
    complaint_type: str
    description: str
    status: ComplaintStatus
    created_at: datetime
    attachments: list[AttachmentOut] = []

    model_config = {"from_attributes": True}
