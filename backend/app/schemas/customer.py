import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CustomerOut(BaseModel):
    id: uuid.UUID
    customer_code: str
    source_customer_id: str | None
    name: str
    phone: str
    whatsapp: str | None
    address: str | None
    governorate: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerListItem(CustomerOut):
    """صف في قائمة العملاء — يضيف معلومات التخصيص والحالة دون تحميل العلاقات الكاملة."""

    assigned_employee_id: uuid.UUID | None = None
    assigned_employee_name: str | None = None
    latest_status_code: str | None = None
    latest_status_label: str | None = None
    latest_interaction_at: datetime | None = None
    latest_order_at: datetime | None = None
    latest_order_total: float | None = None


class PaginatedCustomers(BaseModel):
    items: list[CustomerListItem]
    total: int
    page: int
    page_size: int


class CustomerCreate(BaseModel):
    customer_code: str = Field(min_length=1, max_length=32)
    source_customer_id: str | None = None
    name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=32)
    whatsapp: str | None = None
    address: str | None = None
    governorate: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    address: str | None = None
    governorate: str | None = None
