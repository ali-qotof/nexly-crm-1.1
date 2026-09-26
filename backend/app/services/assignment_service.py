import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerAssignment, User
from app.models.enums import UserRole
from app.schemas.assignment import AssignmentResult
from app.services.audit_service import write_audit_log


class AssignmentError(Exception):
    pass


class AssignmentService:
    """
    القاعدة 13: Assign/Reassign/Unassign/Bulk، مع منع Duplicate assignment (مضمون أيضًا على
    مستوى DB عبر partial unique index — راجع app/models/customer.py) ومنع إعادة الترتيب العشوائي
    (القاعدة 67: employee_order يُحفظ ولا يُعاد حسابه عشوائيًا بعد كل عملية).
    """

    def __init__(self, db: Session):
        self.db = db

    def _next_order_for_employee(self, employee_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(CustomerAssignment.employee_order), 0)).where(
            CustomerAssignment.employee_id == employee_id,
            CustomerAssignment.is_active.is_(True),
        )
        current_max = self.db.execute(stmt).scalar_one()
        return current_max + 1

    def _get_active_assignment(self, customer_id: uuid.UUID) -> CustomerAssignment | None:
        stmt = select(CustomerAssignment).where(
            CustomerAssignment.customer_id == customer_id,
            CustomerAssignment.is_active.is_(True),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def bulk_assign(
        self, customer_ids: list[uuid.UUID], employee_id: uuid.UUID, actor: User
    ) -> AssignmentResult:
        employee = self.db.get(User, employee_id)
        if employee is None or employee.role != UserRole.EMPLOYEE or not employee.is_active:
            raise AssignmentError("الموظفة المحددة غير موجودة أو غير نشطة")

        # إزالة التكرار من نفس الطلب
        unique_ids = list(dict.fromkeys(customer_ids))

        # استبعاد من له تخصيص نشط بالفعل (لأي موظفة) — القاعدة 13: منع Duplicate assignment
        existing_stmt = select(CustomerAssignment.customer_id).where(
            CustomerAssignment.customer_id.in_(unique_ids),
            CustomerAssignment.is_active.is_(True),
        )
        already_assigned = {row for row in self.db.execute(existing_stmt).scalars()}

        to_assign = [cid for cid in unique_ids if cid not in already_assigned]

        next_order = self._next_order_for_employee(employee_id)
        for offset, customer_id in enumerate(to_assign):
            assignment = CustomerAssignment(
                customer_id=customer_id,
                employee_id=employee_id,
                assigned_by_id=actor.id,
                employee_order=next_order + offset,
            )
            self.db.add(assignment)

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="customer_assigned_bulk",
            entity_type="assignment",
            entity_id=str(employee_id),
            meta={"assigned_count": len(to_assign), "skipped_count": len(already_assigned)},
        )
        self.db.commit()

        return AssignmentResult(
            requested=len(unique_ids),
            assigned=len(to_assign),
            skipped_already_assigned=len(already_assigned),
            skipped_customer_ids=list(already_assigned),
        )

    def bulk_unassign(self, customer_ids: list[uuid.UUID], actor: User) -> AssignmentResult:
        unique_ids = list(dict.fromkeys(customer_ids))
        now = datetime.now(timezone.utc)

        stmt = select(CustomerAssignment).where(
            CustomerAssignment.customer_id.in_(unique_ids),
            CustomerAssignment.is_active.is_(True),
        )
        rows = list(self.db.execute(stmt).scalars())
        for row in rows:
            row.is_active = False
            row.unassigned_at = now

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="customer_unassigned_bulk",
            entity_type="assignment",
            entity_id=None,
            meta={"unassigned_count": len(rows), "customer_ids": [str(c) for c in unique_ids]},
        )
        self.db.commit()

        skipped = len(unique_ids) - len(rows)
        return AssignmentResult(
            requested=len(unique_ids), assigned=len(rows), skipped_already_assigned=skipped
        )

    def reassign(
        self, customer_id: uuid.UUID, new_employee_id: uuid.UUID, actor: User
    ) -> CustomerAssignment:
        employee = self.db.get(User, new_employee_id)
        if employee is None or employee.role != UserRole.EMPLOYEE or not employee.is_active:
            raise AssignmentError("الموظفة المحددة غير موجودة أو غير نشطة")

        customer = self.db.get(Customer, customer_id)
        if customer is None:
            raise AssignmentError("العميل غير موجود")

        current = self._get_active_assignment(customer_id)
        now = datetime.now(timezone.utc)
        if current is not None:
            current.is_active = False
            current.unassigned_at = now

        next_order = self._next_order_for_employee(new_employee_id)
        new_assignment = CustomerAssignment(
            customer_id=customer_id,
            employee_id=new_employee_id,
            assigned_by_id=actor.id,
            employee_order=next_order,
        )
        self.db.add(new_assignment)

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="customer_reassigned",
            entity_type="customer",
            entity_id=str(customer_id),
            meta={
                "from_employee_id": str(current.employee_id) if current else None,
                "to_employee_id": str(new_employee_id),
            },
        )
        self.db.commit()
        self.db.refresh(new_assignment)
        return new_assignment
