"""اختبارات تزامن حقيقية بـ threads متعددة ضد PostgreSQL (وليس محاكاة)."""
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, Order, User
from app.models.enums import UserRole


def _setup(db, tag):
    u = User(username=f"mgr_{tag}", full_name="م", password_hash=hash_password("Pass12345"), role=UserRole.SYSTEM_MANAGER)
    c = Customer(customer_code=f"CUST-{tag}", name="ع", phone=f"0100{abs(hash(tag)) % 10**7:07d}")
    db.add_all([u, c]); db.commit(); db.refresh(c)
    client = TestClient(app)
    assert client.post("/api/v1/auth/login", json={"username": f"mgr_{tag}", "password": "Pass12345"}).status_code == 200
    v = client.post("/api/v1/products", json={"sku": f"SKU-{tag}", "name_ar": "م", "variants": [{"unit_label": "1kg", "price": 10}]}).json()["variants"][0]["id"]
    return client.cookies, str(c.id), v


def _post(cookies, body):
    c = TestClient(app)
    c.cookies.update(cookies)
    return c.post("/api/v1/orders", json=body)


def test_parallel_saves_with_same_key_create_exactly_one_order(db):
    cookies, cid, vid = _setup(db, "race1")
    key = str(uuid.uuid4())
    body = {"idempotency_key": key, "customer_id": cid, "items": [{"product_variant_id": vid, "quantity": 1}]}
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: _post(cookies, body), range(8)))
    assert all(r.status_code == 201 for r in results), [r.text for r in results if r.status_code != 201]
    assert len({r.json()["id"] for r in results}) == 1
    assert db.execute(select(func.count(Order.id)).where(Order.idempotency_key == key)).scalar_one() == 1


def test_parallel_different_orders_get_unique_order_numbers(db):
    cookies, cid, vid = _setup(db, "race2")
    def make(_):
        return _post(cookies, {"idempotency_key": str(uuid.uuid4()), "customer_id": cid, "items": [{"product_variant_id": vid, "quantity": 1}]})
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(make, range(16)))
    assert all(r.status_code == 201 for r in results), [r.text for r in results if r.status_code != 201]
    numbers = [r.json()["order_number"] for r in results]
    assert len(set(numbers)) == 16
