import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_manager
from app.db.session import get_db
from app.models import User
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationCreateOut,
    IntegrationEventOut,
    IntegrationOut,
    IntegrationSecretOut,
    IntegrationUpdate,
    WebhookEventIn,
)
from app.services.integration_service import IntegrationError, IntegrationService
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["integrations"])


@router.get("/integrations", response_model=list[IntegrationOut])
def list_integrations(current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    return IntegrationService(db).list_integrations()


@router.post("/integrations", response_model=IntegrationCreateOut, status_code=status.HTTP_201_CREATED)
def create_integration(payload: IntegrationCreate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    """السر يُرجَع مرة واحدة فقط هنا، ولا يظهر مجددًا في أي GET لاحق (القاعدة 38)."""
    integration, plain_secret = IntegrationService(db).create(payload, current_user)
    return IntegrationCreateOut(**IntegrationOut.model_validate(integration).model_dump(), plain_secret_shown_once=plain_secret)


@router.patch("/integrations/{integration_id}", response_model=IntegrationOut)
def update_integration(
    integration_id: uuid.UUID, payload: IntegrationUpdate, current_user: User = Depends(require_manager), db: Session = Depends(get_db)
):
    try:
        return IntegrationService(db).update(integration_id, payload, current_user)
    except IntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/integrations/{integration_id}/rotate-secret", response_model=IntegrationSecretOut)
def rotate_secret(integration_id: uuid.UUID, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        _, plain_secret = IntegrationService(db).rotate_secret(integration_id, current_user)
    except IntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return IntegrationSecretOut(plain_secret=plain_secret)


@router.post("/integrations/{integration_id}/test")
def test_connection(integration_id: uuid.UUID, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    try:
        return IntegrationService(db).test_connection(integration_id)
    except IntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/integrations/{integration_id}/events", response_model=list[IntegrationEventOut])
def list_events(integration_id: uuid.UUID, current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    return WebhookService(db).list_events(integration_id)


@router.post("/webhooks/{integration_id}", status_code=status.HTTP_202_ACCEPTED)
def receive_webhook(
    integration_id: uuid.UUID,
    payload: WebhookEventIn,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    """
    القاعدة 32/34: نقطة استقبال عامة لأي مزوّد خارجي (Google Sheets، إلخ). محمية بسر مشترك
    (وليس جلسة مستخدم — المصدر نظام خارجي)، مع Deduplication صريح على event_id.
    """
    service = IntegrationService(db)
    integration = service.get(integration_id)
    if integration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التكامل غير موجود")
    if not integration.is_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="التكامل معطَّل")
    if not x_webhook_secret or not service.verify_webhook_secret(integration_id, x_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="سر التحقق غير صحيح")

    event, is_new = WebhookService(db).ingest(integration_id, payload)
    return {"event_id": event.event_id, "duplicate": not is_new}
