import uuid

from pydantic import BaseModel


class ImportPreviewRowOut(BaseModel):
    row_number: int
    customer_code: str | None
    source_customer_id: str | None
    phone: str | None
    name: str | None
    matched_customer_id: uuid.UUID | None = None
    match_reason: str | None = None


class ImportPreviewOut(BaseModel):
    total_rows: int
    matched_count: int
    missing_count: int
    duplicate_count: int
    invalid_count: int
    matched: list[ImportPreviewRowOut]
    missing: list[ImportPreviewRowOut]
    duplicate: list[ImportPreviewRowOut]
    invalid: list[ImportPreviewRowOut]


class ImportConfirmRequest(BaseModel):
    matched_customer_ids: list[uuid.UUID]
    employee_id: uuid.UUID
