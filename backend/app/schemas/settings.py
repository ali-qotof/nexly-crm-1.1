import uuid

from pydantic import BaseModel, Field


class ShippingRuleCreate(BaseModel):
    governorate_group: str = Field(min_length=1, max_length=64)
    shipping_cost: float = Field(ge=0)
    free_shipping_threshold: float | None = None


class ShippingRuleUpdate(BaseModel):
    shipping_cost: float | None = Field(default=None, ge=0)
    free_shipping_threshold: float | None = None
    is_active: bool | None = None


class ShippingRuleOut(BaseModel):
    id: uuid.UUID
    governorate_group: str
    shipping_cost: float
    free_shipping_threshold: float | None
    is_active: bool

    model_config = {"from_attributes": True}


class StatusConfigurationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label_ar: str = Field(min_length=1, max_length=100)
    color_hex: str = Field(min_length=4, max_length=7)
    sort_order: int = 0


class StatusConfigurationUpdate(BaseModel):
    label_ar: str | None = None
    color_hex: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class StatusConfigurationOut(BaseModel):
    id: uuid.UUID
    code: str
    label_ar: str
    color_hex: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}
