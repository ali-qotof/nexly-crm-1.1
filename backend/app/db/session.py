"""
إعداد الاتصال بقاعدة البيانات (Engine + Session).

يُستخدم Connection pooling مناسب لتحمّل الحمل المطلوب (100k+ عميل، طلبات متزامنة من الموظفات).
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # يتجنب استخدام اتصالات ميتة (خصوصًا خلف Supabase pooler)
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: جلسة واحدة لكل Request، تُغلق دائمًا بعد الانتهاء."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
