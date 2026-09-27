from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated, require_manager
from app.db.session import get_db
from app.models import User
from app.schemas.dashboard import EmployeePerformanceRow, EmployeeWorkspaceOut, ManagerDashboardOut
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/manager", response_model=ManagerDashboardOut)
def manager_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """القاعدة 8: مؤشرات مجمّعة فقط — لا تحميل أي قوائم عملاء خام."""
    return DashboardService(db).manager_dashboard(date_from, date_to)


@router.get("/employee-performance", response_model=list[EmployeePerformanceRow])
def employee_performance(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """القاعدة 30: بدون Rankings أو Gamification — أرقام فقط."""
    return DashboardService(db).employee_performance(date_from, date_to)


@router.get("/my-workspace", response_model=EmployeeWorkspaceOut)
def my_workspace(current_user: User = Depends(require_any_authenticated), db: Session = Depends(get_db)):
    """القاعدة 29: مساحة عمل الموظفة الشخصية لليوم الحالي."""
    return DashboardService(db).employee_workspace(current_user.id)
