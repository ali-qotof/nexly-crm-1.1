import io
import uuid

import openpyxl
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, CustomerAssignment, User
from app.models.enums import UserRole


def _manager(db, username="mgr3") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password("Pass12345"), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _employee(db, username="emp3") -> User:
    u = User(username=username, full_name="موظفة", password_hash=hash_password("Pass12345"), role=UserRole.EMPLOYEE)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _customer(db, code, name="عميل", phone="0100000001") -> Customer:
    c = Customer(customer_code=code, name=name, phone=phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp


def test_employee_cannot_list_all_customers(db):
    _manager(db, "mgr_a1")
    _employee(db, "emp_a1")
    client = TestClient(app)
    _login(client, "emp_a1")
    resp = client.get("/api/v1/customers")
    assert resp.status_code == 403


def test_manager_can_list_customers_with_pagination(db):
    _manager(db, "mgr_a2")
    for i in range(5):
        _customer(db, f"CUST-A2-{i}", name=f"عميل {i}", phone=f"010000000{i}")
    client = TestClient(app)
    _login(client, "mgr_a2")
    resp = client.get("/api/v1/customers?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 5
    assert len(body["items"]) == 2


def test_customer_search_by_phone(db):
    _manager(db, "mgr_a3")
    _customer(db, "CUST-SEARCH-1", name="محمد", phone="0122223333")
    client = TestClient(app)
    _login(client, "mgr_a3")
    resp = client.get("/api/v1/customers?q=0122223333")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["phone"] == "0122223333"


def test_employee_sees_only_assigned_customers(db):
    manager = _manager(db, "mgr_a4")
    emp1 = _employee(db, "emp_a4_1")
    emp2 = _employee(db, "emp_a4_2")
    c1 = _customer(db, "CUST-A4-1")
    c2 = _customer(db, "CUST-A4-2")

    db.add(CustomerAssignment(customer_id=c1.id, employee_id=emp1.id, assigned_by_id=manager.id))
    db.add(CustomerAssignment(customer_id=c2.id, employee_id=emp2.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "emp_a4_1")
    resp = client.get("/api/v1/customers/my")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["customer_code"] == "CUST-A4-1"


def test_bulk_assign_skips_already_assigned(db):
    manager = _manager(db, "mgr_a5")
    emp1 = _employee(db, "emp_a5_1")
    emp2 = _employee(db, "emp_a5_2")
    c1 = _customer(db, "CUST-A5-1")
    c2 = _customer(db, "CUST-A5-2")

    db.add(CustomerAssignment(customer_id=c1.id, employee_id=emp1.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "mgr_a5")
    resp = client.post(
        "/api/v1/assignments/assign",
        json={"customer_ids": [str(c1.id), str(c2.id)], "employee_id": str(emp2.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["requested"] == 2
    assert body["assigned"] == 1  # c1 already assigned to emp1, skipped
    assert body["skipped_already_assigned"] == 1


def test_unassign_then_reassign_works(db):
    manager = _manager(db, "mgr_a6")
    emp1 = _employee(db, "emp_a6_1")
    emp2 = _employee(db, "emp_a6_2")
    c1 = _customer(db, "CUST-A6-1")

    client = TestClient(app)
    _login(client, "mgr_a6")

    assign_resp = client.post(
        "/api/v1/assignments/assign", json={"customer_ids": [str(c1.id)], "employee_id": str(emp1.id)}
    )
    assert assign_resp.json()["assigned"] == 1

    reassign_resp = client.post(f"/api/v1/assignments/{c1.id}/reassign/{emp2.id}")
    assert reassign_resp.status_code == 200

    my_resp_emp2 = TestClient(app)
    _login(my_resp_emp2, "emp_a6_2")
    my_customers = my_resp_emp2.get("/api/v1/customers/my").json()
    assert my_customers["total"] == 1
    assert my_customers["items"][0]["customer_code"] == "CUST-A6-1"

    my_resp_emp1 = TestClient(app)
    _login(my_resp_emp1, "emp_a6_1")
    my_customers_emp1 = my_resp_emp1.get("/api/v1/customers/my").json()
    assert my_customers_emp1["total"] == 0


def test_excel_import_preview_and_confirm(db):
    manager = _manager(db, "mgr_a7")
    employee = _employee(db, "emp_a7")
    c1 = _customer(db, "CUST-A7-1", phone="0111111111")
    c2 = _customer(db, "CUST-A7-2", phone="0122222222")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["customer_id", "phone", "name"])
    ws.append(["CUST-A7-1", "", "أحمد"])
    ws.append(["", "0122222222", "سارة"])
    ws.append(["", "0199999999", "غير موجود"])  # missing
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    client = TestClient(app)
    _login(client, "mgr_a7")

    preview_resp = client.post(
        "/api/v1/assignments/import/preview",
        files={"file": ("test.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["total_rows"] == 3
    assert preview["matched_count"] == 2
    assert preview["missing_count"] == 1

    matched_ids = [row["matched_customer_id"] for row in preview["matched"]]
    confirm_resp = client.post(
        "/api/v1/assignments/import/confirm",
        json={"matched_customer_ids": matched_ids, "employee_id": str(employee.id)},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["assigned"] == 2


def test_import_never_creates_new_customers(db):
    """القاعدة 15: لا يتم إنشاء عملاء جدد من Assignment Import."""
    manager = _manager(db, "mgr_a8")
    from sqlalchemy import select

    before_count = db.execute(select(Customer)).scalars().all()
    before = len(before_count)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["customer_id", "phone", "name"])
    ws.append(["NON-EXISTENT-CODE", "", "شخص غير موجود"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    client = TestClient(app)
    _login(client, "mgr_a8")
    preview_resp = client.post(
        "/api/v1/assignments/import/preview",
        files={"file": ("test.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert preview_resp.json()["missing_count"] == 1

    after_count = len(db.execute(select(Customer)).scalars().all())
    assert after_count == before  # لم يُنشأ أي عميل جديد


def test_customer_detail_access_control(db):
    manager = _manager(db, "mgr3_detail")
    emp1 = _employee(db, "emp3_detail1")
    emp2 = _employee(db, "emp3_detail2")
    c = _customer(db, "CUST-DETAIL-1", phone="0155555555")
    db.add(CustomerAssignment(customer_id=c.id, employee_id=emp1.id, assigned_by_id=manager.id))
    db.commit()

    owner = TestClient(app); _login(owner, "emp3_detail1")
    assert owner.get(f"/api/v1/customers/{c.id}").json()["customer_code"] == "CUST-DETAIL-1"

    other = TestClient(app); _login(other, "emp3_detail2")
    assert other.get(f"/api/v1/customers/{c.id}").status_code == 403

    mgr = TestClient(app); _login(mgr, "mgr3_detail")
    assert mgr.get(f"/api/v1/customers/{c.id}").status_code == 200
    assert mgr.get(f"/api/v1/customers/{uuid.uuid4()}").status_code == 404
