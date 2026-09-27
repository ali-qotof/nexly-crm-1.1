import uuid

from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.main import app
from app.models import Customer, User
from app.models.enums import UserRole


def _manager(db, username="mgr6", password="Pass12345") -> User:
    u = User(username=username, full_name="مدير", password_hash=hash_password(password), role=UserRole.SYSTEM_MANAGER)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _employee(db, username="emp6", password="Pass12345") -> User:
    u = User(username=username, full_name="موظفة", password_hash=hash_password(password), role=UserRole.EMPLOYEE)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, username: str, password: str = "Pass12345"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def _create_product_variant(client: TestClient, sku: str, price: float) -> str:
    resp = client.post(
        "/api/v1/products",
        json={"sku": sku, "name_ar": "عجوة", "variants": [{"unit_label": "1kg", "price": price}]},
    )
    return resp.json()["variants"][0]["id"]


def test_order_calculation_with_percentage_discount_and_shipping(db):
    manager = _manager(db, "mgr6_calc")
    client = TestClient(app)
    _login(client, "mgr6_calc")

    client.post(
        "/api/v1/settings/shipping-rules",
        json={"governorate_group": "Cairo", "shipping_cost": 30, "free_shipping_threshold": 1000},
    )
    variant_id = _create_product_variant(client, "SKU-ORD-1", 100)

    customer = Customer(customer_code="CUST-ORD-1", name="ع", phone="0100000001", governorate="Cairo")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    resp = client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 2}],
            "discount_type": "PERCENTAGE",
            "discount_value": 10,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["subtotal"] == 200
    assert body["discount_amount"] == 20  # 10% of 200
    assert body["shipping_amount"] == 30  # below free-shipping threshold
    assert body["total_amount"] == 210  # 200 - 20 + 30


def test_free_shipping_threshold_applies(db):
    manager = _manager(db, "mgr6_free")
    client = TestClient(app)
    _login(client, "mgr6_free")

    client.post(
        "/api/v1/settings/shipping-rules",
        json={"governorate_group": "Giza", "shipping_cost": 40, "free_shipping_threshold": 300},
    )
    variant_id = _create_product_variant(client, "SKU-ORD-2", 150)

    customer = Customer(customer_code="CUST-ORD-2", name="ع", phone="0100000002", governorate="Giza")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    resp = client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 3}],  # 450 >= 300 threshold
        },
    )
    body = resp.json()
    assert body["subtotal"] == 450
    assert body["shipping_amount"] == 0
    assert body["total_amount"] == 450


def test_duplicate_save_returns_same_order_no_new_row_created(db):
    """القاعدة 20: ضغط Save عدة مرات بنفس idempotency_key ينشئ Order واحدًا فقط."""
    manager = _manager(db, "mgr6_idem")
    client = TestClient(app)
    _login(client, "mgr6_idem")

    variant_id = _create_product_variant(client, "SKU-ORD-3", 50)
    customer = Customer(customer_code="CUST-ORD-3", name="ع", phone="0100000003")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    key = str(uuid.uuid4())
    payload = {
        "idempotency_key": key,
        "customer_id": str(customer.id),
        "items": [{"product_variant_id": variant_id, "quantity": 1}],
    }

    resp1 = client.post("/api/v1/orders", json=payload)
    resp2 = client.post("/api/v1/orders", json=payload)
    resp3 = client.post("/api/v1/orders", json=payload)

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp3.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"] == resp3.json()["id"]

    from sqlalchemy import select
    from app.models import Order

    all_orders = db.execute(select(Order).where(Order.idempotency_key == key)).scalars().all()
    assert len(all_orders) == 1


def test_price_snapshot_not_affected_by_later_variant_price_change_via_api(db):
    manager = _manager(db, "mgr6_snap")
    client = TestClient(app)
    _login(client, "mgr6_snap")

    create_resp = client.post(
        "/api/v1/products",
        json={"sku": "SKU-ORD-SNAP", "name_ar": "منتج", "variants": [{"unit_label": "1kg", "price": 100}]},
    )
    variant_id = create_resp.json()["variants"][0]["id"]

    customer = Customer(customer_code="CUST-ORD-SNAP", name="ع", phone="0100000004")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    order_resp = client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 1}],
        },
    )
    assert order_resp.json()["subtotal"] == 100

    client.patch(f"/api/v1/product-variants/{variant_id}", json={"price": 500})

    order_id = order_resp.json()["id"]
    refetch_resp = client.get(f"/api/v1/orders/{order_id}")
    assert refetch_resp.json()["subtotal"] == 100  # لم يتأثر بتغيير السعر لاحقًا


