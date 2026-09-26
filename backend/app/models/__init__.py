"""يجمع كل الـ Models في مكان واحد حتى تكتشفها Alembic (autogenerate) والتطبيق بالكامل."""
from app.models.audit_log import AuditLog
from app.models.complaint import Complaint
from app.models.customer import Customer, CustomerAssignment, CustomerSegment, Segment
from app.models.integration import Integration, IntegrationEvent
from app.models.interaction import Attachment, FollowUp, Interaction
from app.models.order import Order, OrderItem
from app.models.product import Bundle, BundleItem, Product, ProductVariant
from app.models.refresh_token import RefreshToken
from app.models.settings import Setting, ShippingRule, StatusConfiguration
from app.models.user import User

__all__ = [
    "AuditLog",
    "Complaint",
    "Customer",
    "CustomerAssignment",
    "CustomerSegment",
    "Segment",
    "Integration",
    "IntegrationEvent",
    "Attachment",
    "FollowUp",
    "Interaction",
    "Order",
    "OrderItem",
    "Bundle",
    "BundleItem",
    "Product",
    "ProductVariant",
    "RefreshToken",
    "Setting",
    "ShippingRule",
    "StatusConfiguration",
    "User",
]
