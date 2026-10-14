# فصل ۷ — تولید شناسهٔ یکتا

**عنوان کتاب:** Design A Unique ID Generator In Distributed Systems · صفحات ۱۱۰ تا ۱۱۸ PDF.

## اول نیاز شناسه را تعیین کن

آیا فقط Unique بودن کافی است؟ آیا باید ۶۴بیتی و قابل مرتب‌سازی زمانی باشد؟ چند Worker داریم؟ آیا شناسه در URL عمومی دیده می‌شود؟ شناسهٔ افزایشی یک DB ساده است، اما چند نویسندهٔ مستقل به هماهنگی یا فضای شناسهٔ جدا نیاز دارند.

فصل چهار گزینه را مقایسه می‌کند: Auto-increment در چند Master، UUID، Ticket Server مرکزی و Snowflake. Ticket Server مرکز هماهنگی و احتمالاً نقطهٔ فشار/خرابی است. UUID نیاز به تخصیص Worker ندارد. Snowflake بخشی از ID را به زمان، بخشی به Node و بخشی به Sequence می‌دهد.

## گزینهٔ ساده در Django

برای خیلی از پروژه‌ها UUID4 کافی است:

```python
import uuid
from django.db import models

class PublicDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
```

`uuid.uuid4` را بدون پرانتز می‌دهیم تا برای هر رکورد دوباره اجرا شود. UUID مجوز دسترسی نیست؛ حتی اگر حدس‌زدنش دشوار باشد باید مالکیت بررسی شود. UUID4 ترتیب زمانی تضمین نمی‌کند و در مقیاس بالا اثر اندازه و الگوی Insert روی Index را باید اندازه بگیری.

## Snowflake را در Python ببین

نمونهٔ همراه، ۴۱ بیت Timestamp، ۱۰ بیت Worker و ۱۲ بیت Sequence دارد. ۱۰ بیت را می‌توان به ۵ بیت Datacenter و ۵ بیت Worker تقسیم کرد؛ این نمونه یک Worker ID ترکیبی دارد.

```python
from demo.algorithms import Snowflake

generator = Snowflake(worker_id=7)
identifier = generator.next_id()
# Layout: timestamp << 22 | worker_id << 12 | sequence
```

در یک میلی‌ثانیه برای هر Worker حداکثر ۴۰۹۶ مقدار داریم. نمونه پس از پر شدن ظرفیت خطا می‌دهد؛ پیاده‌سازی عملی می‌تواند تا Tick بعدی صبر کند و Timeout داشته باشد. ساعت که عقب برود هم خطا می‌دهد تا ID تکراری نسازد. Lock این نمونه فقط Threadهای یک Object در یک Process را هماهنگ می‌کند.

**برای Django چند Worker:** هر Process باید Worker ID متفاوت و تخصیص مدیریت‌شده داشته باشد. دو Process با Worker=7 ممکن است Collision تولید کنند. Restart در همان میلی‌ثانیه و Reuse زودهنگام Worker ID هم باید مدیریت شود. اگر این زیرساخت را نداری، استفادهٔ مستقیم از این نمونه برای Production مناسب نیست؛ UUID یا ID دیتابیس ساده‌تر است.

Snowflake ترتیب تقریبی زمانی می‌دهد، نه ترتیب قطعی همهٔ عملیات بین Nodeها. Timestamp در شناسه اطلاعات زمانی آشکار می‌کند. وقتی ID بزرگ را به JavaScript می‌دهی، بهتر است در JSON رشته باشد تا دقت Number از بین نرود.

**تمرین:** دو Generator با زمان ثابت و Worker متفاوت بساز. **پاسخ:** ID متفاوت می‌شود. اگر Worker و زمان یکسان باشند و Sequence هر دو صفر باشد، ID تکراری می‌شود. تست بسته ظرفیت، ترتیب محلی و عقب رفتن ساعت را بررسی می‌کند.


## هر گزینه کدام نیاز را پوشش می‌دهد؟

| گزینه | هماهنگی | ترتیب | نکتهٔ عملی |
|---|---|---|---|
| ID دیتابیس | یک مرجع تخصیص | افزایشی در تخصیص همان DB | ترتیب Commit نیست |
| UUID4 | هماهنگی Worker ندارد | تصادفی | ۱۲۸بیتی و معمولاً برای ID عمومی مناسب |
| Ticket Server | مرجع مرکزی | قابل کنترل | ظرفیت و Failover لازم |
| Snowflake | Worker ID مدیریت‌شده | تقریبی زمانی | ساعت و Reuse Worker مهم |

