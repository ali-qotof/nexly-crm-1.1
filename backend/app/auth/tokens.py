"""
إدارة Access Tokens (JWT قصيرة العمر) و Refresh Tokens (طويلة العمر، مخزّنة كـ hash في DB).

القرار: Access token يُحمل في HTTP-only Secure cookie (وليس localStorage) لتقليل مخاطر XSS
(القاعدة 38). Refresh token أيضًا HTTP-only cookie منفصل، برمز عشوائي مُخزَّن كـ hash فقط.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

ACCESS_TOKEN_COOKIE_NAME = "nexly_access"
REFRESH_TOKEN_COOKIE_NAME = "nexly_refresh"


def create_access_token(user_id: str, role: str) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": user_id, "role": role, "exp": expires_at, "type": "access"}
    token = jwt.encode(payload, settings.nexly_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.nexly_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def generate_refresh_token() -> tuple[str, str, datetime]:
    """يُرجع (raw_token يُرسل في الكوكي, hash يُخزَّن في DB, تاريخ الانتهاء)."""
    raw = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return raw, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    # SHA-256 كافٍ هنا (التوكن نفسه عشوائي عالي الإنتروبيا، لسنا نجزّئ كلمة مرور بشرية)
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
