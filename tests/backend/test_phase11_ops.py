import io

import openpyxl
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, User
from app.models.enums import UserRole


def _user(db, username, role, password="Pass12345"):
    u = User(username=username, full_name="م", password_hash=hash_password(password), role=role)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(client, username, password="Pass12345"):
    assert client.post("/api/v1/auth/login", json={"username": username, "password": password}).status_code == 200


def test_health_reports_database_and_version_without_secrets():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert {"version", "git_commit", "build_time", "environment", "timestamp", "db_migration"} <= set(body)
    text = r.text.lower()
    assert "password" not in text and "postgresql" not in text and "secret" not in text


def test_health_returns_503_when_database_down(monkeypatch):
    import app.main as main
    class Broken:
        def connect(self): raise RuntimeError("db down")
    monkeypatch.setattr(main, "engine", Broken())
    r = TestClient(app).get("/health")
    assert r.status_code == 503 and r.json()["database"] == "unavailable"


def test_request_id_and_security_headers_present():
    r = TestClient(app).get("/health", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_export_customers_csv_and_xlsx_manager_only(db):
    _user(db, "mgr11_exp", UserRole.SYSTEM_MANAGER)
    _user(db, "emp11_exp", UserRole.EMPLOYEE)
    db.add(Customer(customer_code="CUST-EXP-1", name="=HYPERLINK(\"http://x\")", phone="0100001111"))
    db.commit()

    emp = TestClient(app); _login(emp, "emp11_exp")
    assert emp.get("/api/v1/exports/customers").status_code == 403

    mgr = TestClient(app); _login(mgr, "mgr11_exp")
    csv_resp = mgr.get("/api/v1/exports/customers?fmt=csv")
    assert csv_resp.status_code == 200 and "CUST-EXP-1" in csv_resp.content.decode("utf-8-sig")
    # حماية من Formula injection
    assert "'=HYPERLINK" in csv_resp.content.decode("utf-8-sig")

    xlsx_resp = mgr.get("/api/v1/exports/customers?fmt=xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_resp.content))
    values = [c.value for row in wb.active.iter_rows() for c in row]
    assert "CUST-EXP-1" in values

    for kind in ("orders", "assignments", "employees"):
        assert mgr.get(f"/api/v1/exports/{kind}").status_code == 200
    assert mgr.get("/api/v1/exports/nope").status_code == 404


def test_audit_log_lists_actions_manager_only(db):
    _user(db, "mgr11_aud", UserRole.SYSTEM_MANAGER)
    _user(db, "emp11_aud", UserRole.EMPLOYEE)
    mgr = TestClient(app); _login(mgr, "mgr11_aud")
    mgr.get("/api/v1/exports/employees")  # يولّد data_exported
    body = mgr.get("/api/v1/audit-logs?action=data_exported").json()
    assert body["total"] >= 1 and body["items"][0]["action"] == "data_exported"
    emp = TestClient(app); _login(emp, "emp11_aud")
    assert emp.get("/api/v1/audit-logs").status_code == 403


def test_login_failure_never_logs_password(db, caplog):
    import logging
    _user(db, "mgr11_log", UserRole.SYSTEM_MANAGER)
    with caplog.at_level(logging.INFO, logger="nexly"):
        TestClient(app).post("/api/v1/auth/login", json={"username": "mgr11_log", "password": "SuperSecretWrong99"})
    assert "SuperSecretWrong99" not in caplog.text
