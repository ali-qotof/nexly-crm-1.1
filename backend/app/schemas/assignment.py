import uuid

from pydantic import BaseModel, Field


class AssignRequest(BaseModel):
    customer_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)
    employee_id: uuid.UUID


class UnassignRequest(BaseModel):
    customer_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)


class AssignmentResult(BaseModel):
    requested: int
    assigned: int
    skipped_already_assigned: int
    skipped_customer_ids: list[uuid.UUID] = []
