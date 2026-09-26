"""
منطق المصادقة الكامل. يُستدعى من app/api/v1/auth.py فقط — لا يُكتب أي منطق أعمال داخل طبقة API
مباشرة (القاعدة 4: فصل UI/API عن Business Logic).
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.auth.tokens import create_access_token, generate_refresh_token, hash_refresh_token
from app.models import RefreshToken, User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import write_audit_log


class AuthError(Exception):
    """خطأ مصادقة عام — يُترجَم لاحقًا إلى 401 في طبقة API."""


@dataclass
class LoginResult:
    user: User
    access_token: str
    access_token_expires_at: datetime
    refresh_token_raw: str
    refresh_token_expires_at: datetime


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def login(self, username: str, password: str, user_agent: str | None = None) -> LoginResult:
        user = self.users.get_by_username(username)

        # رسالة خطأ موحّدة لعدم الكشف عن وجود/عدم وجود المستخدم (منع User enumeration)
        generic_error = AuthError("اسم المستخدم أو كلمة المرور غير صحيحة")

        if user is None or not user.is_active or user.deleted_at is not None:
            raise generic_error

        if not verify_password(password, user.password_hash):
            write_audit_log(
                self.db,
                user_id=user.id,
                action="login_failed",
                entity_type="user",
                entity_id=str(user.id),
            )
            self.db.commit()
            raise generic_error

        access_token, access_expires = create_access_token(str(user.id), user.role.value)
        raw_refresh, refresh_hash, refresh_expires = generate_refresh_token()

        token_row = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires,
            user_agent=user_agent,
        )
        self.db.add(token_row)

        write_audit_log(
            self.db, user_id=user.id, action="login_success", entity_type="user", entity_id=str(user.id)
        )
        self.db.commit()

        return LoginResult(
            user=user,
            access_token=access_token,
            access_token_expires_at=access_expires,
            refresh_token_raw=raw_refresh,
            refresh_token_expires_at=refresh_expires,
        )

    def refresh(self, raw_refresh_token: str, user_agent: str | None = None) -> LoginResult:
        """
        يُبطل التوكن القديم فورًا ويصدر واحدًا جديدًا (Rotation). إذا وصل نفس التوكن القديم مرة
        أخرى بعد استخدامه (يدل على سرقة/إعادة استخدام)، تُبطل كل جلسات المستخدم كإجراء احترازي.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token_row = self.db.execute(stmt).scalar_one_or_none()

        if token_row is None:
            raise AuthError("جلسة غير صالحة")

        now = datetime.now(timezone.utc)

        if token_row.revoked:
            # إعادة استخدام توكن تم إلغاؤه بالفعل — إبطال كل جلسات المستخدم احترازيًا
            revoke_all_stmt = select(RefreshToken).where(RefreshToken.user_id == token_row.user_id)
            for row in self.db.execute(revoke_all_stmt).scalars():
                row.revoked = True
            write_audit_log(
                self.db,
                user_id=token_row.user_id,
                action="refresh_token_reuse_detected",
                entity_type="user",
                entity_id=str(token_row.user_id),
            )
            self.db.commit()
            raise AuthError("جلسة غير صالحة")

        if token_row.expires_at < now:
            raise AuthError("انتهت صلاحية الجلسة")

        user = self.users.get_by_id(token_row.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise AuthError("الحساب غير نشط")

        # Rotation: أبطل القديم، أصدر جديد
        token_row.revoked = True

        access_token, access_expires = create_access_token(str(user.id), user.role.value)
        raw_refresh, refresh_hash, refresh_expires = generate_refresh_token()
        token_row.replaced_by_hash = refresh_hash

        new_token_row = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires,
            user_agent=user_agent,
        )
        self.db.add(new_token_row)
        self.db.commit()

        return LoginResult(
            user=user,
            access_token=access_token,
            access_token_expires_at=access_expires,
            refresh_token_raw=raw_refresh,
            refresh_token_expires_at=refresh_expires,
        )

    def logout(self, raw_refresh_token: str | None) -> None:
        if not raw_refresh_token:
            return
        token_hash = hash_refresh_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token_row = self.db.execute(stmt).scalar_one_or_none()
        if token_row is not None:
            token_row.revoked = True
            write_audit_log(
                self.db,
                user_id=token_row.user_id,
                action="logout",
                entity_type="user",
                entity_id=str(token_row.user_id),
            )
        self.db.commit()
