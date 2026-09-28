"""
القاعدة 36: Shipping Integration لا يكون شرطًا لعمل الطلب أبدًا. الطلب يُنشأ وتُحسب تكلفة
شحنه من shipping_rules (PHASE 5/6) بغض النظر تمامًا عن وجود تكامل شحن فعلي متصل.
هذا الملف فقط لتتبّع شحنة بعد إنشاء الطلب، وهو اختياري بالكامل.
"""
from abc import ABC, abstractmethod


class ShipmentResult:
    def __init__(self, success: bool, tracking_number: str | None = None, error: str | None = None):
        self.success = success
        self.tracking_number = tracking_number
        self.error = error


class ShippingProvider(ABC):
    @abstractmethod
    def create_shipment(self, order_id: str) -> ShipmentResult: ...

    @abstractmethod
    def track_shipment(self, tracking_number: str) -> str: ...


class NullShippingProvider(ShippingProvider):
    def create_shipment(self, order_id: str) -> ShipmentResult:
        return ShipmentResult(success=False, error="لا يوجد مزوّد شحن مُفعَّل حاليًا")

    def track_shipment(self, tracking_number: str) -> str:
        return "unknown"


def get_shipping_provider() -> ShippingProvider:
    """نقطة التوسعة الوحيدة لربط EasyShip أو أي مزوّد آخر لاحقًا (القاعدة 36)."""
    return NullShippingProvider()
