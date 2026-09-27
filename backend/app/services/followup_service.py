import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FollowUp, User
from app.models.enums import UserRole
from app.services.access_control import CustomerAccessError, ensure_customer_access


class FollowUpError(Exception):
    pass


class FollowUpService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data, actor: User) -> FollowUp:
        try:
            ensure_customer_access(self.db, data.customer_id, actor)
        except CustomerAccessError as exc:
            raise FollowUpError(str(exc))

        followup = FollowUp(
            customer_id=data.customer_id, employee_id=actor.id, due_at=data.due_at, note=data.note
        )
        self.db.add(followup)
        self.db.commit()
        self.db.refresh(followup)
        return followup

    def list_for_employee(self, actor: User, bucket: str | None = None) -> list[FollowUp]:
        """
        القاعدة 26: Dashboard يعرض Due today / Overdue / Upcoming.
        bucket: 'due_today' | 'overdue' | 'upcoming' | None (كل شيء غير مكتمل).
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        stmt = select(FollowUp).where(FollowUp.is_done.is_(False))
        if actor.role != UserRole.SYSTEM_MANAGER:
            stmt = stmt.where(FollowUp.employee_id == actor.id)

        if bucket == "overdue":
            stmt = stmt.where(FollowUp.due_at < today_start)
        elif bucket == "due_today":
            stmt = stmt.where(FollowUp.due_at >= today_start, FollowUp.due_at < today_end)
        elif bucket == "upcoming":
            stmt = stmt.where(FollowUp.due_at >= today_end)

        stmt = stmt.order_by(FollowUp.due_at)
        return list(self.db.execute(stmt).scalars())

    def mark_done(self, followup_id: uuid.UUID, actor: User) -> FollowUp:
        followup = self.db.get(FollowUp, followup_id)
        if followup is None:
            raise FollowUpError("المتابعة غير موجودة")
        if actor.role != UserRole.SYSTEM_MANAGER and followup.employee_id != actor.id:
            raise FollowUpError("لا تملك صلاحية تعديل هذه المتابعة")

        followup.is_done = True
        self.db.commit()
        self.db.refresh(followup)
        return followup
