import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ShippingRule, StatusConfiguration
from app.services.audit_service import write_audit_log


class SettingsError(Exception):
    pass


class SettingsService:
    """
    القاعدة 66: قواعد الشحن قابلة للإدارة من الـ Backend، وليست ثوابت JavaScript.
    القاعدة 11: حالات التواصل قابلة للإدارة من المدير، مع لون موحّد لكل حالة.
    """

    def __init__(self, db: Session):
        self.db = db

    # --- Shipping rules ---
    def list_shipping_rules(self) -> list[ShippingRule]:
        return list(self.db.execute(select(ShippingRule).order_by(ShippingRule.governorate_group)).scalars())

    def create_shipping_rule(self, data, actor) -> ShippingRule:
        rule = ShippingRule(
            governorate_group=data.governorate_group,
            shipping_cost=data.shipping_cost,
            free_shipping_threshold=data.free_shipping_threshold,
        )
        self.db.add(rule)
        write_audit_log(self.db, user_id=actor.id, action="shipping_rule_created", entity_type="shipping_rule")
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_shipping_rule(self, rule_id: uuid.UUID, data, actor) -> ShippingRule:
        rule = self.db.get(ShippingRule, rule_id)
        if rule is None:
            raise SettingsError("القاعدة غير موجودة")
        for field in ["shipping_cost", "free_shipping_threshold", "is_active"]:
            value = getattr(data, field, None)
            if value is not None:
                setattr(rule, field, value)
        write_audit_log(self.db, user_id=actor.id, action="shipping_rule_updated", entity_type="shipping_rule", entity_id=str(rule_id))
        self.db.commit()
        self.db.refresh(rule)
        return rule

    # --- Status configuration ---
    def list_statuses(self) -> list[StatusConfiguration]:
        return list(
            self.db.execute(select(StatusConfiguration).order_by(StatusConfiguration.sort_order)).scalars()
        )

    def create_status(self, data, actor) -> StatusConfiguration:
        existing = self.db.execute(
            select(StatusConfiguration).where(StatusConfiguration.code == data.code)
        ).scalar_one_or_none()
        if existing is not None:
            raise SettingsError(f"الحالة '{data.code}' موجودة بالفعل")

        status_row = StatusConfiguration(
            code=data.code, label_ar=data.label_ar, color_hex=data.color_hex, sort_order=data.sort_order
        )
        self.db.add(status_row)
        write_audit_log(self.db, user_id=actor.id, action="status_configuration_created", entity_type="status_configuration")
        self.db.commit()
        self.db.refresh(status_row)
        return status_row

    def update_status(self, status_id: uuid.UUID, data, actor) -> StatusConfiguration:
        status_row = self.db.get(StatusConfiguration, status_id)
        if status_row is None:
            raise SettingsError("الحالة غير موجودة")
        for field in ["label_ar", "color_hex", "sort_order", "is_active"]:
            value = getattr(data, field, None)
            if value is not None:
                setattr(status_row, field, value)
        write_audit_log(self.db, user_id=actor.id, action="status_configuration_updated", entity_type="status_configuration", entity_id=str(status_id))
        self.db.commit()
        self.db.refresh(status_row)
        return status_row
