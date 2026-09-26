# Nexly CRM 2.0

CRM حقيقي (Production-Grade) لفريق مبيعات وخدمة عملاء تجارة إلكترونية للتمور والمكسرات والفواكه المجففة.

هذا المستودع يُبنى من الصفر على فرع `nexly-rebuild-2026-09-26` وفق خطة مراحل واضحة (PHASE 1 → PHASE 13)
موثقة في `docs/PHASES.md`. لا يُدمج إلى `main` إلا بعد اجتياز اختبارات كل مرحلة.

## البنية

```
/backend    - FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL (Supabase)
/frontend   - React + TypeScript + Vite + TanStack Query
/tests      - اختبارات Backend و Frontend
/docs       - توثيق Architecture والقرارات التصميمية
```

## حالة المشروع

انظر `docs/PHASES.md` لتتبع تقدّم كل مرحلة.

الحالة الحالية: **PHASE 1 — Architecture + Database** (قيد الإنجاز).

## المتطلبات الأساسية للتشغيل المحلي

### Backend
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # عدّل القيم
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## ملاحظة أمان

لا تُرفع أي أسرار (DATABASE_URL، JWT secrets، مفاتيح Supabase) إلى Git. استخدم `.env` محليًا
ومتغيرات بيئة في الاستضافة الفعلية. راجع `.env.example` في كل من `backend` و`frontend`.
