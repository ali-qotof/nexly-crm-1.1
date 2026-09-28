"""تصدير CSV/XLSX (القاعدة 31). يُبنى في الذاكرة بالتدفق على دفعات (yield_per) لتفادي تحميل كل
الصفوف مرة واحدة. حماية من CSV/Formula injection: أي قيمة نصية تبدأ بـ = + - @ تُسبق بعلامة '."""
import csv
import io

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerAssignment, Order, User
from app.models.enums import UserRole

_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def _safe(v):
    if isinstance(v, str) and v.startswith(_DANGEROUS):
        return "'" + v
    if v is None:
        return ""
    return v if isinstance(v, (int, float, str)) else str(v)


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def _rows(self, kind: str):
        if kind == "customers":
            yield ["customer_code", "source_customer_id", "name", "phone", "whatsapp", "governorate", "address"]
            stmt = select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.customer_code)
            for c in self.db.execute(stmt).scalars().yield_per(2000):
                yield [c.customer_code, c.source_customer_id, c.name, c.phone, c.whatsapp, c.governorate, c.address]
        elif kind == "orders":
            yield ["order_number", "customer_code", "employee", "created_at", "subtotal", "discount", "shipping", "total", "status"]
            stmt = (select(Order, Customer.customer_code, User.full_name)
                    .join(Customer, Customer.id == Order.customer_id).join(User, User.id == Order.employee_id)
                    .order_by(Order.created_at.desc()))
            for o, code, emp in self.db.execute(stmt).yield_per(2000):
                yield [o.order_number, code, emp, o.created_at.isoformat(), float(o.subtotal), float(o.discount_amount),
                       float(o.shipping_amount), float(o.total_amount), o.status.value]
        elif kind == "assignments":
            yield ["customer_code", "customer_name", "employee", "employee_order"]
            stmt = (select(Customer.customer_code, Customer.name, User.full_name, CustomerAssignment.employee_order)
                    .join(CustomerAssignment, CustomerAssignment.customer_id == Customer.id)
                    .join(User, User.id == CustomerAssignment.employee_id)
                    .where(CustomerAssignment.is_active.is_(True)).order_by(User.full_name, CustomerAssignment.employee_order))
            for row in self.db.execute(stmt).yield_per(2000):
                yield list(row)
        elif kind == "employees":
            yield ["username", "full_name", "is_active", "created_at"]
            stmt = select(User).where(User.role == UserRole.EMPLOYEE, User.deleted_at.is_(None)).order_by(User.created_at)
            for u in self.db.execute(stmt).scalars():
                yield [u.username, u.full_name, u.is_active, u.created_at.isoformat()]
        else:
            raise ValueError(kind)

    def to_csv(self, kind: str) -> bytes:
        buf = io.StringIO()
        w = csv.writer(buf)
        for row in self._rows(kind):
            w.writerow([_safe(v) for v in row])
        return ("\ufeff" + buf.getvalue()).encode("utf-8")  # BOM ليفتح العربي صحيحًا في Excel

    def to_xlsx(self, kind: str) -> bytes:
        wb = openpyxl.Workbook(write_only=True)
        ws = wb.create_sheet(kind)
        for row in self._rows(kind):
            ws.append([_safe(v) for v in row])
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()
