# خطة المراحل — Nexly CRM 2.0

كل مرحلة تُبنى، تُختبر، تُصلح، تُوثّق ثم تُدفع (commit) قبل الانتقال للتالية.
لا ننتقل لمرحلة جديدة إذا كانت الحالية بها Critical bugs.

| Phase | الوصف | الحالة |
|---|---|---|
| 1 | Architecture + Database | ✅ مكتملة — انظر `docs/PHASE1_REPORT.md` |
| 2 | Authentication + Roles | ⬜ لم تبدأ |
| 3 | Customers + Assignment | ⬜ لم تبدأ |
| 4 | Employees | ⬜ لم تبدأ |
| 5 | Products + Pricing | ⬜ لم تبدأ |
| 6 | Orders | ⬜ لم تبدأ |
| 7 | Interactions + Follow-ups + Complaints | ⬜ لم تبدأ |
| 8 | Dashboard + Reports | ⬜ لم تبدأ |
| 9 | Integrations (Google Sheets / WhatsApp / Shipping abstractions) | ⬜ لم تبدأ |
| 10 | Mobile UX | ⬜ لم تبدأ |
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
