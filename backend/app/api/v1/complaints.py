import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated
from app.db.session import get_db
from app.models import User
from app.schemas.interaction import AttachmentOut, ComplaintCreate, ComplaintOut, ComplaintUpdate
from app.services.complaint_service import ComplaintError, ComplaintService
from app.utils.file_storage import FileStorageError, save_upload

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(
    payload: ComplaintCreate,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    try:
        return ComplaintService(db).create(payload, current_user)
    except ComplaintError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("", response_model=list[ComplaintOut])
def list_complaints(current_user: User = Depends(require_any_authenticated), db: Session = Depends(get_db)):
    return ComplaintService(db).list_all(current_user)


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: uuid.UUID, current_user: User = Depends(require_any_authenticated), db: Session = Depends(get_db)):
    complaint = ComplaintService(db).get(complaint_id)
    if complaint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الشكوى غير موجودة")
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintUpdate,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    try:
        return ComplaintService(db).update_status(complaint_id, payload, current_user)
    except ComplaintError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{complaint_id}/attachments", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    complaint_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        file_url, stored_name = save_upload(content, file.filename or "upload")
        return ComplaintService(db).add_attachment(complaint_id, file_url, file.filename or stored_name, current_user)
    except FileStorageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ComplaintError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
