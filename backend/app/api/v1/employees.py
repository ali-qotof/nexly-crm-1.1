import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_manager
from app.db.session import get_db
from app.models import User
from app.schemas.employee import EmployeeCreate, EmployeeDeleteRequest, EmployeeOut, EmployeeUpdate
from app.services.employee_service import EmployeeError, EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


def _to_out(user: User, assigned_count: int = 0) -> EmployeeOut:
    return EmployeeOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        deleted_at=user.deleted_at,
        created_at=user.created_at,
        assigned_customers_count=assigned_count,
    )


@router.get("", response_model=list[EmployeeOut])
def list_employees(current_user: User = Depends(require_manager), db: Session = Depends(get_db)):
    service = EmployeeService(db)
    return [_to_out(u, count) for u, count in service.list_employees()]


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """
    القاعدة 14: بعد إنشاء الموظفة مباشرة، الخطوة التالية في الواجهة هي إسناد العملاء لها
    (عبر /api/v1/assignments/assign أو /import/*) — لا تُنشأ هنا لأنها منطقة مسؤولية منفصلة
    (فصل الطبقات، القاعدة 4).
    """
    service = EmployeeService(db)
    try:
        employee = service.create_employee(
            payload.username, payload.full_name, payload.password, current_user
        )
    except EmployeeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_out(employee)


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """يُستخدم أيضًا للتعطيل/إعادة التفعيل عبر is_active (القاعدة 5)."""
    service = EmployeeService(db)
    try:
        employee = service.update_employee(
            employee_id, full_name=payload.full_name, is_active=payload.is_active, actor=current_user
        )
    except EmployeeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_out(employee)


@router.post("/{employee_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: uuid.UUID,
    payload: EmployeeDeleteRequest,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """القاعدة 16: يتطلب كلمة مرور المدير. Soft delete فقط، يحرر عملاءها، لا يحذف تاريخها."""
    service = EmployeeService(db)
    try:
        service.delete_employee(employee_id, payload.manager_password, current_user)
    except EmployeeError as exc:
        code = (
            status.HTTP_401_UNAUTHORIZED
            if "كلمة مرور" in str(exc)
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=str(exc))
