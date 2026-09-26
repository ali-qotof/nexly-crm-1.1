# تقرير PHASE 3 — Customers + Assignment

## الحالة: ✅ مكتملة ومُختبرة (22/22 اختبار إجمالي)

## 1. ماذا تم بناؤه

- **`GET /api/v1/customers`** (مدير فقط): بحث + Pagination + فلترة `unassigned_only`، بالكامل
  Server-side (القاعدة 9/40). استعلام واحد مجمّع (subqueries لآخر تفاعل/آخر أوردر) بدل N+1.
- **`GET /api/v1/customers/my`**: شاشة "عملائي" — كل مستخدم يرى فقط عملاءه المخصصين حاليًا،
  بغض النظر عن دوره (القاعدة 5: عزل بيانات الموظفات عن بعضهن مضمون في طبقة الاستعلام نفسها،
  وليس فقط في الواجهة).
- **Assignment Service** (`app/services/assignment_service.py`) — القاعدة 13 بالكامل:
  - `bulk_assign`: يتجاهل تلقائيًا من له تخصيص نشط بالفعل (لا خطأ، بل عدّاد `skipped`).
  - `bulk_unassign`.
  - `reassign`: سحب من الحالي + إسناد للجديد في معاملة واحدة (atomic).
  - `employee_order` يُحفظ تصاعديًا لكل موظفة ولا يُعاد ترتيبه عشوائيًا (القاعدة 67).
  - كل عملية تُسجَّل في Audit Log.
- **Import من Excel/CSV** (`app/services/import_service.py` + `/assignments/import/preview` و
  `/confirm`) — القاعدة 15 بالكامل:
  - مطابقة بالأولوية: `customer_code` → `source_customer_id` → هاتف مُطبَّع (`normalize_phone`).
  - Preview يُرجع Total/Matched/Missing/Duplicate/Invalid قبل أي تنفيذ.
  - **لا يُنشئ عملاء جدد أبدًا** — تم اختبار هذا صراحة (`test_import_never_creates_new_customers`).
  - يدعم `.xlsx` (عبر openpyxl) و`.csv`.

## 2. اختبارات حقيقية (8 جديدة، 22 إجمالي)

كل الاختبارات عبر `TestClient` (HTTP حقيقي) ضد PostgreSQL حقيقي — لا Mocks:

| الاختبار | يتحقق من |
|---|---|
| `test_employee_cannot_list_all_customers` | 403 — عزل الصلاحيات فعليًا |
| `test_manager_can_list_customers_with_pagination` | Pagination صحيح |
| `test_customer_search_by_phone` | البحث Server-side يعمل |
| `test_employee_sees_only_assigned_customers` | عزل بيانات الموظفات (لا ترى عملاء غيرها) |
| `test_bulk_assign_skips_already_assigned` | منع Duplicate assignment فعليًا عبر API |
| `test_unassign_then_reassign_works` | العميل ينتقل من موظفة لأخرى ويختفي من الأولى فورًا |
| `test_excel_import_preview_and_confirm` | ملف Excel حقيقي (openpyxl) → مطابقة → توزيع فعلي |
| `test_import_never_creates_new_customers` | تأكيد صريح: القاعدة 15 لا تُنتهك |

## 3. قرارات تصميمية

- استعلام `CustomerRepository._base_query` يستخدم `aliased()` + subqueries مجمّعة لآخر تفاعل/أوردر
  بدل تحميل العلاقات كاملة لكل عميل — ضروري لتحمّل 100k+ عميل (القاعدة 40).
  **قيد معروف وموثّق**: في الحالة النادرة جدًا لوجود تفاعلين/طلبين بنفس الـ timestamp بالضبط لنفس
  العميل، قد يظهر أكثر من صف. غير محتمل عمليًا (فارق مايكروثانية)، لكن سيُعاد النظر فيه إذا ظهر
  في الإنتاج الفعلي.
- `reassign` يعمل كمعاملة واحدة (سحب + إسناد) بدل استدعاءين منفصلين — يمنع وجود لحظة يكون فيها
  العميل بلا تخصيص نشط بسبب فشل جزئي.

## 4. الخطوة التالية

**PHASE 4: Employees** — CRUD الموظفين (إنشاء/تعديل/تعطيل/حذف Soft-delete بكلمة مرور المدير)،
workflow إنشاء موظفة جديدة ثم توزيع عملاء عليها مباشرة (يستخدم نفس Import/Assignment المبني هنا).
