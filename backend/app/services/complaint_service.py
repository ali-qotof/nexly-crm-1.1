import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Attachment, Complaint, User
from app.models.enums import UserRole
from app.services.access_control import CustomerAccessError, ensure_customer_access
from app.services.audit_service import write_audit_log


class ComplaintError(Exception):
    pass


class ComplaintService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data, actor: User) -> Complaint:
        try:
            ensure_customer_access(self.db, data.customer_id, actor)
        except CustomerAccessError as exc:
            raise ComplaintError(str(exc))

        complaint = Complaint(
            customer_id=data.customer_id,
            order_id=data.order_id,
            employee_id=actor.id,
            complaint_type=data.complaint_type,
            description=data.description,
        )
        self.db.add(complaint)
        self.db.commit()
        self.db.refresh(complaint)
        return complaint

    def get(self, complaint_id: uuid.UUID) -> Complaint | None:
        stmt = (
            select(Complaint)
            .options(selectinload(Complaint.attachments))
            .where(Complaint.id == complaint_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self, actor: User) -> list[Complaint]:
        stmt = select(Complaint).options(selectinload(Complaint.attachments)).order_by(
            Complaint.created_at.desc()
        )
        if actor.role != UserRole.SYSTEM_MANAGER:
            stmt = stmt.where(Complaint.employee_id == actor.id)
        return list(self.db.execute(stmt).scalars())

    def update_status(self, complaint_id: uuid.UUID, data, actor: User) -> Complaint:
        complaint = self.get(complaint_id)
        if complaint is None:
            raise ComplaintError("الشكوى غير موجودة")

        if data.status is not None:
            complaint.status = data.status
        if data.description is not None:
            complaint.description = data.description

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="complaint_updated",
            entity_type="complaint",
            entity_id=str(complaint.id),
            meta={"new_status": data.status.value if data.status else None},
        )
        self.db.commit()
        self.db.refresh(complaint)
        return complaint

    def add_attachment(self, complaint_id: uuid.UUID, file_url: str, file_name: str, actor: User) -> Attachment:
        complaint = self.get(complaint_id)
        if complaint is None:
            raise ComplaintError("الشكوى غير موجودة")

        attachment = Attachment(
            file_url=file_url, file_name=file_name, uploaded_by_id=actor.id, complaint_id=complaint_id
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment
