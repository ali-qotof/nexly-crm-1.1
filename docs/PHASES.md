# خطة المراحل — Nexly CRM 2.0

كل مرحلة تُبنى، تُختبر، تُصلح، تُوثّق ثم تُدفع (commit) قبل الانتقال للتالية.
لا ننتقل لمرحلة جديدة إذا كانت الحالية بها Critical bugs.

| Phase | الوصف | الحالة |
|---|---|---|
| 1 | Architecture + Database | ✅ مكتملة — انظر `docs/PHASE1_REPORT.md` |
| 2 | Authentication + Roles | ✅ مكتملة — انظر `docs/PHASE2_REPORT.md` |
| 3 | Customers + Assignment | ✅ مكتملة — انظر `docs/PHASE3_REPORT.md` |
| 4 | Employees | ✅ مكتملة — انظر `docs/PHASE4_REPORT.md` |
| 5 | Products + Pricing | ✅ مكتملة — انظر `docs/PHASE5_REPORT.md` |
| 6 | Orders | ✅ مكتملة — انظر `docs/PHASE6_REPORT.md` |
| 7 | Interactions + Follow-ups + Complaints | ✅ مكتملة — انظر `docs/PHASE7_REPORT.md` |
| 8 | Dashboard + Reports | ✅ مكتملة — انظر `docs/PHASE8_REPORT.md` |
| 9 | Integrations (Google Sheets / WhatsApp / Shipping abstractions) | ✅ مكتملة (بنية + webhook) — انظر `docs/PHASE9_REPORT.md` |
| 10 | Frontend + Mobile UX | 🟡 مبنية وتجتاز الفحص الآلي، بدون تحقق بصري — انظر `docs/PHASE10_REPORT.md` |
| 11 | Testing | ⬜ لم تبدأ |
| 12 | Migration (بيانات حقيقية) | ⬜ لم تبدأ — يتطلب تصدير حقيقي للبيانات أو اتصال مباشر بقاعدة المصدر |
| 13 | Production Deployment | ⬜ لم تبدأ — يتطلب صلاحيات نشر فعلية (FastAPI Cloud / Supabase) |

## قيود بيئة التنفيذ الحالية (يجب معرفتها)

- **لا يوجد اتصال شبكة من بيئة التنفيذ هذه إلى Supabase أو أي مضيف قواعد بيانات خارجي.**
  لذلك Alembic migrations تُكتب وتُختبر محليًا على PostgreSQL مؤقتة داخل الحاوية، لا على قاعدة الإنتاج الفعلية.
- **لا يوجد اتصال لنشر فعلي (Deploy) على FastAPI Cloud.** ملفات ومتطلبات النشر (Dockerfile، إعدادات health check، إلخ)
  تُجهَّز بالكامل في PHASE 13، لكن الضغط الفعلي على "Deploy" يحتاج تنفيذه من جهتكم أو عبر ربط بيئة تنفيذ متصلة.
- **Migration من بيانات الإنتاج الحقيقية (84,414 عميل، إلخ) يتطلب ملف تصدير فعلي (CSV/SQL dump) يُرفع في هذه المحادثة**،
  أو الاتصال المباشر بقاعدة المصدر. سكربت الـ Migration في PHASE 12 يُكتب بحيث يقبل أي من المصدرين، مع مقارنة أعداد
  (Count comparison) والتوقف الفوري (STOP) عند أي اختلاف، كما هو مطلوب.

كل ما عدا ذلك (الكود، الـ Schema، الـ API، الـ Frontend، الاختبارات) يُبنى بالكامل وفعليًا في هذا المستودع.
