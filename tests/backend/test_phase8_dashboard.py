import uuid

from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, CustomerAssignment, Interaction, User
from app.models.enums import UserRole


def _manager(db, username="mgr8", password="Pass12345") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password(password), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _employee(db, username="emp8", password="Pass12345") -> User:
    u = User(username=username, full_name="موظفة", password_hash=hash_password(password), role=UserRole.EMPLOYEE)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def test_manager_dashboard_counts_are_accurate(db):
    manager = _manager(db, "mgr8_counts")

    client = TestClient(app)
    _login(client, "mgr8_counts")
    before = client.get("/api/v1/dashboard/manager").json()

    employee = _employee(db, "emp8_counts")

    c1 = Customer(customer_code="CUST-P8-1", name="ع1", phone="0100000801")
    c2 = Customer(customer_code="CUST-P8-2", name="ع2", phone="0100000802")
    c3 = Customer(customer_code="CUST-P8-3", name="ع3", phone="0100000803")
    db.add_all([c1, c2, c3])
    db.commit()
    db.refresh(c1)
    db.refresh(c2)
    db.refresh(c3)

    db.add(CustomerAssignment(customer_id=c1.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.add(CustomerAssignment(customer_id=c2.id, employee_id=employee.id, assigned_by_id=manager.id))
    db.commit()
    # c3 يبقى بلا تخصيص

    db.add(Interaction(customer_id=c1.id, employee_id=employee.id, channel="call", note="تم"))
    db.commit()
    # c2 مخصص لكن بلا تفاعل → يجب أن يظهر في customers_not_contacted

    resp = client.get("/api/v1/dashboard/manager")
    assert resp.status_code == 200
    body = resp.json()

    # مقارنة بالفارق (delta) بدل قيم مطلقة — قاعدة الاختبار مشتركة عبر كل الاختبارات في نفس التشغيلة
    assert body["total_customers"] - before["total_customers"] == 3
    assert body["assigned_customers"] - before["assigned_customers"] == 2
    assert body["unassigned_customers"] - before["unassigned_customers"] == 1
    assert body["total_employees"] - before["total_employees"] == 1
    assert body["customers_not_contacted"] - before["customers_not_contacted"] == 1  # c2 فقط


def test_employee_cannot_access_manager_dashboard(db):
    _employee(db, "emp8_forbidden")
    client = TestClient(app)
    _login(client, "emp8_forbidden")
    resp = client.get("/api/v1/dashboard/manager")
    assert resp.status_code == 403


def test_employee_workspace_reflects_own_data_only(db):
    manager = _manager(db, "mgr8_ws")
    emp1 = _employee(db, "emp8_ws1")
    emp2 = _employee(db, "emp8_ws2")

    c1 = Customer(customer_code="CUST-P8-WS1", name="ع", phone="0100000804")
    c2 = Customer(customer_code="CUST-P8-WS2", name="ع", phone="0100000805")
    db.add_all([c1, c2])
    db.commit()
    db.refresh(c1)
    db.refresh(c2)

    db.add(CustomerAssignment(customer_id=c1.id, employee_id=emp1.id, assigned_by_id=manager.id))
    db.add(CustomerAssignment(customer_id=c2.id, employee_id=emp2.id, assigned_by_id=manager.id))
    db.commit()

    db.add(Interaction(customer_id=c1.id, employee_id=emp1.id, channel="call"))
    db.commit()

    client = TestClient(app)
    _login(client, "emp8_ws1")
    resp = client.get("/api/v1/dashboard/my-workspace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["assigned_customers"] == 1
    assert body["contacted_today"] == 1
    assert body["not_contacted_today"] == 0


def test_employee_performance_reflects_orders_and_conversion(db):
    manager = _manager(db, "mgr8_perf")
    client = TestClient(app)
    _login(client, "mgr8_perf")

    emp_resp = client.post(
        "/api/v1/employees", json={"username": "emp8_perf", "full_name": "V", "password": "Pass12345"}
    )
    employee_id = emp_resp.json()["id"]

    product_resp = client.post(
        "/api/v1/products", json={"sku": "SKU-P8-PERF", "name_ar": "منتج", "variants": [{"unit_label": "1kg", "price": 100}]}
    )
    variant_id = product_resp.json()["variants"][0]["id"]

    customer = Customer(customer_code="CUST-P8-PERF", name="ع", phone="0100000806")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    client.post(
        "/api/v1/assignments/assign",
        json={"customer_ids": [str(customer.id)], "employee_id": employee_id},
    )

    emp_client = TestClient(app)
    _login(emp_client, "emp8_perf")
    emp_client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 1}],
        },
    )

    perf_resp = client.get("/api/v1/dashboard/employee-performance")
    assert perf_resp.status_code == 200
    rows = perf_resp.json()
    matching = [r for r in rows if r["employee_id"] == employee_id]
    assert len(matching) == 1
    row = matching[0]
    assert row["assigned_customers"] == 1
    assert row["orders_count"] == 1
    assert row["sales_total"] == 100
    assert row["conversion_rate"] == 100.0
