"""
Dependencies تُستخدم في كل الـ Routes المحمية. القاعدة 6: 401 handling واضح، حماية Routes.
"""
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.tokens import ACCESS_TOKEN_COOKIE_NAME, decode_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="غير مصادَق عليه")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="جلسة غير صالحة")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="جلسة غير صالحة")

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="الحساب غير نشط")

    return user


def require_role(*allowed_roles: UserRole):
    """Dependency factory: يسمح فقط للأدوار المحددة (القاعدة 5: صلاحيات المدير مقابل الموظفة)."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="لا تملك صلاحية الوصول لهذا المورد"
            )
        return user

    return _checker


require_manager = require_role(UserRole.SYSTEM_MANAGER)
require_any_authenticated = require_role(UserRole.SYSTEM_MANAGER, UserRole.EMPLOYEE)
