import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated, require_manager
from app.db.session import get_db
from app.models import User
from app.schemas.settings import (
    ShippingRuleCreate,
    ShippingRuleOut,
    ShippingRuleUpdate,
    StatusConfigurationCreate,
    StatusConfigurationOut,
    StatusConfigurationUpdate,
)
from app.services.settings_service import SettingsError, SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/shipping-rules", response_model=list[ShippingRuleOut])
def list_shipping_rules(current_user: User = Depends(require_any_authenticated), db: Session = Depends(get_db)):
    return SettingsService(db).list_shipping_rules()


@router.post("/shipping-rules", response_model=ShippingRuleOut, status_code=status.HTTP_201_CREATED)
def create_shipping_rule(payload: ShippingRuleCreate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    return SettingsService(db).create_shipping_rule(payload, current_user)


@router.patch("/shipping-rules/{rule_id}", response_model=ShippingRuleOut)
def update_shipping_rule(rule_id: uuid.UUID, payload: ShippingRuleUpdate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return SettingsService(db).update_shipping_rule(rule_id, payload, current_user)
    except SettingsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/statuses", response_model=list[StatusConfigurationOut])
def list_statuses(current_user: User = Depends(require_any_authenticated), db: Session = Depends(get_db)):
    """تُقرأ مرة واحدة في الواجهة الأمامية وتُستخدم كمصدر الألوان الموحّد (القاعدة 11)."""
    return SettingsService(db).list_statuses()


@router.post("/statuses", response_model=StatusConfigurationOut, status_code=status.HTTP_201_CREATED)
def create_status(payload: StatusConfigurationCreate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return SettingsService(db).create_status(payload, current_user)
    except SettingsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/statuses/{status_id}", response_model=StatusConfigurationOut)
def update_status(status_id: uuid.UUID, payload: StatusConfigurationUpdate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return SettingsService(db).update_status(status_id, payload, current_user)
    except SettingsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
