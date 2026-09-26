from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import User
from app.models.enums import UserRole


def _manager(db, username="mgr5", password="Pass12345") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password(password), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _employee(db, username="emp5", password="Pass12345") -> User:
    u = User(username=username, full_name="موظفة", password_hash=hash_password(password), role=UserRole.EMPLOYEE)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def test_create_product_with_variants(db):
    _manager(db, "mgr5_prod")
    client = TestClient(app)
    _login(client, "mgr5_prod")

    resp = client.post(
        "/api/v1/products",
        json={
            "sku": "SKU-AJWA-5",
            "name_ar": "عجوة",
            "variants": [
                {"unit_label": "500g", "price": 90},
                {"unit_label": "1kg", "price": 170},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["variants"]) == 2
    assert body["variants"][0]["price"] == 90


def test_duplicate_sku_rejected(db):
    _manager(db, "mgr5_sku")
    client = TestClient(app)
    _login(client, "mgr5_sku")
    client.post("/api/v1/products", json={"sku": "SKU-DUP-5", "name_ar": "منتج", "variants": []})
    resp2 = client.post("/api/v1/products", json={"sku": "SKU-DUP-5", "name_ar": "منتج آخر", "variants": []})
    assert resp2.status_code == 409


def test_employee_can_read_but_not_create_products(db):
    _employee(db, "emp5_read")
    client = TestClient(app)
    _login(client, "emp5_read")

    list_resp = client.get("/api/v1/products")
    assert list_resp.status_code == 200

    create_resp = client.post("/api/v1/products", json={"sku": "SKU-X", "name_ar": "منتج", "variants": []})
    assert create_resp.status_code == 403


def test_price_change_updates_variant_and_is_visible(db):
    _manager(db, "mgr5_price")
    client = TestClient(app)
    _login(client, "mgr5_price")

    create_resp = client.post(
        "/api/v1/products",
        json={"sku": "SKU-PRICE-5", "name_ar": "منتج سعر", "variants": [{"unit_label": "1kg", "price": 100}]},
    )
    variant_id = create_resp.json()["variants"][0]["id"]

    update_resp = client.patch(f"/api/v1/product-variants/{variant_id}", json={"price": 120})
    assert update_resp.status_code == 200
    assert update_resp.json()["price"] == 120


def test_bundle_creation_and_duplicate_item_rejected(db):
    _manager(db, "mgr5_bundle")
    client = TestClient(app)
    _login(client, "mgr5_bundle")

    product_resp = client.post(
        "/api/v1/products",
        json={
            "sku": "SKU-BUNDLE-5",
            "name_ar": "مكسرات",
            "variants": [{"unit_label": "500g", "price": 80}],
        },
    )
    variant_id = product_resp.json()["variants"][0]["id"]

    bundle_resp = client.post(
        "/api/v1/bundles",
        json={
            "name": "عرض تجريبي",
            "bundle_price": 300,
            "items": [{"product_variant_id": variant_id, "quantity": 2}],
        },
    )
    assert bundle_resp.status_code == 201
    body = bundle_resp.json()
    assert body["regular_total"] == 160  # 80 * 2
    assert body["items"][0]["product_name"] == "مكسرات"

    # عرض بنفس المنتج مكرر داخل عناصره يجب أن يُرفض
    dup_bundle_resp = client.post(
        "/api/v1/bundles",
        json={
            "name": "عرض مكرر",
            "bundle_price": 300,
            "items": [
                {"product_variant_id": variant_id, "quantity": 1},
                {"product_variant_id": variant_id, "quantity": 3},
            ],
        },
    )
    assert dup_bundle_resp.status_code == 409


def test_shipping_rules_crud(db):
    _manager(db, "mgr5_ship")
    client = TestClient(app)
    _login(client, "mgr5_ship")

    create_resp = client.post(
        "/api/v1/settings/shipping-rules",
        json={"governorate_group": "Cairo/Giza", "shipping_cost": 30, "free_shipping_threshold": 500},
    )
    assert create_resp.status_code == 201
    rule_id = create_resp.json()["id"]

    update_resp = client.patch(f"/api/v1/settings/shipping-rules/{rule_id}", json={"shipping_cost": 25})
    assert update_resp.status_code == 200
    assert update_resp.json()["shipping_cost"] == 25

    list_resp = client.get("/api/v1/settings/shipping-rules")
    assert any(r["id"] == rule_id for r in list_resp.json())


def test_status_configuration_crud_and_uniqueness(db):
    _manager(db, "mgr5_status")
    client = TestClient(app)
    _login(client, "mgr5_status")

    create_resp = client.post(
        "/api/v1/settings/statuses",
        json={"code": "no_answer", "label_ar": "لا يوجد رد", "color_hex": "#FF0000", "sort_order": 1},
    )
    assert create_resp.status_code == 201

    dup_resp = client.post(
        "/api/v1/settings/statuses",
        json={"code": "no_answer", "label_ar": "تكرار", "color_hex": "#000000", "sort_order": 2},
    )
    assert dup_resp.status_code == 409

    list_resp = client.get("/api/v1/settings/statuses")
    codes = [s["code"] for s in list_resp.json()]
    assert "no_answer" in codes
