import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost/nexly_test"
)
os.environ.setdefault("NEXLY_SECRET", "test-secret")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

settings = get_settings()
engine = create_engine(settings.database_url)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """ينشئ كل الجداول مباشرة من الـ Models على قاعدة الاختبار (بديل أسرع من alembic لكل تشغيلة اختبار،
    بينما صحة الـ migrations نفسها تُتحقق منفصلًا عبر alembic upgrade/downgrade — راجع docs/PHASE1_REPORT.md)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Session:
    session = TestSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
