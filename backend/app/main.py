"""
نقطة الدخول لتطبيق FastAPI.

في PHASE 1 هذا الملف يوفر فقط /health لإثبات أن التطبيق يقلع بشكل صحيح ويكتشف كل الـ Models
(القاعدة 57/59). المسارات الفعلية (Auth، Customers، Orders...) تُضاف تباعًا في المراحل القادمة
عبر app/api/v1، ولا تُكتب هنا مباشرة (فصل الطبقات — القاعدة 4).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.assignments import router as assignments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.employees import router as employees_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.interactions import router as interactions_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.settings import router as settings_router
from app.config import get_settings
import app.models  # noqa: F401  يضمن أن كل الجداول مسجّلة في Base.metadata

settings = get_settings()

app = FastAPI(
    title="Nexly CRM API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

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


@app.get("/health", tags=["system"])
def health() -> dict:
    """
    فحص صحة النظام (القاعدة 57). لا يُظهر أي أسرار — فقط الحالة والإصدار والبيئة.
    فحص قاعدة البيانات الفعلي (SELECT 1) يُضاف في PHASE 2 مع طبقة DB session الكاملة
    وتغطية اختبارات، حتى لا يفشل /health بشكل غامض قبل اكتمال طبقة الاتصال.
    """
    return {
        "status": "ok",
        "version": settings.app_version,
        "git_commit": settings.git_commit,
        "environment": settings.app_env,
    }
