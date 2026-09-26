import uuid
from datetime import date

from pydantic import BaseModel, Field


class VariantCreate(BaseModel):
    unit_label: str = Field(min_length=1, max_length=32)
    weight_grams: int | None = None
    price: float = Field(gt=0)


class VariantUpdate(BaseModel):
    unit_label: str | None = None
    weight_grams: int | None = None
    price: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


class VariantOut(BaseModel):
    id: uuid.UUID
    unit_label: str
    weight_grams: int | None
    price: float
    is_active: bool

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = None
    name_ar: str = Field(min_length=1, max_length=150)
    name_en: str | None = None
    category: str | None = None
    description: str | None = None
    image_url: str | None = None
    variants: list[VariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    category: str | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    sku: str
    barcode: str | None
    name_ar: str
    name_en: str | None
    category: str | None
    description: str | None
    image_url: str | None
    is_active: bool
    variants: list[VariantOut] = []

    model_config = {"from_attributes": True}


class BundleItemCreate(BaseModel):
    product_variant_id: uuid.UUID
    quantity: int = Field(gt=0)


class BundleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    bundle_price: float = Field(gt=0)
    start_date: date | None = None
    end_date: date | None = None
    items: list[BundleItemCreate] = Field(min_length=1)


class BundleUpdate(BaseModel):
    name: str | None = None
    bundle_price: float | None = Field(default=None, gt=0)
    is_active: bool | None = None
    start_date: date | None = None
    end_date: date | None = None


class BundleItemOut(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID
    quantity: int
    variant_label: str | None = None
    product_name: str | None = None

    model_config = {"from_attributes": True}


class BundleOut(BaseModel):
    id: uuid.UUID
    name: str
    bundle_price: float
    is_active: bool
    start_date: date | None
    end_date: date | None
    items: list[BundleItemOut] = []
    regular_total: float | None = None

    model_config = {"from_attributes": True}