def test_employee_only_sees_own_orders(db):
    manager = _manager(db, "mgr6_iso")
    emp1 = _employee(db, "emp6_iso1")
    emp2 = _employee(db, "emp6_iso2")

    mgr_client = TestClient(app)
    _login(mgr_client, "mgr6_iso")
    variant_id = _create_product_variant(mgr_client, "SKU-ORD-ISO", 20)

    customer = Customer(customer_code="CUST-ORD-ISO", name="ع", phone="0100000005")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    emp1_client = TestClient(app)
    _login(emp1_client, "emp6_iso1")
    emp1_client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 1}],
        },
    )

    emp2_client = TestClient(app)
    _login(emp2_client, "emp6_iso2")
    emp2_orders = emp2_client.get("/api/v1/orders").json()
    assert emp2_orders["total"] == 0

    emp1_orders = emp1_client.get("/api/v1/orders").json()
    assert emp1_orders["total"] == 1


def test_cancel_order_manager_only(db):
    manager = _manager(db, "mgr6_cancel", password="ManagerPass1")
    employee = _employee(db, "emp6_cancel")

    mgr_client = TestClient(app)
    _login(mgr_client, "mgr6_cancel", password="ManagerPass1")
    variant_id = _create_product_variant(mgr_client, "SKU-ORD-CANCEL", 20)

    customer = Customer(customer_code="CUST-ORD-CANCEL", name="ع", phone="0100000006")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    emp_client = TestClient(app)
    _login(emp_client, "emp6_cancel")
    order_resp = emp_client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": str(uuid.uuid4()),
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 1}],
        },
    )
    order_id = order_resp.json()["id"]

    emp_cancel_resp = emp_client.post(f"/api/v1/orders/{order_id}/cancel")
    assert emp_cancel_resp.status_code == 403

    mgr_cancel_resp = mgr_client.post(f"/api/v1/orders/{order_id}/cancel")
    assert mgr_cancel_resp.status_code == 200
    assert mgr_cancel_resp.json()["status"] == "CANCELLED"


def test_primary_acceptance_flow_end_to_end(db):
    """
    القاعدة 55: السيناريو الحرج الكامل — Manager Login → Add Employee → Assign Customer →
    Employee Login → View My Customers → Open Customer → Register Interaction → Create Order →
    Refresh → Order remains → Open customer → Order appears in history.
    """
    manager = _manager(db, "mgr6_e2e", password="ManagerPassE2E1")

    mgr_client = TestClient(app)
    _login(mgr_client, "mgr6_e2e", password="ManagerPassE2E1")

    # Add Employee
    emp_resp = mgr_client.post(
        "/api/v1/employees", json={"username": "emp6_e2e", "full_name": "سارة", "password": "EmpPassE2E1"}
    )
    assert emp_resp.status_code == 201
    employee_id = emp_resp.json()["id"]

    # منتج للطلب
    variant_id = _create_product_variant(mgr_client, "SKU-E2E", 75)

    # عميل + توزيعه على الموظفة
    customer = Customer(customer_code="CUST-E2E", name="عميل الاختبار الشامل", phone="0100000099")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    assign_resp = mgr_client.post(
        "/api/v1/assignments/assign",
        json={"customer_ids": [str(customer.id)], "employee_id": employee_id},
    )
    assert assign_resp.json()["assigned"] == 1

    # Employee Login
    emp_client = TestClient(app)
    _login(emp_client, "emp6_e2e", password="EmpPassE2E1")

    # View My Customers
    my_customers = emp_client.get("/api/v1/customers/my").json()
    assert my_customers["total"] == 1
    assert my_customers["items"][0]["customer_code"] == "CUST-E2E"

    # Register Interaction — نموذج بسيط مباشر (لا يوجد بعد endpoint مخصص للتفاعلات؛ سيُبنى في PHASE 7)
    from app.models import Interaction

    interaction = Interaction(customer_id=customer.id, employee_id=uuid.UUID(employee_id), channel="call", note="تم الاتصال")
    db.add(interaction)
    db.commit()

    # Create Order
    idem_key = str(uuid.uuid4())
    order_resp = emp_client.post(
        "/api/v1/orders",
        json={
            "idempotency_key": idem_key,
            "customer_id": str(customer.id),
            "items": [{"product_variant_id": variant_id, "quantity": 2}],
        },
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]
    assert order_resp.json()["total_amount"] == 150

    # Refresh page (محاكاة: طلب GET جديد بعد "تحديث") — Order remains
    refetch_resp = emp_client.get(f"/api/v1/orders/{order_id}")
    assert refetch_resp.status_code == 200
    assert refetch_resp.json()["id"] == order_id
    assert refetch_resp.json()["total_amount"] == 150

    # Open customer → Order appears in history
    customer_orders = emp_client.get(f"/api/v1/orders?customer_id={customer.id}").json()
    assert customer_orders["total"] == 1
    assert customer_orders["items"][0]["id"] == order_id
