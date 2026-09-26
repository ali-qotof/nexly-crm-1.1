"""
نقطة الدخول لتطبيق FastAPI.

في PHASE 1 هذا الملف يوفر فقط /health لإثبات أن التطبيق يقلع بشكل صحيح ويكتشف كل الـ Models
(القاعدة 57/59). المسارات الفعلية (Auth، Customers، Orders...) تُضاف تباعًا في المراحل القادمة
عبر app/api/v1، ولا تُكتب هنا مباشرة (فصل الطبقات — القاعدة 4).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
