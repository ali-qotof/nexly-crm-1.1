import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Product, ProductVariant
from app.services.audit_service import write_audit_log


class ProductError(Exception):
    pass


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def list_products(self, *, q: str | None = None, category: str | None = None) -> list[Product]:
        stmt = select(Product).options(selectinload(Product.variants)).where(
            Product.deleted_at.is_(None)
        )
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where((Product.name_ar.ilike(like)) | (Product.name_en.ilike(like)) | (Product.sku.ilike(like)))
        if category:
            stmt = stmt.where(Product.category == category)
        stmt = stmt.order_by(Product.name_ar)
        return list(self.db.execute(stmt).scalars())

    def get_product(self, product_id: uuid.UUID) -> Product | None:
        stmt = select(Product).options(selectinload(Product.variants)).where(Product.id == product_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_product(self, data, actor) -> Product:
        product = Product(
            sku=data.sku,
            barcode=data.barcode,
            name_ar=data.name_ar,
            name_en=data.name_en,
            category=data.category,
            description=data.description,
            image_url=data.image_url,
        )
        for v in data.variants:
            product.variants.append(
                ProductVariant(unit_label=v.unit_label, weight_grams=v.weight_grams, price=v.price)
            )
        self.db.add(product)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ProductError(f"SKU '{data.sku}' مستخدَم بالفعل")

        write_audit_log(
            self.db, user_id=actor.id, action="product_created", entity_type="product", entity_id=str(product.id)
        )
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(self, product_id: uuid.UUID, data, actor) -> Product:
        product = self.get_product(product_id)
        if product is None:
            raise ProductError("المنتج غير موجود")

        for field in ["name_ar", "name_en", "category", "description", "image_url", "is_active"]:
            value = getattr(data, field, None)
            if value is not None:
                setattr(product, field, value)

        write_audit_log(
            self.db, user_id=actor.id, action="product_updated", entity_type="product", entity_id=str(product.id)
        )
        self.db.commit()
        self.db.refresh(product)
        return product

    def add_variant(self, product_id: uuid.UUID, data, actor) -> ProductVariant:
        product = self.get_product(product_id)
        if product is None:
            raise ProductError("المنتج غير موجود")

        variant = ProductVariant(
            product_id=product_id, unit_label=data.unit_label, weight_grams=data.weight_grams, price=data.price
        )
        self.db.add(variant)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ProductError(f"الوحدة '{data.unit_label}' موجودة بالفعل لهذا المنتج")

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="price_changed",
            entity_type="product_variant",
            entity_id=str(variant.id),
            meta={"action": "variant_added", "unit_label": data.unit_label, "price": data.price},
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def update_variant(self, variant_id: uuid.UUID, data, actor) -> ProductVariant:
        variant = self.db.get(ProductVariant, variant_id)
        if variant is None:
            raise ProductError("الوحدة غير موجودة")

        old_price = float(variant.price)
        for field in ["unit_label", "weight_grams", "price", "is_active"]:
            value = getattr(data, field, None)
            if value is not None:
                setattr(variant, field, value)

        if data.price is not None and float(data.price) != old_price:
            write_audit_log(
                self.db,
                user_id=actor.id,
                action="price_changed",
                entity_type="product_variant",
                entity_id=str(variant.id),
                meta={"old_price": old_price, "new_price": float(data.price)},
            )
        self.db.commit()
        self.db.refresh(variant)
        return variant
