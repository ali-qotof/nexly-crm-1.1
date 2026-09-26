"""
إعدادات التطبيق المركزية.

كل القيم الحساسة تُقرأ من متغيرات البيئة (.env محليًا، Environment Variables في الإنتاج).
لا يوجد أي سر مكتوب مباشرة هنا (راجع القاعدة 38 و60 في المتطلبات: لا أسرار في الكود أو الـ logs).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Auth
    nexly_secret: str
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"

    # App / diagnostics (Requirement 58/59: version & commit visibility)
    app_env: str = "development"
    app_version: str = "0.1.0"
    git_commit: str = "unknown"

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Integrations
    webhook_shared_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings مُخزّنة (cached) — تُقرأ مرة واحدة فقط."""
    return Settings()
