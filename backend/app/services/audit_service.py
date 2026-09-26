import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    meta: dict | None = None,
) -> None:
    """
    يكتب سجل تدقيق (القاعدة 37). لا يعمل commit بنفسه — يُدمج ضمن نفس معاملة العملية الأصلية
    حتى يكون تسجيل التدقيق جزءًا من نفس الـ Transaction (لا سجل عملية بدون تدقيق، والعكس).
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=meta or {},
    )
    db.add(log)
