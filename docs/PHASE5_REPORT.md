# تقرير PHASE 5 — Products + Pricing

## الحالة: ✅ مكتملة ومُختبرة (36/36 اختبار إجمالي)

## 1. ماذا تم بناؤه

- **المنتجات**: `GET/POST/PATCH /api/v1/products`، مع إنشاء Variants مباشرة عند إنشاء المنتج.
  القراءة متاحة لكل مستخدم مصادَق عليه (مدير أو موظفة — القاعدة 65: الموظفة تحتاج وصولًا سريعًا
  للاسم/السعر/الوحدة أثناء تسجيل الأوردر)، والكتابة للمدير فقط.
- **Variants**: `POST /products/{id}/variants`, `PATCH /product-variants/{id}` — كل تغيير سعر
  يُسجَّل في Audit Log بالقيمة القديمة والجديدة (action=`price_changed`).
- **العروض/Bundles**: `GET/POST/PATCH /api/v1/bundles` — يحسب `regular_total` (مجموع الأسعار
  العادية) تلقائيًا للمقارنة مع `bundle_price`. **منع تكرار نفس المنتج داخل نفس العرض تم التحقق
  منه فعليًا عبر API** (409)، معتمدًا على القيد المبني في PHASE 1.
- **قواعد الشحن** (القاعدة 66): `GET/POST/PATCH /api/v1/settings/shipping-rules` — بيانات Backend
  قابلة للإدارة، وليست ثوابت Frontend.
- **حالات التواصل** (القاعدة 11): `GET/POST/PATCH /api/v1/settings/statuses` — كود فريد لكل حالة،
  لون موحّد (`color_hex`)، ترتيب عرض (`sort_order`). تُقرأ مرة واحدة في الواجهة وتُستخدم كمصدر
  الألوان الموحّد بدل تكرارها Hard-coded.

## 2. اختبارات حقيقية (7 جديدة، 36 إجمالي)

| الاختبار | يتحقق من |
|---|---|
| `test_create_product_with_variants` | إنشاء منتج بأكثر من وحدة سعر دفعة واحدة |
| `test_duplicate_sku_rejected` | 409 عند تكرار SKU |
| `test_employee_can_read_but_not_create_products` | القراءة للجميع، الكتابة للمدير فقط |
| `test_price_change_updates_variant_and_is_visible` | تحديث السعر يعمل ويظهر فورًا |
| `test_bundle_creation_and_duplicate_item_rejected` | حساب `regular_total` صحيح + منع تكرار المنتج في نفس العرض (409 فعلي) |
| `test_shipping_rules_crud` | قواعد شحن قابلة للإدارة فعليًا |
| `test_status_configuration_crud_and_uniqueness` | حالات تواصل قابلة للإدارة + منع تكرار الكود |

## 3. الخطوة التالية

**PHASE 6: Orders** — Order Engine المركزي (Backend = Source of Truth للحساب)، Idempotency
(الجدول والحقل جاهزان من PHASE 1)، دعم الخصومات (نسبة/مبلغ ثابت)، ربط الشحن بقواعد PHASE 5،
قائمة الطلبات بفلاتر، وربطها بصفحة تفاصيل العميل.