در Multi-master می‌توان Nodeهای مختلف را با Offset و Step جدا جلو برد؛ مثلاً یکی اعداد فرد و دیگری زوج. اضافه کردن Node یا تغییر تعداد آن‌ها هماهنگی تازه می‌خواهد و ترتیب زمانی جهانی هم تضمین نمی‌شود. بنابراین آن را صرفاً با تغییر AutoField در Django حل نکن.

## اجزای Snowflake را از ID جدا کن

در نمونه، Timestamp نسبت به ابتدای ۲۰۲۴ محاسبه می‌شود. زمان فعلی به میلی‌ثانیه منهای Epoch در ۴۱ بیت قرار می‌گیرد. Shift، فضای بیت‌های پایین را خالی می‌کند:

```python
from demo.algorithms import Snowflake

generator = Snowflake(worker_id=7)
value = generator.next_id()
sequence = value & ((1 << 12) - 1)
worker = (value >> 12) & ((1 << 10) - 1)
timestamp_ms = (value >> 22) + Snowflake.EPOCH
print(worker, sequence, timestamp_ms)
```

`&` با Mask بخش موردنظر را جدا می‌کند؛ `>>` بیت‌ها را به راست می‌برد. مقدارها باید قبل از ساخت ID در محدوده باشند تا به بخش دیگر سرریز نکنند. ۴۱ بیت میلی‌ثانیه حدود ۶۹٫۷ سال نسبت به Epoch ظرفیت دارد؛ عوض کردن Epoch وسط عمر یک سیستم بخشی از قرارداد ID را می‌شکند.

## اتصال به Model Django

در `lab` مدل `PublicDocument` با UUID4 آماده است. برای استفاده از Snowflake در مدل مستقل، فیلد `BigIntegerField(primary_key=True)` و Service تولید ID لازم است. Generator را برای هر رکورد با Worker ثابت دوباره نساز؛ Sequence هر بار صفر می‌شود و Collision ممکن است رخ دهد. باید یک Generator زنده با State مشخص داشته باشی و Worker ID از تنظیمات مدیریت‌شده بیاید.

قید Primary Key آخرین سد در برابر شناسهٔ تکراری است، نه جایگزین الگوریتم صحیح. اگر Collision رخ داد، Retry کور با همان Worker/Clock دوباره همان خطا را تولید می‌کند. علت باید بررسی شود: دو Process یک Worker دارند؟ ساعت عقب رفته؟ State پس از Restart حفظ نشده؟

## Restart، Clock و ظرفیت

کد آموزشی هنگام عقب رفتن ساعت خطا می‌دهد. استفاده از Monotonic به‌جای زمان دیواری مستقیماً مسئله را حل نمی‌کند، چون بعد از Restart مرجع مشترک تاریخی ندارد. نسخهٔ عملی ممکن است صبر کند، منطقی زمان را جلو ببرد یا Worker را از سرویس خارج کند؛ هر انتخاب Tradeoff دارد.

۴۰۹۶ ID در میلی‌ثانیه برای هر Worker سقف نظری Sequence است؛ Throughput واقعی Python، قفل، DB و بار سیستم محدودیت‌های دیگری دارند. Worker Lease باید جلوی دو مالک همزمان را بگیرد؛ صرف متغیر Environment با مقدار ۱ در همهٔ Containerها کافی نیست.

## تمرین و پاسخ

1. دو Document بدون تعیین ID بساز. — UUIDهای متفاوت تولید می‌شوند؛ `default=uuid.uuid4()` با پرانتز ممکن است یک مقدار ثابت را به همه بدهد.
2. Clock را ثابت نگه دار و ۴۰۹۶ ID بساز. — Sequence از ۰ تا ۴۰۹۵ می‌رود؛ درخواست بعدی در نمونه خطا دارد.
3. ID را در JSON Number بزرگ به مرورگر بده. — بالاتر از محدودهٔ Integer دقیق JavaScript ممکن است رقم تغییر کند؛ رشته امن‌تر است.
4. آیا ID ترتیب قطعی پیام‌های Chat را می‌دهد؟ — خیر؛ فصل ۱۲ Sequence داخل Room و قرارداد دریافت را جدا طراحی می‌کند.

**تست‌ها:** UUID Model، یکتایی محلی، استخراج بیت Worker، سقف Sequence و عقب رفتن ساعت بررسی می‌شوند؛ تخصیص Worker توزیع‌شده آزمایش نشده است.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
