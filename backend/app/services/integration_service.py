"""
القاعدة 32/33: طبقة تكامل عامة — Google Sheets، وفي المستقبل Meta/WhatsApp/Shipping/E-commerce،
بدون ربط الكود الأساسي مباشرة بأي مزوّد خارجي محدد (راجع app/integrations/*.py للـ Abstractions).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Integration
from app.services.audit_service import write_audit_log


class IntegrationError(Exception):
    pass


def _hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

    def list_integrations(self) -> list[Integration]:
        return list(self.db.execute(select(Integration).order_by(Integration.created_at.desc())).scalars())

    def get(self, integration_id: uuid.UUID) -> Integration | None:
        return self.db.get(Integration, integration_id)

    def create(self, data, actor) -> tuple[Integration, str]:
        """يُرجع (integration, plain_secret) — plain_secret يُعرض مرة واحدة فقط للمستخدم."""
        plain_secret = secrets.token_urlsafe(32)
        integration = Integration(
            type=data.type, name=data.name, config=data.config, secret_hash=_hash_secret(plain_secret)
        )
        self.db.add(integration)
        write_audit_log(
            self.db, user_id=actor.id, action="integration_changed", entity_type="integration", meta={"action": "created", "type": data.type.value}
        )
        self.db.commit()
        self.db.refresh(integration)
        return integration, plain_secret

    def update(self, integration_id: uuid.UUID, data, actor) -> Integration:
        integration = self.get(integration_id)
        if integration is None:
            raise IntegrationError("التكامل غير موجود")

        if data.is_enabled is not None:
            integration.is_enabled = data.is_enabled
        if data.config is not None:
            integration.config = data.config

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="integration_changed",
            entity_type="integration",
            entity_id=str(integration.id),
            meta={"is_enabled": integration.is_enabled},
        )
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def rotate_secret(self, integration_id: uuid.UUID, actor) -> tuple[Integration, str]:
        integration = self.get(integration_id)
        if integration is None:
            raise IntegrationError("التكامل غير موجود")

        plain_secret = secrets.token_urlsafe(32)
        integration.secret_hash = _hash_secret(plain_secret)

        write_audit_log(
            self.db,
            user_id=actor.id,
            action="integration_changed",
            entity_type="integration",
            entity_id=str(integration.id),
            meta={"action": "secret_rotated"},
        )
        self.db.commit()
        self.db.refresh(integration)
        return integration, plain_secret

    def test_connection(self, integration_id: uuid.UUID) -> dict:
        """
        فحص اتصال بسيط. لا يوجد مزوّد فعلي مُفعَّل بعد (القاعدة 32: البنية جاهزة، الربط الفعلي
        بمزوّد حقيقي خارج نطاق هذا المستودع دون بيانات اعتماد فعلية من الفريق).
        """
        integration = self.get(integration_id)
        if integration is None:
            raise IntegrationError("التكامل غير موجود")
        if not integration.is_enabled:
            return {"ok": False, "message": "التكامل معطَّل"}

        integration.last_sync_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"ok": True, "message": "الاتصال يعمل (فحص بنيوي — لا يوجد مزوّد خارجي فعلي متصل بعد)"}

    def verify_webhook_secret(self, integration_id: uuid.UUID, provided_secret: str) -> bool:
        integration = self.get(integration_id)
        if integration is None or integration.secret_hash is None:
            return False
        return secrets.compare_digest(_hash_secret(provided_secret), integration.secret_hash)
