# تقرير PHASE 2 — Authentication + Roles

## الحالة: ✅ مكتملة ومُختبرة فعليًا (وحدة + E2E عبر HTTP حقيقي + تشغيل حي)

## 1. ماذا تم بناؤه

- **تجزئة كلمات المرور**: bcrypt عبر passlib (`app/auth/security.py`).
- **Access Token**: JWT قصير العمر (60 دقيقة افتراضيًا)، يُحمل في HTTP-only Secure cookie
  (`nexly_access`) — وليس localStorage، لتقليل مخاطر XSS.
- **Refresh Token**: عشوائي عالي الإنتروبيا (`secrets.token_urlsafe`)، يُخزَّن كـ **hash فقط**
  في جدول `refresh_tokens`، مع **Rotation** عند كل استخدام: التوكن القديم يُبطَل فورًا ويُصدَر
  توكن جديد. إذا وصل توكن مُبطَل مسبقًا (يدل على سرقة/إعادة استخدام) → **تُبطَل كل جلسات
  المستخدم احترازيًا** ويُسجَّل الحدث في Audit Log.
- **Rate limiting لتسجيل الدخول**: حظر بعد 5 محاولات فاشلة خلال 5 دقائق (in-process — موثّق
  كقيد صريح أدناه، وليس إخفاءً للمشكلة).
- **رسالة خطأ موحّدة** لعدم الكشف عن وجود/عدم وجود اسم المستخدم (منع User enumeration).
- **Dependencies للحماية**: `get_current_user` (401 عند غياب/فساد الجلسة)، `require_role` /
  `require_manager` / `require_any_authenticated` لصلاحيات المدير مقابل الموظفة (القاعدة 5).
- **Endpoints**: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`,
  `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.
- **Audit Log**: `login_success`, `login_failed`, `logout`, `refresh_token_reuse_detected` —
  كلها تُسجَّل فعليًا (تم التحقق في الاختبارات).
- **سكربت تأسيس أول مدير** (`backend/scripts/create_manager.py`): يحل مشكلة "البيضة والدجاجة"
  (لا يوجد مدير لإنشاء موظفين قبل أن يوجد مدير أصلًا) — تفاعلي، كلمة المرور لا تُمرَّر كـ argument
  حتى لا تبقى في تاريخ الأوامر.

## 2. الجدول الجديد

`refresh_tokens` (user_id, token_hash فريد، expires_at، revoked، replaced_by_hash، user_agent) —
Migration مستقلة (`phase2_refresh_tokens`)، تم تطبيقها والتحقق من دورة upgrade/downgrade/upgrade.

## 3. اختبارات حقيقية (14/14 ناجحة، 5 من Phase 1 + 9 جديدة)

| الاختبار | يتحقق من |
|---|---|
| `test_login_success_sets_cookies_and_returns_user` | تسجيل دخول ناجح + كوكيز صحيحة |
| `test_login_wrong_password_...` / `test_login_unknown_user_...` | رسالة 401 موحّدة (لا كشف عن وجود المستخدم) |
| `test_me_requires_authentication` | 401 بدون جلسة |
| `test_me_returns_current_user_after_login` | الجلسة تعمل فعليًا |
| `test_refresh_rotates_token_and_old_one_becomes_invalid` | Rotation + إبطال التوكن القديم |
| `test_logout_invalidates_session` | Logout يُبطل الجلسة فعليًا |
| `test_rate_limiting_blocks_after_repeated_failures` | حظر بعد 5 محاولات فاشلة (429) |
| `test_disabled_employee_cannot_login` | موظف معطَّل لا يستطيع الدخول |

كل الاختبارات تعمل عبر `TestClient` (HTTP فعلي بكوكيز حقيقية) ضد PostgreSQL حقيقي — وليست Mocks.

بالإضافة، تم تشغيل **خادم Uvicorn حي فعليًا** وتنفيذ دورة كاملة عبر `curl`:
تسجيل دخول → `/me` بنجاح → `/me` بدون كوكي (401) → `/refresh` ناجح. كل الاستجابات تحققت يدويًا.

## 4. خطأ حقيقي تم اكتشافه وإصلاحه

**تعارض إصدارات `passlib` + `bcrypt`**: الإصدار الحديث من مكتبة `bcrypt` (4.1+) أزال خاصية
داخلية كانت `passlib 1.7.4` تعتمد عليها، فكان أي استدعاء لـ `hash_password` يفشل فورًا بخطأ
`password cannot be longer than 72 bytes` (خطأ داخلي في فحص التوافق لدى passlib نفسها، ليس
متعلقًا بطول كلمة مرور المستخدم الفعلية). تم إصلاحه بتثبيت `bcrypt==4.0.1` صراحة في
`requirements.txt`، والتحقق من نجاح hash/verify فعليًا بعدها.

## 5. قيود موثّقة صراحة

- **Rate limiting in-process**: يعمل بشكل صحيح لعملية Uvicorn واحدة. عند تشغيل أكثر من
  Worker/Instance في الإنتاج (وهو المتوقع لتحمّل الحمل)، يجب الانتقال لمخزن مشترك (Redis) —
  هذا مطلوب فعليًا قبل PHASE 13 (Deployment)، وسيُعاد النظر فيه حينها.
- **Cookie `secure=True`** مفعّل فقط عند `APP_ENV=production` (لأن HTTPS غير متاح محليًا أثناء
  التطوير) — يجب التأكد أن الإنتاج يعمل عبر HTTPS دائمًا قبل النشر.
- لم يُبنَ بعد Boot Sequence الكامل في الواجهة الأمامية (القاعدة 7) — هذا يبدأ عمليًا في
  PHASE 3/4 عند بناء أول صفحات React الفعلية، وسيُستخدم `GET /api/v1/auth/me` كخطوة "Validate
  session" ضمن ذلك التسلسل.

## 6. الخطوة التالية

**PHASE 3: Customers + Assignment** — CRUD كامل للعملاء (server-side pagination/search/filter
لتحمّل 100k+)، شاشة "عملائي" للموظفة، ونظام التوزيع (Assignment Manager) بكل قواعده (منع
Duplicate، Bulk assign/unassign، Import من Excel/CSV مع Preview).
