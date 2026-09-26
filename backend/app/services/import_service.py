"""
مطابقة عملاء من ملف Excel/CSV لتوزيعهم على موظفة (القاعدة 15).

القاعدة صريحة: Import Assignment لا ينشئ عملاء جدد أبدًا — فقط يطابق عملاء موجودين بالفعل
ويجهّزهم للتوزيع. المطابقة بالأولوية: Customer ID (customer_code) → Source Customer ID → هاتف مُطبَّع.
"""
import io
import re
import uuid
from dataclasses import dataclass, field

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer


def normalize_phone(raw: str) -> str:
    """يزيل كل شيء عدا الأرقام، ويوحّد صيغة الأرقام المصرية (يحذف صفر الدولي/رمز الدولة الشائع)."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("20") and len(digits) > 10:
        digits = digits[2:]
    if not digits.startswith("0") and len(digits) == 10:
        digits = "0" + digits
    return digits


@dataclass
class ImportPreviewRow:
    row_number: int
    customer_code: str | None
    source_customer_id: str | None
    phone: str | None
    name: str | None
    matched_customer_id: uuid.UUID | None = None
    match_reason: str | None = None


@dataclass
class ImportPreview:
    total_rows: int
    matched: list[ImportPreviewRow] = field(default_factory=list)
    missing: list[ImportPreviewRow] = field(default_factory=list)
    duplicate: list[ImportPreviewRow] = field(default_factory=list)
    invalid: list[ImportPreviewRow] = field(default_factory=list)


class CustomerImportService:
    def __init__(self, db: Session):
        self.db = db

    def parse_rows(self, file_bytes: bytes, filename: str) -> list[dict]:
        """يدعم .xlsx و.csv. العمود الأول من صف العناوين يُستخدم للمطابقة بالاسم (case-insensitive)."""
        if filename.lower().endswith(".csv"):
            import csv

            text = file_bytes.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return [
                {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                for row in reader
            ]

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower() for h in next(rows_iter)]
        result = []
        for row in rows_iter:
            if all(cell is None for cell in row):
                continue
            result.append(
                {headers[i]: ("" if row[i] is None else str(row[i]).strip()) for i in range(len(headers))}
            )
        return result

    def build_preview(self, rows: list[dict]) -> ImportPreview:
        preview = ImportPreview(total_rows=len(rows))
        seen_matches: set[uuid.UUID] = set()

        for idx, row in enumerate(rows, start=2):  # الصف 1 عناوين
            customer_code = row.get("customer id") or row.get("customer_id") or None
            source_id = row.get("source customer id") or row.get("source_customer_id") or None
            phone = row.get("phone") or row.get("mobile") or None
            name = row.get("name") or None

            parsed = ImportPreviewRow(
                row_number=idx,
                customer_code=customer_code or None,
                source_customer_id=source_id or None,
                phone=phone or None,
                name=name or None,
            )

            if not customer_code and not source_id and not phone:
                preview.invalid.append(parsed)
                continue

            match: Customer | None = None
            if customer_code:
                match = self.db.execute(
                    select(Customer).where(Customer.customer_code == customer_code)
                ).scalar_one_or_none()
                if match:
                    parsed.match_reason = "customer_code"
            if match is None and source_id:
                match = self.db.execute(
                    select(Customer).where(Customer.source_customer_id == source_id)
                ).scalar_one_or_none()
                if match:
                    parsed.match_reason = "source_customer_id"
            if match is None and phone:
                normalized = normalize_phone(phone)
                match = self.db.execute(
                    select(Customer).where(Customer.phone == normalized)
                ).scalar_one_or_none()
                if match:
                    parsed.match_reason = "phone"

            if match is None:
                preview.missing.append(parsed)
                continue

            if match.id in seen_matches:
                preview.duplicate.append(parsed)
                continue

            seen_matches.add(match.id)
            parsed.matched_customer_id = match.id
            preview.matched.append(parsed)

        return preview
