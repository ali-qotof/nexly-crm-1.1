"""Enums مشتركة. الحالات القابلة للإدارة من المدير (مثل Communication Status) لا تُثبَّت هنا
كـ Python Enum، بل تُخزَّن كبيانات في جدول status_configurations (راجع status_config.py) — لأن
القاعدة 11 تنص على أن الحالات "قابلة للإدارة" وليست ثابتة في الكود."""
import enum


class UserRole(str, enum.Enum):
    SYSTEM_MANAGER = "SYSTEM_MANAGER"
    EMPLOYEE = "EMPLOYEE"
    # SUPERVISOR / ADMIN محجوزة للمستقبل (القاعدة 5) — غير مفعّلة الآن.


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IntegrationEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class IntegrationType(str, enum.Enum):
    GOOGLE_SHEETS = "GOOGLE_SHEETS"
    WHATSAPP = "WHATSAPP"
    SHIPPING = "SHIPPING"
    CRM = "CRM"
    ECOMMERCE = "ECOMMERCE"
