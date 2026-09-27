"""
محرّك الحساب المركزي للطلبات (القاعدة 19).

Backend هو Source of Truth الوحيد. الواجهة الأمامية قد تعرض تقديرًا فوريًا للمستخدم لتجربة أفضل،
لكن الرقم النهائي المحفوظ دائمًا يأتي من هنا فقط — لا حساب مزدوج بمنطق مختلف.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bundle, Customer, ProductVariant, ShippingRule
from app.models.enums import DiscountType


class PricingError(Exception):
    pass


@dataclass
class PricedLine:
    product_variant_id: str | None
    bundle_id: str | None
    name_snapshot: str
    unit_price: float
    quantity: int
    line_total: float


@dataclass
class PricingResult:
    lines: list[PricedLine]
    subtotal: float
    discount_amount: float
    shipping_amount: float
    total_amount: float


class OrderPricingService:
    def __init__(self, db: Session):
        self.db = db

    def price_order(
        self,
        *,
        customer: Customer,
        items: list,
        discount_type: DiscountType | None,
        discount_value: float | None,
    ) -> PricingResult:
        lines: list[PricedLine] = []
        subtotal = 0.0

        for item in items:
            if item.product_variant_id and item.bundle_id:
                raise PricingError("لا يمكن أن يكون البند منتجًا وعرضًا في نفس الوقت")
            if not item.product_variant_id and not item.bundle_id:
                raise PricingError("كل بند يجب أن يحدد منتجًا أو عرضًا")

            if item.product_variant_id:
                variant = self.db.get(ProductVariant, item.product_variant_id)
                if variant is None or not variant.is_active:
                    raise PricingError("أحد المنتجات المحددة غير متاح")
                unit_price = float(variant.price)
                name = f"{variant.product.name_ar} {variant.unit_label}"
                line_total = unit_price * item.quantity
                lines.append(
                    PricedLine(
                        product_variant_id=str(variant.id),
                        bundle_id=None,
                        name_snapshot=name,
                        unit_price=unit_price,
                        quantity=item.quantity,
                        line_total=line_total,
                    )
                )
            else:
                bundle = self.db.get(Bundle, item.bundle_id)
                if bundle is None or not bundle.is_active:
                    raise PricingError("أحد العروض المحددة غير متاح")
                unit_price = float(bundle.bundle_price)
                line_total = unit_price * item.quantity
                lines.append(
                    PricedLine(
                        product_variant_id=None,
                        bundle_id=str(bundle.id),
                        name_snapshot=bundle.name,
                        unit_price=unit_price,
                        quantity=item.quantity,
                        line_total=line_total,
                    )
                )
            subtotal += line_total

        discount_amount = self._compute_discount(subtotal, discount_type, discount_value)
        shipping_amount = self._compute_shipping(customer, subtotal - discount_amount)
        total_amount = subtotal - discount_amount + shipping_amount

        return PricingResult(
            lines=lines,
            subtotal=round(subtotal, 2),
            discount_amount=round(discount_amount, 2),
            shipping_amount=round(shipping_amount, 2),
            total_amount=round(total_amount, 2),
        )

    def _compute_discount(
        self, subtotal: float, discount_type: DiscountType | None, discount_value: float | None
    ) -> float:
        if not discount_type or not discount_value:
            return 0.0
        if discount_type == DiscountType.PERCENTAGE:
            if discount_value > 100:
                raise PricingError("نسبة الخصم لا يمكن أن تتجاوز 100%")
            amount = subtotal * (discount_value / 100)
        else:
            amount = discount_value
        return min(amount, subtotal)  # الخصم لا يمكن أن يتجاوز قيمة الطلب أبدًا

    def _compute_shipping(self, customer: Customer, amount_after_discount: float) -> float:
        governorate = (customer.governorate or "").strip()
        stmt = select(ShippingRule).where(
            ShippingRule.governorate_group == governorate, ShippingRule.is_active.is_(True)
        )
        rule = self.db.execute(stmt).scalar_one_or_none()

        if rule is None:
            # لا توجد قاعدة مطابقة للمحافظة — يُستخدم قاعدة "أخرى" العامة إن وُجدت، وإلا شحن صفر
            fallback_stmt = select(ShippingRule).where(
                ShippingRule.governorate_group == "other", ShippingRule.is_active.is_(True)
            )
            rule = self.db.execute(fallback_stmt).scalar_one_or_none()

        if rule is None:
            return 0.0

        if rule.free_shipping_threshold is not None and amount_after_discount >= float(
            rule.free_shipping_threshold
        ):
            return 0.0

        return float(rule.shipping_cost)
