from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, CustomerAssignment, User
from app.models.enums import UserRole


def _manager(db, username="mgr4", password="Pass12345") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password(password), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def test_employee_creation_full_flow(db):
    _manager(db, "mgr4_create")
    client = TestClient(app)
    _login(client, "mgr4_create")

    resp = client.post(
        "/api/v1/employees",
        json={"username": "sara_new", "full_name": "ساره", "password": "EmpPass123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "sara_new"
    assert body["role"] == "EMPLOYEE"
    assert body["is_active"] is True

    # الموظفة الجديدة تستطيع تسجيل الدخول فورًا
    emp_client = TestClient(app)
    login_resp = emp_client.post(
        "/api/v1/auth/login", json={"username": "sara_new", "password": "EmpPass123"}
    )
    assert login_resp.status_code == 200


def test_duplicate_username_rejected(db):
    _manager(db, "mgr4_dup")
    client = TestClient(app)
    _login(client, "mgr4_dup")

    client.post("/api/v1/employees", json={"username": "dup_emp", "full_name": "A", "password": "Pass12345"})
    resp2 = client.post("/api/v1/employees", json={"username": "dup_emp", "full_name": "B", "password": "Pass12345"})
    assert resp2.status_code == 409


def test_employee_cannot_create_employees(db):
    from app.models import User as UserModel

    emp = UserModel(username="emp4_perm", full_name="X", password_hash=hash_password("Pass12345"), role=UserRole.EMPLOYEE)
    db.add(emp)
    db.commit()

    client = TestClient(app)
    _login(client, "emp4_perm")
    resp = client.post("/api/v1/employees", json={"username": "z", "full_name": "z", "password": "Pass12345678"})
    assert resp.status_code == 403


def test_disable_and_reenable_employee(db):
    _manager(db, "mgr4_disable")
    client = TestClient(app)
    _login(client, "mgr4_disable")

    create_resp = client.post(
        "/api/v1/employees", json={"username": "emp4_disable", "full_name": "Y", "password": "Pass12345"}
    )
    emp_id = create_resp.json()["id"]

    disable_resp = client.patch(f"/api/v1/employees/{emp_id}", json={"is_active": False})
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    # الموظفة المعطَّلة لا تستطيع تسجيل الدخول
    emp_client = TestClient(app)
    login_resp = emp_client.post(
        "/api/v1/auth/login", json={"username": "emp4_disable", "password": "Pass12345"}
    )
    assert login_resp.status_code == 401

    # إعادة التفعيل تُعيد القدرة على الدخول
    client.patch(f"/api/v1/employees/{emp_id}", json={"is_active": True})
    login_resp2 = emp_client.post(
        "/api/v1/auth/login", json={"username": "emp4_disable", "password": "Pass12345"}
    )
    assert login_resp2.status_code == 200


def test_delete_employee_requires_correct_manager_password(db):
    manager = _manager(db, "mgr4_delpw", password="ManagerRealPass1")
    client = TestClient(app)
    _login(client, "mgr4_delpw", password="ManagerRealPass1")

    create_resp = client.post(
        "/api/v1/employees", json={"username": "emp4_delpw", "full_name": "Z", "password": "Pass12345"}
    )
    emp_id = create_resp.json()["id"]

    wrong_pw_resp = client.post(
        f"/api/v1/employees/{emp_id}/delete", json={"manager_password": "WrongPassword"}
    )
    assert wrong_pw_resp.status_code == 401

    correct_pw_resp = client.post(
        f"/api/v1/employees/{emp_id}/delete", json={"manager_password": "ManagerRealPass1"}
    )
    assert correct_pw_resp.status_code == 204


def test_delete_employee_frees_customers_and_preserves_history(db):
    manager = _manager(db, "mgr4_delfree", password="ManagerRealPass2")
    client = TestClient(app)
    _login(client, "mgr4_delfree", password="ManagerRealPass2")

    create_resp = client.post(
        "/api/v1/employees", json={"username": "emp4_delfree", "full_name": "W", "password": "Pass12345"}
    )
    emp_id = create_resp.json()["id"]

    customer = Customer(customer_code="CUST-P4-DEL", name="ع", phone="0100000099")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    assign_resp = client.post(
        "/api/v1/assignments/assign", json={"customer_ids": [str(customer.id)], "employee_id": emp_id}
    )
    assert assign_resp.json()["assigned"] == 1

    delete_resp = client.post(
        f"/api/v1/employees/{emp_id}/delete", json={"manager_password": "ManagerRealPass2"}
    )
    assert delete_resp.status_code == 204

    from sqlalchemy import select

    stmt = select(CustomerAssignment).where(
        CustomerAssignment.customer_id == customer.id, CustomerAssignment.is_active.is_(True)
    )
    active_assignment = db.execute(stmt).scalar_one_or_none()
    assert active_assignment is None  # تحرر العميل فعليًا

    # الموظفة نفسها لا تزال موجودة (Soft delete فقط) وليست محذوفة فعليًا من قاعدة البيانات
    from sqlalchemy import select as sel

    employee_row = db.execute(sel(User).where(User.id == emp_id)).scalar_one_or_none()
    assert employee_row is not None
    assert employee_row.is_active is False
    assert employee_row.deleted_at is not None

    # لا تستطيع تسجيل الدخول بعد الحذف
    emp_client = TestClient(app)
    login_resp = emp_client.post(
        "/api/v1/auth/login", json={"username": "emp4_delfree", "password": "Pass12345"}
    )
    assert login_resp.status_code == 401


def test_employee_list_shows_assigned_customers_count(db):
    manager = _manager(db, "mgr4_count", password="ManagerRealPass3")
    client = TestClient(app)
    _login(client, "mgr4_count", password="ManagerRealPass3")

    create_resp = client.post(
        "/api/v1/employees", json={"username": "emp4_count", "full_name": "V", "password": "Pass12345"}
    )
    emp_id = create_resp.json()["id"]

    c1 = Customer(customer_code="CUST-P4-C1", name="ع1", phone="0100000091")
    c2 = Customer(customer_code="CUST-P4-C2", name="ع2", phone="0100000092")
    db.add_all([c1, c2])
    db.commit()
    db.refresh(c1)
    db.refresh(c2)

    client.post(
        "/api/v1/assignments/assign",
        json={"customer_ids": [str(c1.id), str(c2.id)], "employee_id": emp_id},
    )

    list_resp = client.get("/api/v1/employees")
    assert list_resp.status_code == 200
    matching = [e for e in list_resp.json() if e["id"] == emp_id]
    assert len(matching) == 1
    assert matching[0]["assigned_customers_count"] == 2
