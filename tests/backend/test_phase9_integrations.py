import uuid

from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.integrations.messaging import NullMessagingProvider, get_messaging_provider
from app.integrations.shipping import NullShippingProvider, get_shipping_provider
from app.main import app
from app.models import User
from app.models.enums import UserRole


def _manager(db, username="mgr9", password="Pass12345") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password(password), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _employee(db, username="emp9", password="Pass12345") -> User:
    u = User(username=username, full_name="موظفة", password_hash=hash_password(password), role=UserRole.EMPLOYEE)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def _create_integration(client: TestClient, name="Sheets") -> dict:
    resp = client.post("/api/v1/integrations", json={"type": "GOOGLE_SHEETS", "name": name, "config": {}})
    assert resp.status_code == 201
    return resp.json()


def test_employee_cannot_manage_integrations(db):
    _employee(db, "emp9_forbid")
    client = TestClient(app)
    _login(client, "emp9_forbid")
    assert client.get("/api/v1/integrations").status_code == 403
    assert client.post("/api/v1/integrations", json={"type": "GOOGLE_SHEETS", "name": "x"}).status_code == 403


def test_secret_returned_once_and_never_via_get(db):
    _manager(db, "mgr9_secret")
    client = TestClient(app)
    _login(client, "mgr9_secret")

    created = _create_integration(client, "SecretOnce")
    assert created["plain_secret_shown_once"]
    assert created["is_enabled"] is False

    listed = client.get("/api/v1/integrations").json()
    row = [i for i in listed if i["id"] == created["id"]][0]
    assert "plain_secret_shown_once" not in row
    assert "secret_hash" not in row


def test_webhook_rejected_when_disabled_or_bad_secret(db):
    _manager(db, "mgr9_wh")
    client = TestClient(app)
    _login(client, "mgr9_wh")

    created = _create_integration(client, "WH")
    integration_id = created["id"]
    secret = created["plain_secret_shown_once"]
    body = {"event_id": str(uuid.uuid4()), "event_type": "order.created", "payload": {}}

    public = TestClient(app)  # بدون جلسة مستخدم — مصدر خارجي
    assert public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": secret}).status_code == 403  # معطَّل

    client.patch(f"/api/v1/integrations/{integration_id}", json={"is_enabled": True})

    assert public.post(f"/api/v1/webhooks/{integration_id}", json=body).status_code == 401  # بلا سر
    assert public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": "wrong"}).status_code == 401
    assert public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": secret}).status_code == 202


def test_webhook_deduplicates_by_event_id(db):
    _manager(db, "mgr9_dedup")
    client = TestClient(app)
    _login(client, "mgr9_dedup")

    created = _create_integration(client, "Dedup")
    integration_id = created["id"]
    secret = created["plain_secret_shown_once"]
    client.patch(f"/api/v1/integrations/{integration_id}", json={"is_enabled": True})

    public = TestClient(app)
    body = {"event_id": "evt-dedup-1", "event_type": "customer.updated", "entity_type": "customer", "entity_id": "c1", "payload": {"a": 1}}
    r1 = public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": secret})
    r2 = public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": secret})
    assert r1.json()["duplicate"] is False
    assert r2.json()["duplicate"] is True

    events = client.get(f"/api/v1/integrations/{integration_id}/events").json()
    assert len(events) == 1
    assert events[0]["event_id"] == "evt-dedup-1"
    assert events[0]["status"] == "SUCCESS"


def test_rotate_secret_invalidates_old_secret(db):
    _manager(db, "mgr9_rotate")
    client = TestClient(app)
    _login(client, "mgr9_rotate")

    created = _create_integration(client, "Rotate")
    integration_id = created["id"]
    old_secret = created["plain_secret_shown_once"]
    client.patch(f"/api/v1/integrations/{integration_id}", json={"is_enabled": True})

    new_secret = client.post(f"/api/v1/integrations/{integration_id}/rotate-secret").json()["plain_secret"]
    assert new_secret != old_secret

    public = TestClient(app)
    body = {"event_id": str(uuid.uuid4()), "event_type": "x", "payload": {}}
    assert public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": old_secret}).status_code == 401
    assert public.post(f"/api/v1/webhooks/{integration_id}", json=body, headers={"x-webhook-secret": new_secret}).status_code == 202


def test_test_connection_reflects_enabled_state(db):
    _manager(db, "mgr9_test")
    client = TestClient(app)
    _login(client, "mgr9_test")

    created = _create_integration(client, "Test")
    integration_id = created["id"]
    assert client.post(f"/api/v1/integrations/{integration_id}/test").json()["ok"] is False

    client.patch(f"/api/v1/integrations/{integration_id}", json={"is_enabled": True})
    assert client.post(f"/api/v1/integrations/{integration_id}/test").json()["ok"] is True


def test_provider_abstractions_fail_explicitly_without_provider():
    """القاعدة 35/36: لا مزوّد → فشل صريح، لا صمت ولا انهيار، والطلبات لا تعتمد على هذه الطبقة."""
    messaging = get_messaging_provider()
    assert isinstance(messaging, NullMessagingProvider)
    result = messaging.send_whatsapp_message("0100000000", "مرحبا")
    assert result.success is False and result.error

    shipping = get_shipping_provider()
    assert isinstance(shipping, NullShippingProvider)
    assert shipping.create_shipment("order-1").success is False
