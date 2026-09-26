"""
مسارات المصادقة. كل منطق الأعمال في app/services/auth_service.py — هذا الملف فقط يترجم
HTTP request/response ويضبط الكوكيز (القاعدة 4 و6).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rate_limit import clear_attempts, is_rate_limited, register_failed_attempt
from app.auth.tokens import ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME
from app.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, access_expires, refresh_token: str, refresh_expires) -> None:
    is_prod = settings.is_production
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        expires=access_expires,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        expires=refresh_expires,
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/api/v1/auth")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit_key = f"{payload.username}:{request.client.host if request.client else 'unknown'}"
    if is_rate_limited(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="محاولات كثيرة جدًا. حاول لاحقًا بعد بضع دقائق.",
        )

    service = AuthService(db)
    try:
        result = service.login(
            payload.username, payload.password, user_agent=request.headers.get("user-agent")
        )
    except AuthError as exc:
        register_failed_attempt(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    clear_attempts(rate_limit_key)
    _set_auth_cookies(
        response,
        result.access_token,
        result.access_token_expires_at,
        result.refresh_token_raw,
        result.refresh_token_expires_at,
    )
    return LoginResponse(user=UserOut.model_validate(result.user))


@router.post("/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="لا توجد جلسة")

    service = AuthService(db)
    try:
        result = service.refresh(raw_refresh, user_agent=request.headers.get("user-agent"))
    except AuthError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    _set_auth_cookies(
        response,
        result.access_token,
        result.access_token_expires_at,
        result.refresh_token_raw,
        result.refresh_token_expires_at,
    )
    return LoginResponse(user=UserOut.model_validate(result.user))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    AuthService(db).logout(raw_refresh)
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
