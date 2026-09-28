from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_manager
from app.db.session import get_db
from app.models import User
from app.services.audit_service import write_audit_log
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])
KINDS = {"customers", "orders", "assignments", "employees"}


@router.get("/{kind}")
def export(kind: str, fmt: str = Query(default="csv", pattern="^(csv|xlsx)$"),
           current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="نوع التصدير غير معروف")
    svc = ExportService(db)
    write_audit_log(db, user_id=current_user.id, action="data_exported", entity_type="export", entity_id=kind, meta={"format": fmt})
    db.commit()
    if fmt == "xlsx":
        return Response(svc.to_xlsx(kind), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{kind}.xlsx"'})
    return Response(svc.to_csv(kind), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'})
