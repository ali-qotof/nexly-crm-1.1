# تقرير PHASE 4 — Employees

## الحالة: ✅ مكتملة ومُختبرة (29/29 اختبار إجمالي)

## 1. ماذا تم بناؤه

- **`GET /api/v1/employees`**: قائمة الموظفات + عدد العملاء المخصصين لكل واحدة (استعلام مجمّع
  واحد، لا N+1).
- **`POST /api/v1/employees`**: إنشاء موظفة (اسم مستخدم فريد، كلمة مرور 8+ أحرف، Hash فورًا).
  تسجّل Audit Log `employee_created`.
- **`PATCH /api/v1/employees/{id}`**: تعديل الاسم و/أو `is_active` (نفس المسار يُستخدم للتعطيل
  وإعادة التفعيل — القاعدة 5).
- **`POST /api/v1/employees/{id}/delete`**: تنفيذ القاعدة 16 حرفيًا:
  - Manager only (مضمون عبر `require_manager`).
  - يتطلب **كلمة مرور المدير الحالي (actor)** قبل التنفيذ — وليس أي كلمة مرور، وتم التحقق أن
    كلمة مرور خاطئة تُرفض بـ 401.
  - **Soft delete فقط** (`is_active=False`, `deleted_at=now`) — لا حذف فعلي من قاعدة البيانات.
  - **يحرر كل عملائها المخصصين تلقائيًا** (`is_active=False` على `CustomerAssignment`) —
    تم التحقق أن العميل يصبح بلا تخصيص نشط فورًا بعد الحذف.
  - **لا يحذف تاريخ الأوردرات أو التفاعلات** — تبقى مرتبطة بمعرّف المستخدم القديم للأرشفة (لم
    تُحذف أي صفوف من `orders`/`interactions`، فقط `assignments` أصبحت غير نشطة).
  - الموظفة المحذوفة لا تستطيع تسجيل الدخول بعدها (يتكامل تلقائيًا مع PHASE 2: `get_current_user`
    و`AuthService.login` يرفضان أي مستخدم بـ `deleted_at != NULL`).

## 2. اختبارات حقيقية (7 جديدة، 29 إجمالي)

| الاختبار | يتحقق من |
|---|---|
| `test_employee_creation_full_flow` | إنشاء موظفة → تسجيل دخولها فعليًا يعمل فورًا |
| `test_duplicate_username_rejected` | 409 عند تكرار اسم المستخدم |
| `test_employee_cannot_create_employees` | 403 — عزل صلاحيات المدير |
| `test_disable_and_reenable_employee` | تعطيل يمنع الدخول، إعادة تفعيل تُعيده |
| `test_delete_employee_requires_correct_manager_password` | 401 بكلمة مرور خاطئة، 204 بالصحيحة |
| `test_delete_employee_frees_customers_and_preserves_history` | تحرير العملاء + Soft delete + منع الدخول |
| `test_employee_list_shows_assigned_customers_count` | العداد صحيح فعليًا بعد التوزيع |

## 3. الخطوة التالية

**PHASE 5: Products + Pricing** — إدارة المنتجات والمتغيرات (Variants بأوزان/أسعار مختلفة)،
العروض/Bundles، مع منع تكرار المنتج داخل نفس العرض (مبني بالفعل في الـ Schema من PHASE 1، تبقى
طبقة الـ API والـ Service).
