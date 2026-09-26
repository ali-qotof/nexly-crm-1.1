import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.models import CustomerAssignment, User
from app.models.enums import UserRole
from app.services.audit_service import write_audit_log


class EmployeeError(Exception):
    pass


class EmployeeService:
    def __init__(self, db: Session):
        self.db = db

    def list_employees(self) -> list[tuple[User, int]]:
        count_sq = (
            select(
                CustomerAssignment.employee_id,
                func.count(CustomerAssignment.id).label("cnt"),
            )
            .where(CustomerAssignment.is_active.is_(True))
            .group_by(CustomerAssignment.employee_id)
            .subquery()
        )
        stmt = (
            select(User, func.coalesce(count_sq.c.cnt, 0))
            .outerjoin(count_sq, count_sq.c.employee_id == User.id)
            .where(User.role == UserRole.EMPLOYEE)
            .order_by(User.created_at.desc())
        )
        return list(self.db.execute(stmt).all())

    def create_employee(self, username: str, full_name: str, password: str, actor: User) -> User:
        existing = self.db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing is not None:
            raise EmployeeError(f"اسم المستخدم '{username}' مستخدَم بالفعل")

        employee = User(
            username=username,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.EMPLOYEE,
        )
        self.db.add(employee)
        self.db.flush()  # للحصول على employee.id قبل الـ commit من أجل الـ audit log

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="employee_created",
            entity_type="user",
            entity_id=str(employee.id),
            meta={"username": username},
        )
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def update_employee(
        self, employee_id: uuid.UUID, *, full_name: str | None, is_active: bool | None, actor: User
    ) -> User:
        employee = self._get_employee_or_raise(employee_id)

        changes = {}
        if full_name is not None:
            changes["full_name"] = (employee.full_name, full_name)
            employee.full_name = full_name
        if is_active is not None and is_active != employee.is_active:
            changes["is_active"] = (employee.is_active, is_active)
            employee.is_active = is_active

        if changes:
            write_audit_log(
                self.db,
                user_id=actor.id,
                action="employee_updated",
                entity_type="user",
                entity_id=str(employee.id),
                meta={k: {"from": v[0], "to": v[1]} for k, v in changes.items()},
            )
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def delete_employee(self, employee_id: uuid.UUID, manager_password: str, actor: User) -> None:
        """
        القاعدة 16: حذف الموظفة Manager only، ويتطلب كلمة مرور المدير الحالي (actor) قبل التنفيذ.
        ينفّذ Soft Delete فقط (تعطيل + deleted_at)، ويحرر كل عملائها المخصصين (Unassign)، ولا يحذف
        الأوردرات أو التفاعلات التاريخية إطلاقًا — تبقى مرتبطة بمعرّف المستخدم القديم للأرشفة.
        """
        if not verify_password(manager_password, actor.password_hash):
            raise EmployeeError("كلمة مرور المدير غير صحيحة")

        employee = self._get_employee_or_raise(employee_id)
        now = datetime.now(timezone.utc)

        freed_stmt = select(CustomerAssignment).where(
            CustomerAssignment.employee_id == employee_id,
            CustomerAssignment.is_active.is_(True),
        )
        freed_assignments = list(self.db.execute(freed_stmt).scalars())
        for assignment in freed_assignments:
            assignment.is_active = False
            assignment.unassigned_at = now

        employee.is_active = False
        employee.deleted_at = now

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="employee_deleted",
            entity_type="user",
            entity_id=str(employee.id),
            meta={"freed_customers_count": len(freed_assignments)},
        )
        self.db.commit()

    def _get_employee_or_raise(self, employee_id: uuid.UUID) -> User:
        employee = self.db.get(User, employee_id)
        if employee is None or employee.role != UserRole.EMPLOYEE:
            raise EmployeeError("الموظفة غير موجودة")
        return employee
