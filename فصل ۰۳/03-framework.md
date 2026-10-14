# فصل ۳ — از نیازمندی تا طراحی قابل اجرا

**عنوان کتاب:** A Framework For System Design Interviews · صفحات ۴۲ تا ۵۰ PDF.

## چهار مرحلهٔ فصل

1. مسئله و Scope را روشن کن: چه کارهایی لازم‌اند؟ مقیاس، Latency و Consistency چقدر مهم‌اند؟
2. طرح کلی و مسیر داده را پیشنهاد بده و دربارهٔ فرض‌ها توافق کن.
3. روی بخش‌های دشوار عمیق شو؛ برای همهٔ اجزا زمان مساوی نگذار.
4. محدودیت، نقطهٔ خرابی، رشد و جمع‌بندی طراحی را توضیح بده.

برای فروشگاه ما، Scope اولیه «مشاهدهٔ کتاب و تغییر قیمت توسط مدیر» است. پرداخت و انبار هنوز داخل آن نیستند. Read فهرست می‌تواند کمی تأخیر داشته باشد؛ پاسخ تغییر قیمت باید مقدار ثبت‌شده را نشان دهد. این تفاوت مستقیماً انتخاب Replica و Primary را تعیین می‌کند.

## تبدیل Scope به قرارداد کد

قبل از نوشتن View این جدول را تهیه کن:

| عملیات | مسیر | مجوز | منبع خواندن | خروجی خطا |
|---|---|---|---|---|
| جزئیات کتاب | `GET /books/<id>/` | عمومی | Cache یا Primary | ۴۰۴ |
| جزئیات تازه | `GET /books/<id>/?fresh=1` | عمومی | Primary | ۴۰۴ |
| تغییر قیمت | `POST /books/<id>/price/` | مدیر دارای Permission | Primary | ۴۰۰، ۴۰۳، ۴۰۴ |

نمونهٔ پروژهٔ فصل اول (کد رزرو مخصوص این فصل در آزمایشگاه پایین آمده):

```python
@require_POST
@login_required
def change_price(request, pk):
    if not request.user.has_perm("catalog.change_book"):
        return JsonResponse({"error": "permission required"}, status=403)
    # Parse and validate JSON; call the service; map errors to HTTP.
    # Complete implementation in chapter 1: lab/catalog/views.py
```

قرار دادن منطق تغییر داده در `update_price` باعث می‌شود همان قواعد از View، Command یا Worker قابل استفاده باشند. صرف داشتن Service Layer معماری را مقیاس‌پذیر نمی‌کند؛ اما محل تصمیم‌های مهم مثل Transaction، Routing و Cache Invalidation را روشن می‌کند.

## Deep Dive کاربردی

در این Scope دو سؤال ارزش بیشتری از انتخاب اسم سرویس‌ها دارند: اگر مدیر قیمت را عوض کرد Replica چه نشان می‌دهد؟ اگر Transaction شکست خورد Cache چه می‌شود؟ فصل اول برای هر دو کد و تست دارد. برای پروژهٔ پرداخت، سؤال مهم‌تر می‌تواند اجرای تکراری و جلوگیری از دو بار برداشت باشد.

یک تصمیم طراحی کوچک را این‌طور ثبت کن: «برای مشاهدهٔ عمومی، Cache با TTL سی‌ثانیه‌ای داریم؛ برای تأیید تغییر، Primary خوانده می‌شود. مزیت: Readهای تکراری کم می‌شوند. هزینه: نمایش عمومی می‌تواند قدیمی بماند.» این بیان قابل آزمون است.

**تمرین:** اگر کاربر خواست موجودی هنگام پرداخت دقیق باشد چه تغییر می‌کند؟ **پاسخ:** خواندن Replica کافی نیست؛ رزرو موجودی باید روی منبع اصلی و با کنترل همزمانی انجام شود. Scope، مدل داده و Transaction باید تغییر کنند.

این فصل الگوریتم تازه‌ای ندارد؛ مثال پیاده‌سازی آن، تبدیل نیازمندی به API، Service و تست است.


## یک طراحی کامل کوچک: رزرو موجودی

برای تمرین Scope را عوض می‌کنیم: کاربر یک کالا را رزرو می‌کند؛ تعداد نباید منفی شود؛ Retry درخواست موفق نباید دوباره موجودی کم کند. پرداخت واقعی هنوز داخل Scope نیست. این سه نیاز، سه تصمیم کدی ایجاد می‌کنند: Transaction روی Primary، کنترل همزمانی روی موجودی و Idempotency Key برای درخواست.

مدل `Inventory` دارای `available` است؛ مدل `Reservation` مالک، کالا، تعداد و `request_id` دارد. قید DB برای موجودی غیرمنفی و یکتایی درخواست ایجاد می‌کنیم. منطق کامل در `lab/demo/services.py` است؛ قسمت مهم:

