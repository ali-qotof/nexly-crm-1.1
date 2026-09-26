from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Setting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    إعدادات عامة key/value (مثال: free_shipping_threshold، default_currency).
    key فريد. value مرن (JSON) لأنواع بيانات مختلفة، لكن هذا الجدول للإعدادات العامة القليلة
    وليس بديلًا عن Schema علائقي للبيانات الأساسية (القاعدة 39).
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class StatusConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    حالات التواصل القابلة للإدارة من المدير (القاعدة 11): "سجل أوردر"، "لا يوجد رد"،
    "لسه عنده تمر"، إلخ — مع لون موحّد لكل حالة، بدل تكرار الألوان Hard-coded في كل مكان
    (تُقرأ هذه القائمة مرة واحدة في الواجهة الأمامية وتُستخدم كـ Design token).
    """

    __tablename__ = "status_configurations"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ShippingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    قواعد الشحن قابلة للإدارة من الـ Backend (القاعدة 66) — وليست JavaScript ثابت في الواجهة.
    مثال: القاهرة/الجيزة سعر شحن مختلف عن باقي المحافظات، وحد أدنى للشحن المجاني.
    """

    __tablename__ = "shipping_rules"

    governorate_group: Mapped[str] = mapped_column(String(64), nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Integer, nullable=False, default=0)
    free_shipping_threshold: Mapped[float | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
