import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated, require_manager
from app.db.session import get_db
from app.models import User
from app.schemas.product import (
    BundleCreate,
    BundleOut,
    BundleUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    VariantCreate,
    VariantOut,
    VariantUpdate,
)
from app.services.bundle_service import BundleError, BundleService
from app.services.product_service import ProductError, ProductService

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    متاح لكل المستخدمين المصادَق عليهم (مدير وموظفة) — القاعدة 65: الموظفة تحتاج الوصول السريع
    لاسم المنتج والسعر والوحدة والعرض أثناء تسجيل الأوردر.
    """
    return ProductService(db).list_products(q=q, category=category)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return ProductService(db).create_product(payload, current_user)
    except ProductError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: uuid.UUID, payload: ProductUpdate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return ProductService(db).update_product(product_id, payload, current_user)
    except ProductError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/products/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
def add_variant(product_id: uuid.UUID, payload: VariantCreate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return ProductService(db).add_variant(product_id, payload, current_user)
    except ProductError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/product-variants/{variant_id}", response_model=VariantOut)
def update_variant(variant_id: uuid.UUID, payload: VariantUpdate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return ProductService(db).update_variant(variant_id, payload, current_user)
    except ProductError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _bundle_to_out(bundle, service: BundleService) -> BundleOut:
    out = BundleOut.model_validate(bundle)
    out.regular_total = service.compute_regular_total(bundle)
    for item_out, item in zip(out.items, bundle.items):
        item_out.variant_label = item.product_variant.unit_label
        item_out.product_name = item.product_variant.product.name_ar
    return out


@router.get("/bundles", response_model=list[BundleOut])
def list_bundles(
    active_only: bool = Query(default=False),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    service = BundleService(db)
    return [_bundle_to_out(b, service) for b in service.list_bundles(active_only=active_only)]


@router.post("/bundles", response_model=BundleOut, status_code=status.HTTP_201_CREATED)
def create_bundle(payload: BundleCreate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    service = BundleService(db)
    try:
        bundle = service.create_bundle(payload, current_user)
    except BundleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _bundle_to_out(bundle, service)


@router.patch("/bundles/{bundle_id}", response_model=BundleOut)
def update_bundle(bundle_id: uuid.UUID, payload: BundleUpdate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    service = BundleService(db)
    try:
        bundle = service.update_bundle(bundle_id, payload, current_user)
    except BundleError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _bundle_to_out(bundle, service)
