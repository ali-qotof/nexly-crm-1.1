import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_manager
from app.db.session import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    meta: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AuditPage)
def list_audit(action: str | None = Query(default=None), page: int = Query(default=1, ge=1),
               page_size: int = Query(default=50, ge=1, le=200),
               current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    cond = [AuditLog.action == action] if action else []
    total = db.execute(select(func.count(AuditLog.id)).where(*cond)).scalar_one()
    rows = db.execute(select(AuditLog).where(*cond).order_by(AuditLog.created_at.desc())
                      .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return AuditPage(items=list(rows), total=total, page=page, page_size=page_size)