```python
with transaction.atomic(using="default"):
    item = Inventory.objects.using("default").select_for_update().get(pk=item_id)
    previous = Reservation.objects.using("default").filter(request_id=request_id).first()
    if previous:
        # Return only if user, item and quantity match the original request.
        return previous
    if item.available < quantity:
        raise NotEnoughStock()
    item.available -= quantity
    item.save(using="default", update_fields=["available"])
    reservation = Reservation.objects.using("default").create(
        user_id=user_id, inventory=item, quantity=quantity, request_id=request_id)
```

کد کوتاه بالا برای خواندن مسیر است؛ بررسی تطابق Retry در فایل کامل انجام می‌شود. `user_id` را از هویت احراز‌شدهٔ Server بگیر، نه ادعای Client. کلید تکراری با Payload متفاوت باید خطا بدهد. برای پاسخ HTTP، کمبود موجودی یا تناقض Retry را به 409 تبدیل کن؛ ورودی نامعتبر 400 و هویت نامعتبر خطای دسترسی است.

در PostgreSQL، `select_for_update` روی سطر کالا اجازه نمی‌دهد دو رزرو از همان مقدار قدیمی کم کنند. `atomic` باعث می‌شود کاهش موجودی و ساخت Reservation با هم موفق یا Rollback شوند. SQLite تمرین مسیر را اجرا می‌کند ولی همان Row Lock را ندارد؛ آزمون همزمانی را روی PostgreSQL انجام بده.

## از طرح کلی تا سناریوی خرابی

```text
Authenticated request → validate quantity/key → primary transaction
                                               ├─ replay existing result
                                               └─ lock stock → reserve → commit
```

اگر پاسخ شبکه گم شود ولی Commit موفق شده باشد، Client همان `request_id` را تکرار می‌کند و Reservation قبلی را می‌گیرد. اگر Transaction Rollback شده باشد، Retry عملیات تازه‌ای انجام می‌دهد. این تفاوت را در تست طراحی بررسی می‌کنیم. اگر صف اعلان اضافه کنیم، Outbox باید داخل همین Transaction ایجاد شود؛ فصل ۱۰ آن را اجرا می‌کند.

زمان قفل را کوتاه نگه دار. تماس با درگاه پرداخت یا ایمیل داخل این Transaction نگذار؛ زمان شبکه قابل پیش‌بینی نیست. برای رزرو زمان‌دار، فیلد Expiry و Worker آزادسازی لازم است و آزادسازی هم باید Idempotent باشد. محدودیت‌های تازه را صریح به Scope اضافه کن.

## تصمیم‌ها را چطور در مصاحبه توضیح بدهیم؟

اول نیاز را بگو: «نباید بیش از موجودی رزرو کنیم». بعد گزینه‌ها: Row Lock، Conditional Update یا Serializability با Retry. سپس انتخاب: «برای این نسخه تک‌دیتابیس، Row Lock روی همان کالا». آخر محدودیت: «کالای بسیار محبوب باعث انتظار روی یک سطر می‌شود». اسم Lock بدون این اتصال به نیاز، طراحی را توضیح نمی‌دهد.

در Wrap-up، مسیر موفق، Retry و خرابی را دوباره مرور کن. مهم‌ترین معیارها برای این قابلیت تعداد Conflict، زمان انتظار قفل، p95 و رزروهای منقضی‌اند. اضافه کردن Cache به موجودی نمایشی ممکن است خوب باشد؛ تصمیم نهایی رزرو نباید از Cache قدیمی بیاید.

## تمرین و پاسخ

1. یک واحد موجودی داریم و دو درخواست مستقل داریم؛ آیا هر دو باید موفق شوند؟ — خیر؛ حداکثر یکی. روی PostgreSQL با دو اتصال و Barrier این سناریو را بررسی کن.
2. همان Request ID با تعداد جدید فرستاده شود چه کنیم؟ — تناقض است؛ برگرداندن موفقیت قبلی بدون بررسی Payload گمراه‌کننده است.
3. بعد از کم کردن موجودی Exception رخ بدهد چه می‌شود؟ — در همان Transaction، موجودی و Reservation هر دو Rollback می‌شوند.
4. چرا درخواست رزرو را به Replica نمی‌فرستیم؟ — خواندن عقب‌مانده می‌تواند تصمیم نادرست دربارهٔ موجودی بدهد و محل Write هم Primary است.

**روش مطالعه:** نیازمندی را قبل از دیدن کد روی کاغذ بنویس، سه سناریوی شکست تعریف کن و بعد ببین Service کدام را پوشش می‌دهد. کد آزمایشگاه کل محصول سفارش/پرداخت نیست.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 4 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
