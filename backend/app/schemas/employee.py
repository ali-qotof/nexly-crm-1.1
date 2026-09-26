import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class EmployeeOut(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: str
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    assigned_customers_count: int = 0

    model_config = {"from_attributes": True}


class EmployeeDeleteRequest(BaseModel):
    manager_password: str = Field(min_length=1)
