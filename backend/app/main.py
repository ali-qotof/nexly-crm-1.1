"""
نقطة الدخول لتطبيق FastAPI.

في PHASE 1 هذا الملف يوفر فقط /health لإثبات أن التطبيق يقلع بشكل صحيح ويكتشف كل الـ Models
(القاعدة 57/59). المسارات الفعلية (Auth، Customers، Orders...) تُضاف تباعًا في المراحل القادمة
عبر app/api/v1، ولا تُكتب هنا مباشرة (فصل الطبقات — القاعدة 4).
"""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.assignments import router as assignments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.employees import router as employees_router
from app.api.v1.exports import router as exports_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.interactions import router as interactions_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.settings import router as settings_router
from app.config import get_settings
from app.db.session import engine
from app.utils.logging_config import configure_logging
from app.utils.middleware import RequestContextMiddleware
import app.models  # noqa: F401  يضمن أن كل الجداول مسجّلة في Base.metadata

settings = get_settings()
configure_logging()

app = FastAPI(
    title="Nexly CRM API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(assignments_router, prefix="/api/v1")
app.include_router(employees_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(interactions_router, prefix="/api/v1")
app.include_router(complaints_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(exports_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health():
    """
    فحص صحة فعلي (القاعدة 57/59): يجري SELECT 1 على قاعدة البيانات ويُرجع 503 إذا فشل، حتى لا
    يعتبر الـ Deployment ناجحًا لمجرد أن الـ Build نجح. لا يعرض أي سر أو رابط اتصال.
    """
    db_status, alembic_rev = "ok", None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            try:
                alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            except Exception:
                alembic_rev = None
    except Exception:
        db_status = "unavailable"
    body = {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "db_migration": alembic_rev,
        "version": settings.app_version,
        "git_commit": settings.git_commit,
        "build_time": settings.build_time,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(body, status_code=200 if db_status == "ok" else 503)
