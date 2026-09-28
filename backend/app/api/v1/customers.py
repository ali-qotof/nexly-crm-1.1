import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated, require_manager
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.customer import CustomerOut, PaginatedCustomers
from app.services.access_control import CustomerAccessError, ensure_customer_access
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=PaginatedCustomers)
def list_customers(
    q: str | None = Query(default=None, description="بحث بالاسم/الهاتف/الكود"),
    unassigned_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """قائمة كل العملاء — للمدير فقط (القاعدة 9). الموظفة تستخدم /customers/my."""
    service = CustomerService(db)
    return service.list_customers(q=q, unassigned_only=unassigned_only, page=page, page_size=page_size)


@router.get("/my", response_model=PaginatedCustomers)
def list_my_customers(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    عملائي — الموظفة ترى فقط عملاءها المخصصين (القاعدة 5: لا تستطيع رؤية عملاء موظفات أخريات).
    المدير أيضًا يمكنه استخدامها لمعاينة نفس الشاشة، لكن دائمًا مقيّدة بمعرّف المستخدم الحالي فقط.
    """
    service = CustomerService(db)
    return service.list_customers(q=q, employee_id=current_user.id, page=page, page_size=page_size)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: uuid.UUID,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """تفاصيل عميل — الموظفة فقط لعملائها المخصصين (القاعدة 5)، المدير لأي عميل."""
    try:
        return ensure_customer_access(db, customer_id, current_user)
    except CustomerAccessError as exc:
        code = status.HTTP_404_NOT_FOUND if "غير موجود" in str(exc) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=code, detail=str(exc))
