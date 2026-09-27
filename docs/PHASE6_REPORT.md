# تقرير PHASE 6 — Orders

## الحالة: ✅ مكتملة ومُختبرة (43/43 اختبار إجمالي) — بما فيها Primary Acceptance Test (القاعدة 55)

## 1. ماذا تم بناؤه

- **محرّك حساب مركزي** (`app/services/pricing_service.py`) — Backend هو المصدر الوحيد للحساب
  (القاعدة 19):
  - يدعم بنود منتجات (Variant) وبنود عروض (Bundle) في نفس الطلب.
  - خصم نسبة مئوية أو مبلغ ثابت، مع سقف: **الخصم لا يتجاوز قيمة الطلب أبدًا** مهما كانت النسبة/القيمة.
  - شحن مبني على قواعد `ShippingRule` القابلة للإدارة من PHASE 5 (مطابقة بمحافظة العميل، مع حد
    أدنى للشحن المجاني، وقاعدة احتياطية `other`).
- **`POST /api/v1/orders`**: إنشاء طلب. **Idempotency حقيقي**: نفس `idempotency_key` يُرجع دائمًا
  نفس الطلب (نفس `id`) بدل إنشاء نسخة جديدة — تم التحقق بثلاث محاولات متتالية بنفس المفتاح تُنتج
  صفًا واحدًا فقط في قاعدة البيانات.
- **`GET /api/v1/orders`**: قائمة مع فلاتر (موظف، عميل، حالة، مدى تاريخ) + Pagination. **عزل
  صارم**: الموظفة تُقيَّد تلقائيًا لطلباتها فقط بغض النظر عمّا تمرره في الفلتر (القاعدة 5 تمتد
  للطلبات).
- **`GET /api/v1/orders/{id}`**: تفاصيل طلب، بحماية 403 إن حاولت موظفة فتح طلب موظفة أخرى.
- **`POST /api/v1/orders/{id}/cancel`**: إلغاء — مدير فقط.

## 2. القاعدة 55 — Primary Acceptance Test: ✅ نجح بالكامل فعليًا

تم تنفيذ السيناريو الحرج الكامل حرفيًا كاختبار واحد (`test_primary_acceptance_flow_end_to_end`)
عبر HTTP حقيقي ضد PostgreSQL حقيقي:

Manager Login → Add Employee → Assign Customer → Employee Login → View My Customers →
Open Customer → Register Interaction → Create Order → Add products → Calculate price →
Save Order → **Refresh (GET جديد)** → **Order remains** → Open customer →
**Order appears in history** — كل خطوة تحققت بـ `assert` صريح، وليس افتراضًا.

## 3. أخطاء حقيقية تم اكتشافها وإصلاحها

**استعلام العدّ (Count) في `list_orders` كان يُنتج Cartesian Product**: التنفيذ الأول استخدم
`select(Order.id).select_from(stmt.subquery())` حيث `stmt` يحمل `selectinload` options، ما
أنتج تحذير SQLAlchemy صريح (`cartesian product`) ونتيجة عدد خاطئة تمامًا (**9 بدل 1** في اختبار
فعلي). تم اكتشافه لأن اختباري `test_employee_only_sees_own_orders` و
`test_primary_acceptance_flow_end_to_end` فشلا فعليًا عند التشغيل — لم يكن خطأ نظريًا.
الإصلاح: بناء شروط الفلترة مرة واحدة (`conditions` كقائمة)، واستخدامها في استعلامين منفصلين
ونظيفين: `select(func.count(Order.id)).where(*conditions)` للعدّ، واستعلام منفصل للصفحة الفعلية.

## 4. قرارات تصميمية

- **رقم الطلب البشري** (`order_number`) يُولَّد تسلسليًا (`ORD-000001`) — بسيط وكافٍ للحجم الحالي.
  **قيد معروف**: الاعتماد على `COUNT` لتوليد الرقم التالي عرضة لتضارب نادر تحت تحميل متزامن عالٍ
  جدًا (لا يؤثر على صحة البيانات لأن `idempotency_key` هو الحارس الحقيقي ضد التكرار، فقط قد يُنتج
  رقمًا غير متسلسل تمامًا في حالات نادرة). سيُستبدل بـ PostgreSQL `SEQUENCE` مخصص إذا ظهر هذا في
  اختبارات الحمل قبل PHASE 13.
- تسجيل التفاعل (Interaction) في الاختبار استُخدم مباشرة عبر الـ Model وليس عبر API مخصص — لأن
  **PHASE 7 (Interactions + Follow-ups + Complaints)** هي المسؤولة عن بناء تلك الـ Endpoints،
  والجدول والعلاقات جاهزة بالفعل من PHASE 1.

## 5. الخطوة التالية

**PHASE 7: Interactions + Follow-ups + Complaints** — Endpoints فعلية لتسجيل حالة التواصل
(مرتبط بـ `status_configurations` من PHASE 5)، Follow-ups مجدولة، الشكاوى مع دعم رفع مرفقات.
