import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerAssignment, User
from app.models.enums import UserRole


class CustomerAccessError(Exception):
    pass


def ensure_customer_access(db: Session, customer_id: uuid.UUID, actor: User) -> Customer:
    """
    القاعدة 5: الموظفة لا تستطيع التعامل مع عملاء غير مخصصين لها (رؤية أو تسجيل تفاعل/متابعة/
    شكوى/أوردر). المدير يتجاوز هذا القيد دائمًا.
    """
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise CustomerAccessError("العميل غير موجود")

    if actor.role == UserRole.SYSTEM_MANAGER:
        return customer

    stmt = select(CustomerAssignment).where(
        CustomerAssignment.customer_id == customer_id,
        CustomerAssignment.employee_id == actor.id,
        CustomerAssignment.is_active.is_(True),
    )
    assignment = db.execute(stmt).scalar_one_or_none()
    if assignment is None:
        raise CustomerAccessError("هذا العميل غير مخصص لك")

    return customer
