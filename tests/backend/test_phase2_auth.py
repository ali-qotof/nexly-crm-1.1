"""
اختبارات PHASE 2: تختبر مسارات المصادقة فعليًا عبر TestClient (HTTP حقيقي، كوكيز حقيقية)
وليس فقط استدعاء الدوال مباشرة.
"""
import uuid

from fastapi.testclient import TestClient

from app.auth.rate_limit import _attempts
from app.auth.security import hash_password
from app.main import app
from app.models import User
from app.models.enums import UserRole


def _make_manager(db, username="manager1", password="StrongPass123") -> User:
    u = User(
        username=username,
        full_name="مدير تجريبي",
        password_hash=hash_password(password),
        role=UserRole.SYSTEM_MANAGER,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_employee_user(db, username="emp1", password="StrongPass123") -> User:
    u = User(
        username=username,
        full_name="موظفة تجريبية",
        password_hash=hash_password(password),
        role=UserRole.EMPLOYEE,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_login_success_sets_cookies_and_returns_user(db):
    _make_manager(db, username="mgr_login_ok")
    client = TestClient(app)

    resp = client.post(
        "/api/v1/auth/login", json={"username": "mgr_login_ok", "password": "StrongPass123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == "mgr_login_ok"
    assert body["user"]["role"] == "SYSTEM_MANAGER"
    assert "nexly_access" in resp.cookies
    assert "nexly_refresh" in resp.cookies


def test_login_wrong_password_returns_401_generic_message(db):
    _make_manager(db, username="mgr_wrong_pw")
    client = TestClient(app)

    resp = client.post(
        "/api/v1/auth/login", json={"username": "mgr_wrong_pw", "password": "WrongPassword"}
    )
    assert resp.status_code == 401
    # لا يكشف الفرق بين "مستخدم غير موجود" و"كلمة مرور خاطئة"
    assert "غير صحيحة" in resp.json()["detail"]


def test_login_unknown_user_returns_same_generic_401(db):
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/login", json={"username": "no_such_user_xyz", "password": "whatever123"}
    )
    assert resp.status_code == 401
    assert "غير صحيحة" in resp.json()["detail"]


def test_me_requires_authentication(db):
    client = TestClient(app)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_after_login(db):
    _make_manager(db, username="mgr_me")
    client = TestClient(app)
    client.post("/api/v1/auth/login", json={"username": "mgr_me", "password": "StrongPass123"})

    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "mgr_me"


def test_refresh_rotates_token_and_old_one_becomes_invalid(db):
    _make_manager(db, username="mgr_refresh")
    client = TestClient(app)
    login_resp = client.post(
        "/api/v1/auth/login", json={"username": "mgr_refresh", "password": "StrongPass123"}
    )
    old_refresh_cookie = login_resp.cookies.get("nexly_refresh")
    assert old_refresh_cookie

    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    new_refresh_cookie = refresh_resp.cookies.get("nexly_refresh")
    assert new_refresh_cookie
    assert new_refresh_cookie != old_refresh_cookie

    # إعادة استخدام التوكن القديم المُستبدل يجب أن تفشل (Rotation reuse detection)
    client.cookies.set("nexly_refresh", old_refresh_cookie)
    reuse_resp = client.post("/api/v1/auth/refresh")
    assert reuse_resp.status_code == 401


def test_logout_invalidates_session(db):
    _make_manager(db, username="mgr_logout")
    client = TestClient(app)
    client.post("/api/v1/auth/login", json={"username": "mgr_logout", "password": "StrongPass123"})
    assert client.get("/api/v1/auth/me").status_code == 200

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # بعد Logout: لا Refresh يعمل بنفس التوكن القديم
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401


def test_rate_limiting_blocks_after_repeated_failures(db):
    _attempts.clear()
    _make_manager(db, username="mgr_ratelimit")
    client = TestClient(app)

    for _ in range(5):
        resp = client.post(
            "/api/v1/auth/login", json={"username": "mgr_ratelimit", "password": "wrong"}
        )
        assert resp.status_code == 401

    blocked_resp = client.post(
        "/api/v1/auth/login", json={"username": "mgr_ratelimit", "password": "wrong"}
    )
    assert blocked_resp.status_code == 429
    _attempts.clear()


def test_disabled_employee_cannot_login(db):
    employee = _make_employee_user(db, username="emp_disabled")
    employee.is_active = False
    db.add(employee)
    db.commit()

    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/login", json={"username": "emp_disabled", "password": "StrongPass123"}
    )
    assert resp.status_code == 401
