"""
اختبارات PHASE 1: تتحقق من أن الـ Models والقيود (constraints) تعمل فعليًا على PostgreSQL حقيقي،
وليس مجرد أنها "تستورد بدون خطأ".
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Customer,
    CustomerAssignment,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    User,
)
from app.models.enums import OrderStatus, UserRole


def _make_customer(db, code="CUST-0001") -> Customer:
    c = Customer(customer_code=code, name="عميل تجريبي", phone="0100000000")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_employee(db, username="sara") -> User:
    u = User(
        username=username,
        full_name="ساره",
        password_hash="hashed",
        role=UserRole.EMPLOYEE,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_customer_and_employee_created(db):
    customer = _make_customer(db)
    employee = _make_employee(db)
    assert customer.id is not None
    assert employee.role == UserRole.EMPLOYEE


def test_customer_assignment_prevents_duplicate_active_assignment(db):
    """
    القاعدة 13: منع Duplicate assignment على مستوى قاعدة البيانات.
    نفس العميل لا يمكن أن يكون له تخصيص نشط (is_active=True) مرتين في نفس الوقت.
    """
    customer = _make_customer(db, code="CUST-DUP")
    emp1 = _make_employee(db, username="emp1")
    emp2 = _make_employee(db, username="emp2")

    a1 = CustomerAssignment(customer_id=customer.id, employee_id=emp1.id, assigned_by_id=emp1.id)
    db.add(a1)
    db.commit()

    a2 = CustomerAssignment(customer_id=customer.id, employee_id=emp2.id, assigned_by_id=emp2.id)
    db.add(a2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # بعد سحب التخصيص الأول (is_active=False) يجب أن يكون التخصيص الجديد مسموحًا
    a1.is_active = False
    db.add(a1)
    db.commit()

    a3 = CustomerAssignment(customer_id=customer.id, employee_id=emp2.id, assigned_by_id=emp2.id)
    db.add(a3)
    db.commit()  # يجب ألا يفشل
    assert a3.id is not None


def test_order_idempotency_key_is_unique(db):
    """القاعدة 20: مفتاح Idempotency يمنع إنشاء Order مكرر عند الضغط المتكرر على Save."""
    customer = _make_customer(db, code="CUST-ORDER")
    employee = _make_employee(db, username="emp_order")
    key = str(uuid.uuid4())

    order1 = Order(
        order_number="ORD-0001",
        idempotency_key=key,
        customer_id=customer.id,
        employee_id=employee.id,
        subtotal=100,
        discount_amount=0,
        shipping_amount=0,
        total_amount=100,
        status=OrderStatus.PENDING,
    )
    db.add(order1)
    db.commit()

    order2 = Order(
        order_number="ORD-0002",
        idempotency_key=key,  # نفس المفتاح — يحاكي ضغط Save مرتين
        customer_id=customer.id,
        employee_id=employee.id,
        subtotal=100,
        discount_amount=0,
        shipping_amount=0,
        total_amount=100,
        status=OrderStatus.PENDING,
    )
    db.add(order2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_order_item_price_snapshot_survives_variant_price_change(db):
    """يتأكد أن unit_price في OrderItem هو لقطة (snapshot) لا تتأثر بتغيّر سعر المنتج لاحقًا."""
    customer = _make_customer(db, code="CUST-SNAP")
    employee = _make_employee(db, username="emp_snap")
    product = Product(sku="SKU-AJWA", name_ar="عجوة")
    db.add(product)
    db.commit()
    db.refresh(product)

    variant = ProductVariant(product_id=product.id, unit_label="1kg", price=150)
    db.add(variant)
    db.commit()
    db.refresh(variant)

    order = Order(
        order_number="ORD-SNAP",
        idempotency_key=str(uuid.uuid4()),
        customer_id=customer.id,
        employee_id=employee.id,
        subtotal=150,
        discount_amount=0,
        shipping_amount=0,
        total_amount=150,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_variant_id=variant.id,
        name_snapshot="عجوة 1kg",
        unit_price=150,
        quantity=1,
        line_total=150,
    )
    db.add(item)
    db.commit()

    # غيّر سعر الـ variant الآن
    variant.price = 200
    db.add(variant)
    db.commit()

    db.refresh(item)
    assert float(item.unit_price) == 150  # اللقطة القديمة لم تتغيّر


def test_bundle_item_rejects_duplicate_variant_in_same_bundle(db):
    """القاعدة 23: منع تكرار نفس المنتج داخل نفس العرض."""
    from app.models import Bundle, BundleItem

    product = Product(sku="SKU-MIX", name_ar="مكسرات مشكلة")
    db.add(product)
    db.commit()
    db.refresh(product)

    variant = ProductVariant(product_id=product.id, unit_label="500g", price=80)
    db.add(variant)
    db.commit()
    db.refresh(variant)

    bundle = Bundle(name="عرض 6 أكياس", bundle_price=400)
    db.add(bundle)
    db.commit()
    db.refresh(bundle)

    item1 = BundleItem(bundle_id=bundle.id, product_variant_id=variant.id, quantity=1)
    db.add(item1)
    db.commit()

    item2 = BundleItem(bundle_id=bundle.id, product_variant_id=variant.id, quantity=2)
    db.add(item2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
