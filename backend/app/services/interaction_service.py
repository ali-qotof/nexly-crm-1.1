import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Interaction, User
from app.services.access_control import CustomerAccessError, ensure_customer_access


class InteractionError(Exception):
    pass


class InteractionService:
    def __init__(self, db: Session):
        self.db = db

    def create_interaction(self, data, actor: User) -> Interaction:
        try:
            ensure_customer_access(self.db, data.customer_id, actor)
        except CustomerAccessError as exc:
            raise InteractionError(str(exc))

        interaction = Interaction(
            customer_id=data.customer_id,
            employee_id=actor.id,
            channel=data.channel,
            status_code=data.status_code,
            note=data.note,
        )
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    def list_timeline(self, customer_id: uuid.UUID, actor: User) -> list[Interaction]:
        try:
            ensure_customer_access(self.db, customer_id, actor)
        except CustomerAccessError as exc:
            raise InteractionError(str(exc))

        stmt = (
            select(Interaction)
            .where(Interaction.customer_id == customer_id)
            .order_by(Interaction.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars())
