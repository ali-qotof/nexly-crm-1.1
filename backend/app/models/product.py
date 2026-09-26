import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """منتج أساسي (القاعدة 22). الأسعار الفعلية والوحدات تعيش في ProductVariant."""

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name_ar: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(150), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    الوزن/الوحدة والسعر الفعلي (مثال القاعدة 24: عجوة 500g/1kg/2kg/3kg بأسعار مختلفة).
    هذا هو الكيان الذي يُستخدم فعليًا داخل Order Items — وليس Product مباشرة.
    """

    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "unit_label", name="uq_product_unit"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    unit_label: Mapped[str] = mapped_column(String(32), nullable=False)  # "500g", "1kg", ...
    weight_grams: Mapped[int | None] = mapped_column(nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="variants")


class Bundle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """عرض/Bundle (القاعدة 23) — مثال: 6 أكياس مكسرات مختلفة بسعر إجمالي مخفّض."""

    __tablename__ = "bundles"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    bundle_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    items: Mapped[list["BundleItem"]] = relationship(
        back_populates="bundle", cascade="all, delete-orphan"
    )


class BundleItem(Base):
    """منتج داخل عرض. القاعدة 23: يُمنع تكرار نفس المنتج/Variant داخل نفس العرض (uq_bundle_variant)."""

    __tablename__ = "bundle_items"
    __table_args__ = (UniqueConstraint("bundle_id", "product_variant_id", name="uq_bundle_variant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)

    bundle: Mapped["Bundle"] = relationship(back_populates="items")
    product_variant: Mapped["ProductVariant"] = relationship()
