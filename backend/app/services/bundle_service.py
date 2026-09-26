import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Bundle, BundleItem, ProductVariant
from app.services.audit_service import write_audit_log


class BundleError(Exception):
    pass


class BundleService:
    def __init__(self, db: Session):
        self.db = db

    def list_bundles(self, *, active_only: bool = False) -> list[Bundle]:
        stmt = select(Bundle).options(
            selectinload(Bundle.items).selectinload(BundleItem.product_variant).selectinload(ProductVariant.product)
        )
        if active_only:
            stmt = stmt.where(Bundle.is_active.is_(True))
        stmt = stmt.order_by(Bundle.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def get_bundle(self, bundle_id: uuid.UUID) -> Bundle | None:
        stmt = (
            select(Bundle)
            .options(
                selectinload(Bundle.items)
                .selectinload(BundleItem.product_variant)
                .selectinload(ProductVariant.product)
            )
            .where(Bundle.id == bundle_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def compute_regular_total(self, bundle: Bundle) -> float:
        return sum(float(item.product_variant.price) * item.quantity for item in bundle.items)

    def create_bundle(self, data, actor) -> Bundle:
        bundle = Bundle(
            name=data.name,
            bundle_price=data.bundle_price,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        self.db.add(bundle)
        self.db.flush()

        for item in data.items:
            variant = self.db.get(ProductVariant, item.product_variant_id)
            if variant is None:
                self.db.rollback()
                raise BundleError("أحد المنتجات المحددة غير موجود")
            bundle.items.append(BundleItem(product_variant_id=item.product_variant_id, quantity=item.quantity))

        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise BundleError("يوجد تكرار لنفس المنتج داخل هذا العرض — القاعدة 23 تمنع ذلك")

        write_audit_log(
            self.db, user_id=actor.id, action="bundle_created", entity_type="bundle", entity_id=str(bundle.id)
        )
        self.db.commit()
        return self.get_bundle(bundle.id)

    def update_bundle(self, bundle_id: uuid.UUID, data, actor) -> Bundle:
        bundle = self.get_bundle(bundle_id)
        if bundle is None:
            raise BundleError("العرض غير موجود")

        for field in ["name", "bundle_price", "is_active", "start_date", "end_date"]:
            value = getattr(data, field, None)
            if value is not None:
                setattr(bundle, field, value)

        write_audit_log(
            self.db, user_id=actor.id, action="bundle_updated", entity_type="bundle", entity_id=str(bundle.id)
        )
        self.db.commit()
        return self.get_bundle(bundle_id)
