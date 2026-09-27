# تقرير PHASE 7 — Interactions + Follow-ups + Complaints

## الحالة: ✅ مكتملة ومُختبرة (50/50 اختبار إجمالي)

## 1. ماذا تم بناؤه

- **`app/services/access_control.py`**: دالة مركزية `ensure_customer_access` تتحقق أن الموظفة
  مخصص لها العميل قبل أي عملية (تفاعل/متابعة/شكوى/أوردر) — المدير يتجاوزها دائمًا. هذه الدالة
  هي **نقطة تطبيق واحدة** للقاعدة 5 بدل تكرار نفس الفحص في كل Service.
- **Interactions**: `POST /api/v1/interactions`, `GET /api/v1/customers/{id}/interactions` —
  Timeline مرتب زمنيًا (الأحدث أولًا)، منفصل تمامًا عن حالة الأوردر (القاعدة 11/12).
- **Follow-ups**: `POST /api/v1/followups`, `GET /api/v1/followups?bucket=due_today|overdue|upcoming`,
  `PATCH /api/v1/followups/{id}` (تعليم كمكتمل) — القاعدة 26 بالكامل، مع عزل الموظفة لمتابعاتها.
- **Complaints**: `POST/GET/PATCH /api/v1/complaints`, ورفع مرفقات
  `POST /complaints/{id}/attachments` — القاعدة 27. تخزين ملفات محلي بسيط
  (`app/utils/file_storage.py`) بحد 10MB ونوع ملف مسموح (jpg/png/webp/pdf)، **موثّق صراحة كقيد
  مؤقت** يجب استبداله بتخزين سحابي (Supabase Storage) قبل PHASE 13.

## 2. إصلاح رجعي مهم اكتُشف أثناء هذه المرحلة

أثناء بناء `ensure_customer_access`، تبيّن أن **PHASE 6 (Orders) لم تكن تتحقق من تخصيص العميل
للموظفة عند إنشاء الطلب** — أي موظفة كانت تستطيع تقنيًا إنشاء طلب لأي عميل حتى لو لم يكن مخصصًا
لها، طالما تعرف الـ `customer_id`. تم إصلاحه فورًا بربط `OrderService.create_order` بنفس دالة
`ensure_customer_access`، وأُضيف اختبار رجعي صريح (`test_order_creation_blocked_for_unassigned_customer`)
يتحقق أن المحاولة تُرفض بـ 400 الآن. اختباران من PHASE 6
(`test_employee_only_sees_own_orders`, `test_cancel_order_manager_only`) كانا يعتمدان (بدون قصد)
على غياب هذا الفحص، فتم تعديلهما ليُسندا العميل للموظفة أولًا قبل إنشاء الطلب — وهو السلوك
الصحيح المطلوب أصلًا.

## 3. اختبارات حقيقية (7 جديدة + 1 رجعي، 50 إجمالي)

| الاختبار | يتحقق من |
|---|---|
| `test_employee_cannot_interact_with_unassigned_customer` | 403 فعلي |
| `test_employee_can_interact_with_assigned_customer_and_timeline_orders_desc` | تسجيل تفاعلات + ترتيب Timeline |
| `test_followup_buckets_due_today_overdue_upcoming` | تصنيف المتابعات بدقة زمنية فعلية |
| `test_followup_mark_done_removes_from_active_lists` | إكمال متابعة يخرجها من القوائم النشطة |
| `test_complaint_creation_and_status_update_with_attachment` | شكوى + رفع صورة حقيقية + تحديث حالة |
| `test_complaint_rejects_disallowed_file_type` | رفض امتداد ملف غير مسموح (400) |
| `test_order_creation_blocked_for_unassigned_customer` | الإصلاح الرجعي أعلاه |

## 4. الخطوة التالية

**PHASE 8: Dashboard + Reports** — Aggregated queries لكل مؤشرات المدير والموظفة (القاعدة 8/29/30)،
بفلاتر تاريخ، بدون تحميل كل البيانات للمتصفح.
