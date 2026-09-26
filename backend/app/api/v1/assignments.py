import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_manager
from app.db.session import get_db
from app.models import User
from app.schemas.assignment import AssignmentResult, AssignRequest, UnassignRequest
from app.schemas.import_ import ImportConfirmRequest, ImportPreviewOut, ImportPreviewRowOut
from app.services.assignment_service import AssignmentError, AssignmentService
from app.services.import_service import CustomerImportService

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _row_to_out(row) -> ImportPreviewRowOut:
    return ImportPreviewRowOut(
        row_number=row.row_number,
        customer_code=row.customer_code,
        source_customer_id=row.source_customer_id,
        phone=row.phone,
        name=row.name,
        matched_customer_id=row.matched_customer_id,
        match_reason=row.match_reason,
    )


@router.post("/import/preview", response_model=ImportPreviewOut)
async def import_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """
    معاينة ملف Import قبل التنفيذ (القاعدة 15): Total/Matched/Missing/Duplicate/Invalid.
    لا يُنشئ أي عميل جديد ولا يوزّع أي شيء بعد — فقط مطابقة وعرض.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الملف فارغ")

    service = CustomerImportService(db)
    try:
        rows = service.parse_rows(content, file.filename or "")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="تعذّر قراءة الملف")

    preview = service.build_preview(rows)
    return ImportPreviewOut(
        total_rows=preview.total_rows,
        matched_count=len(preview.matched),
        missing_count=len(preview.missing),
        duplicate_count=len(preview.duplicate),
        invalid_count=len(preview.invalid),
        matched=[_row_to_out(r) for r in preview.matched],
        missing=[_row_to_out(r) for r in preview.missing],
        duplicate=[_row_to_out(r) for r in preview.duplicate],
        invalid=[_row_to_out(r) for r in preview.invalid],
    )


@router.post("/import/confirm", response_model=AssignmentResult)
def import_confirm(
    payload: ImportConfirmRequest,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """تنفيذ التوزيع الفعلي بعد موافقة المدير على المعاينة (القاعدة 15: Preview → Confirm → Execute)."""
    service = AssignmentService(db)
    try:
        return service.bulk_assign(payload.matched_customer_ids, payload.employee_id, current_user)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/assign", response_model=AssignmentResult)
def assign_customers(
    payload: AssignRequest,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """توزيع عملاء على موظفة (Bulk، أو عميل واحد ضمن قائمة من عنصر واحد) — القاعدة 13."""
    service = AssignmentService(db)
    try:
        return service.bulk_assign(payload.customer_ids, payload.employee_id, current_user)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/unassign", response_model=AssignmentResult)
def unassign_customers(
    payload: UnassignRequest,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """سحب عملاء من موظفاتهم الحاليات — القاعدة 13."""
    service = AssignmentService(db)
    return service.bulk_unassign(payload.customer_ids, current_user)


@router.post("/{customer_id}/reassign/{new_employee_id}")
def reassign_customer(
    customer_id: uuid.UUID,
    new_employee_id: uuid.UUID,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """إعادة توزيع عميل واحد من موظفة إلى أخرى في عملية واحدة atomically."""
    service = AssignmentService(db)
    try:
        result = service.reassign(customer_id, new_employee_id, current_user)
    except AssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"customer_id": str(customer_id), "new_employee_id": str(new_employee_id), "assignment_id": str(result.id)}
