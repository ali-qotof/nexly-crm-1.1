import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated
from app.db.session import get_db
from app.models import User
from app.schemas.interaction import (
    FollowUpCreate,
    FollowUpOut,
    FollowUpUpdate,
    InteractionCreate,
    InteractionOut,
)
from app.services.followup_service import FollowUpError, FollowUpService
from app.services.interaction_service import InteractionError, InteractionService

router = APIRouter(tags=["interactions"])


@router.post("/interactions", response_model=InteractionOut, status_code=status.HTTP_201_CREATED)
def create_interaction(
    payload: InteractionCreate,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """تسجيل تفاعل (مكالمة/واتساب/ملاحظة) — منفصل عن حالة الأوردر ومنفصل عن آخر تفاعل (القاعدة 11)."""
    try:
        return InteractionService(db).create_interaction(payload, current_user)
    except InteractionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/customers/{customer_id}/interactions", response_model=list[InteractionOut])
def customer_timeline(
    customer_id: uuid.UUID,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    try:
        return InteractionService(db).list_timeline(customer_id, current_user)
    except InteractionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/followups", response_model=FollowUpOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    payload: FollowUpCreate,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    try:
        return FollowUpService(db).create(payload, current_user)
    except FollowUpError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/followups", response_model=list[FollowUpOut])
def list_followups(
    bucket: str | None = Query(default=None, pattern="^(due_today|overdue|upcoming)$"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """القاعدة 26: Due today / Overdue / Upcoming. المدير يرى الكل، الموظفة تُقيَّد لمتابعاتها."""
    return FollowUpService(db).list_for_employee(current_user, bucket)


@router.patch("/followups/{followup_id}", response_model=FollowUpOut)
def update_followup(
    followup_id: uuid.UUID,
    payload: FollowUpUpdate,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    service = FollowUpService(db)
    if payload.is_done:
        try:
            return service.mark_done(followup_id, current_user)
        except FollowUpError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يوجد تعديل مدعوم غير is_done حاليًا")
