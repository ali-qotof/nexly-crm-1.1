import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_authenticated, require_manager
from app.db.session import get_db
from app.models import User
from app.models.enums import OrderStatus
from app.schemas.order import OrderCreate, OrderOut, PaginatedOrders
from app.services.order_service import OrderError, OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    القاعدة 20/19: Idempotent + Backend = Source of Truth للحساب. نفس idempotency_key يُرجع
    نفس الطلب دائمًا مهما تكررت المحاولة (ضغط متكرر على "حفظ").
    """
    service = OrderService(db)
    try:
        order = service.create_order(payload, current_user)
    except OrderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return order


@router.get("", response_model=PaginatedOrders)
def list_orders(
    employee_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    order_status: OrderStatus | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    المدير يرى كل الطلبات (بفلاتر). الموظفة تُقيَّد تلقائيًا لطلباتها فقط — القاعدة 5 (عزل بيانات
    الموظفات) تمتد لتشمل الطلبات وليس فقط العملاء.
    """
    from app.models.enums import UserRole

    effective_employee_id = employee_id
    if current_user.role != UserRole.SYSTEM_MANAGER:
        effective_employee_id = current_user.id

    service = OrderService(db)
    items, total = service.list_orders(
        employee_id=effective_employee_id,
        customer_id=customer_id,
        status_filter=order_status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedOrders(items=items, total=total, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    from app.models.enums import UserRole

    order = OrderService(db).get_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطلب غير موجود")
    if current_user.role != UserRole.SYSTEM_MANAGER and order.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا تملك صلاحية رؤية هذا الطلب")
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: uuid.UUID,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """إلغاء طلب — مدير فقط."""
    try:
        return OrderService(db).cancel_order(order_id, current_user)
    except OrderError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
