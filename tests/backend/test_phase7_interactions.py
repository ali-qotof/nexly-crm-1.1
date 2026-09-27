import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, CustomerAssignment, User
from app.models.enums import UserRole


def _manager(db, username="mgr7", password="Pass12345") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password(password), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _employee(db, username="emp7", password="Pass12345") -> User:
    u = User(username=username, full_name="موظفة", password_hash=hash_password(password), role=UserRole.EMPLOYEE)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def _customer(db, code) -> Customer:
    c = Customer(customer_code=code, name="عميل", phone=f"010{code[-7:]}")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_employee_cannot_interact_with_unassigned_customer(db):
    _employee(db, "emp7_unassigned")
    customer = _customer(db, "CUST-P7-UN1")
    client = TestClient(app)
    _login(client, "emp7_unassigned")

    resp = client.post(
        "/api/v1/interactions",
        json={"customer_id": str(customer.id), "channel": "call", "note": "محاولة"},
    )
    assert resp.status_code == 403


def test_employee_can_interact_with_assigned_customer_and_timeline_orders_desc(db):
    manager = _manager(db, "mgr7_ok")
    employee = _employee(db, "emp7_ok")
    customer = _customer(db, "CUST-P7-OK1")

    db.add(CustomerAssignment(customer_id=customer.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "emp7_ok")

    r1 = client.post("/api/v1/interactions", json={"customer_id": str(customer.id), "channel": "call", "note": "أول اتصال"})
    assert r1.status_code == 201
    r2 = client.post("/api/v1/interactions", json={"customer_id": str(customer.id), "channel": "whatsapp", "status_code": "no_answer"})
    assert r2.status_code == 201

    timeline = client.get(f"/api/v1/customers/{customer.id}/interactions").json()
    assert len(timeline) == 2
    assert timeline[0]["channel"] == "whatsapp"  # الأحدث أولًا


def test_followup_buckets_due_today_overdue_upcoming(db):
    manager = _manager(db, "mgr7_fu")
    employee = _employee(db, "emp7_fu")
    customer = _customer(db, "CUST-P7-FU1")
    db.add(CustomerAssignment(customer_id=customer.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "emp7_fu")

    now = datetime.now(timezone.utc)
    overdue_at = (now - timedelta(days=2)).isoformat()
    today_at = now.isoformat()
    upcoming_at = (now + timedelta(days=5)).isoformat()

    for due_at in [overdue_at, today_at, upcoming_at]:
        resp = client.post(
            "/api/v1/followups", json={"customer_id": str(customer.id), "due_at": due_at, "note": "متابعة"}
        )
        assert resp.status_code == 201

    overdue = client.get("/api/v1/followups?bucket=overdue").json()
    due_today = client.get("/api/v1/followups?bucket=due_today").json()
    upcoming = client.get("/api/v1/followups?bucket=upcoming").json()

    assert len(overdue) == 1
    assert len(due_today) == 1
    assert len(upcoming) == 1


def test_followup_mark_done_removes_from_active_lists(db):
    manager = _manager(db, "mgr7_done")
    employee = _employee(db, "emp7_done")
    customer = _customer(db, "CUST-P7-DONE1")
    db.add(CustomerAssignment(customer_id=customer.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "emp7_done")

    create_resp = client.post(
        "/api/v1/followups",
        json={"customer_id": str(customer.id), "due_at": datetime.now(timezone.utc).isoformat()},
    )
    followup_id = create_resp.json()["id"]

    all_active = client.get("/api/v1/followups").json()
    assert len(all_active) == 1

    done_resp = client.patch(f"/api/v1/followups/{followup_id}", json={"is_done": True})
    assert done_resp.status_code == 200
    assert done_resp.json()["is_done"] is True

    all_active_after = client.get("/api/v1/followups").json()
    assert len(all_active_after) == 0


def test_complaint_creation_and_status_update_with_attachment(db):
    manager = _manager(db, "mgr7_complaint")
    employee = _employee(db, "emp7_complaint")
    customer = _customer(db, "CUST-P7-COMP1")
    db.add(CustomerAssignment(customer_id=customer.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "emp7_complaint")

    create_resp = client.post(
        "/api/v1/complaints",
        json={"customer_id": str(customer.id), "complaint_type": "تأخير شحن", "description": "الطلب متأخر 3 أيام"},
    )
    assert create_resp.status_code == 201
    complaint_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "OPEN"

    # رفع صورة كمرفق
    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0fakejpegcontent")
    upload_resp = client.post(
        f"/api/v1/complaints/{complaint_id}/attachments",
        files={"file": ("proof.jpg", fake_image.read(), "image/jpeg")},
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["file_name"] == "proof.jpg"

    # المدير يحدّث الحالة
    mgr_client = TestClient(app)
    _login(mgr_client, "mgr7_complaint")
    update_resp = mgr_client.patch(f"/api/v1/complaints/{complaint_id}", json={"status": "RESOLVED"})
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "RESOLVED"
    assert len(update_resp.json()["attachments"]) == 1


def test_complaint_rejects_disallowed_file_type(db):
    manager = _manager(db, "mgr7_badfile")
    employee = _employee(db, "emp7_badfile")
    customer = _customer(db, "CUST-P7-BAD1")
    db.add(CustomerAssignment(customer_id=customer.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.commit()

    client = TestClient(app)
    _login(client, "emp7_badfile")
    complaint_resp = client.post(
        "/api/v1/complaints",
        json={"customer_id": str(customer.id), "complaint_type": "شكوى", "description": "وصف"},
    )
    complaint_id = complaint_resp.json()["id"]

    bad_file = io.BytesIO(b"not really an exe but wrong extension")
    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/attachments",
        files={"file": ("virus.exe", bad_file.read(), "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_order_creation_blocked_for_unassigned_customer(db):
    """اختبار رجعي: يمنع منتجات PHASE 6 (الأوردرات) من العمل على عميل غير مخصص للموظفة."""
    manager = _manager(db, "mgr7_orderacl")
    employee = _employee(db, "emp7_orderacl")
    customer = _customer(db, "CUST-P7-ORDERACL")

    mgr_client = TestClient(app)
    _login(mgr_client, "mgr7_orderacl")
    product_resp = mgr_client.post(
        "/api/v1/products", json={"sku": "SKU-P7-ACL", "name_ar": "منتج", "variants": [{"unit_label": "1kg", "price": 50}]}
    )
    variant_id = product_resp.json()["variants"][0]["id"]

    emp_client = TestClient(app)
    _login(emp_client, "emp7_orderacl")
    resp = emp_client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 1}],
        },
    )
    assert resp.status_code == 400
    assert "غير مخصص" in resp.json()["detail"]
