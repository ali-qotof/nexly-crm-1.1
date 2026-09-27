import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DiscountType, OrderStatus


class OrderItemInput(BaseModel):
    product_variant_id: uuid.UUID | None = None
    bundle_id: uuid.UUID | None = None
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=64)
    customer_id: uuid.UUID
    items: list[OrderItemInput] = Field(min_length=1)
    discount_type: DiscountType | None = None
    discount_value: float | None = Field(default=None, ge=0)
    notes: str | None = None
    order_source: str = "crm"


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID | None
    bundle_id: uuid.UUID | None
    name_snapshot: str
    unit_price: float
    quantity: int
    line_total: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    employee_id: uuid.UUID
    subtotal: float
    discount_amount: float
    shipping_amount: float
    total_amount: float
    status: OrderStatus
    order_source: str
    notes: str | None
    created_at: datetime
    items: list[OrderItemOut] = []

    model_config = {"from_attributes": True}


class PaginatedOrders(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int
