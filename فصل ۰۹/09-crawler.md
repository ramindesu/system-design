# فصل ۹ — Crawler و مدیریت کارهای زیاد

**عنوان کتاب:** Design A Web Crawler · صفحات ۱۳۲ تا ۱۵۰ PDF.

## اجزای اصلی

Crawler یک Loop سادهٔ «صفحه را بگیر، لینک‌ها را دنبال کن» نیست. **URL Frontier** صف کارهای آینده است؛ Downloader صفحه را دریافت می‌کند؛ Parser محتوا و لینک را استخراج می‌کند؛ Deduplication جلوی کار تکراری را می‌گیرد؛ Scheduler سرعت هر Host را محدود می‌کند. Priority و Politeness باید همزمان در Frontier در نظر گرفته شوند.

دو نوع تکرار داریم: URL تکراری و محتوای یکسان با URL مختلف. URL Normalization را بااحتیاط انجام بده: Fragment معمولاً به Server نمی‌رود؛ اما حذف Query String یا عوض کردن بزرگی/کوچکی Path می‌تواند صفحهٔ دیگری را تبدیل کند. Hash محتوا هم برای تشخیص نسخهٔ تکراری کمک می‌کند.

## بخش قابل پیاده‌سازی با Django: Claim کردن کار

برای یک Crawler کوچک، DB می‌تواند صف اولیه باشد. نمونه برای PostgreSQL است. مدل‌های زیر را در اپ مستقل قرار بده:

```python
from datetime import timedelta
from django.db import models, transaction
from django.utils import timezone

class CrawlJob(models.Model):
    url = models.URLField(max_length=2000, unique=True)
    state = models.CharField(max_length=16, default="pending")
    priority = models.IntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    class Meta:
        indexes = [models.Index(fields=["state", "-priority", "id"])]

def claim_job():
    with transaction.atomic(using="default"):
        job = (CrawlJob.objects.using("default")
               .select_for_update(skip_locked=True)
               .filter(state="pending").order_by("-priority", "id").first())
        if job is None:
            return None
        job.state = "running"
        job.lease_until = timezone.now() + timedelta(minutes=2)
        job.save(using="default", update_fields=["state", "lease_until"])
        return job.pk, job.url
```

Worker کار را Claim می‌کند و Transaction را می‌بندد؛ دریافت شبکه را **بیرون Transaction** انجام می‌دهد. `skip_locked` اجازه می‌دهد Worker بعدی کار قفل‌شده را رد کند. Reaper باید کارهای Running با Lease منقضی را دوباره Pending کند. برای جلوگیری از تکمیل کار توسط Worker قدیمی پس از انقضای Lease، در نسخهٔ کامل Claim Token هم اضافه کن و Update نهایی را با همان Token مشروط کن.

این Claim فقط جلوگیری از انتخاب همزمان یک Job را نشان می‌دهد؛ Politeness هر Host هنوز پیاده نشده. اگر دو Job از یک Host باشند، دو Worker می‌توانند همزمان Fetch کنند. برای هر Host صف یا Rate Limit مستقل و `next_allowed_at` اتمیک لازم است.

## Downloader چه قواعدی دارد؟

برای تمرین از دامنه‌های مجاز و مشخص استفاده کن. قبل از Crawl، `robots.txt` و بودجهٔ هر Host را بررسی کن؛ `urllib.robotparser.RobotFileParser` می‌تواند قواعد Robots را Parse کند. Timeout، سقف اندازهٔ Body، محدودیت Redirect و Retry با Backoff قرار بده. Robots کنترل دسترسی امنیتی نیست. URLهای ورودی نباید به شبکهٔ داخلی سرویس دسترسی بدهند؛ محدودیت مقصد باید Redirect و Resolve مجدد را هم پوشش دهد.

Storage خام را از Metadata کار جدا کن. برای Recrawl، زمان آخرین Fetch، Hash محتوا و خطا را ثبت کن. Bloom Filter می‌تواند کمک کند، اما False Positive دارد؛ اگر کشف همهٔ صفحات مهم است، تنها مرجع حذف کار نباشد. حجم صف و تعداد URL تکراری و خطاهای هر Host معیارهای مفیدند.

**تمرین:** Worker بعد از Download و قبل از ثبت موفقیت بمیرد چه می‌شود؟ **پاسخ:** Lease منقضی می‌شود و Job تکرار می‌شود؛ ذخیرهٔ محتوا باید Idempotent باشد. این همان تفاوت «یک بار انتخاب» و «یک بار اثرگذاری» است.

[منبع رسمی: RobotFileParser در Python](https://docs.python.org/3/library/urllib.robotparser.html)


## Claim، Lease و Fencing را جدا بفهم

Claim یعنی یک Worker کار را انتخاب می‌کند. Lease یعنی این حق تا زمان مشخصی اعتبار دارد. Fencing یعنی Worker قدیمی بعد از واگذاری دوباره نتواند نتیجهٔ کار جدید را خراب کند. در مدل آزمایشگاه، `claim_token` یک UUID تازه در هر Claim است؛ تکمیل کار باید همان Token و Lease معتبر را داشته باشد.

```python
from demo.services import enqueue, claim_job, complete_job

enqueue("https://example.com/a#section")
job = claim_job()
if job:
    # Fetch/parse outside the DB transaction; the teaching lab does no network fetch.
    done = complete_job(job["id"], job["token"])
```

`enqueue` در این نسخه فقط دامنهٔ `example.com` را قبول می‌کند و Fragment را حذف می‌کند. Query String را نگه می‌دارد. این Allowlist برای تمرین است؛ Downloader عمومی ساخته نشده است. Canonicalization بیش از حد می‌تواند صفحه‌های واقعاً متفاوت را یکی کند.

## Crash را بدون تماس با اینترنت شبیه‌سازی کن

یک Job را Claim کن، Lease آن را در DB به گذشته ببر و `requeue_expired` را اجرا کن. Claim بعدی Token جدید می‌دهد. اگر Worker قبلی حالا `complete_job` را با Token قدیمی صدا بزند، صفر سطر تغییر می‌کند. Worker تازه تنها دارندهٔ Token معتبر است. اگر Upload محتوا خارج DB اثر جانبی دارد، همان Token یا کلید نسخه‌دار باید در انتشار محتوا هم اعمال شود؛ محافظت سطر Metadata همهٔ اثرهای خارجی را کنترل نمی‌کند.

`skip_locked` در PostgreSQL به Worker اجازه می‌دهد به کار بعدی برود. در SQLite این قفل واقعی وجود ندارد؛ آزمایشگاه فقط ترتیب و State Machine را تست می‌کند. Lease را متناسب با مدت کار انتخاب کن و برای کار طولانی تمدید اتمیک با همان Token داشته باش. اگر Worker بدون تمدید کند شود، دوباره اجرا شدن طبیعی است.

## Frontier خوب فقط یک Priority Queue نیست

Priority مشخص می‌کند کدام صفحه ارزشمندتر است؛ Politeness مشخص می‌کند چه وقت مجازیم Host را دوباره بخوانیم. یک Queue برای هر Host یا Slot محدود هر Host جلوی Fetch همزمان زیاد را می‌گیرد. Priority بالای یک دامنه نباید بودجهٔ آن را دور بزند. برای Hostها با هزینهٔ متفاوت، زمان‌بندی Fairness هم مهم می‌شود.

Parsing را از Download جدا کن تا خطای Parser همهٔ Workerهای شبکه را درگیر نکند. HTML خام می‌تواند در Storage باشد و Metadata URL، Status، زمان Fetch و Hash در DB. Hash یک محتوا جای تشخیص Canonical URL و قواعد Recrawl را نمی‌گیرد. برای صفحهٔ Dynamic ممکن است Browser Rendering لازم شود که هزینهٔ CPU/RAM بسیار بیشتری از Fetch متن دارد؛ Scope این فصل تمرین HTML ساده است.

## Retry و Recrawl

Timeout یا خطای موقت ممکن است با Backoff تکرار شود. 404 معمولاً همان لحظه Retry مداوم نمی‌خواهد؛ Recrawl بعدی سیاست جداست. ETag و Last-Modified می‌توانند به Download مشروط کمک کنند، ولی رفتار Serverها یکسان نیست. Cache DNS نیز TTL دارد؛ برای ارتباط امن و درست مقصد نهایی باید کنترل شود.

برای پرهیز از Spider Trap، سقف Depth، تعداد URL هر Host، Query Variant و اندازهٔ پاسخ لازم است. معیارهای useful شامل عمر قدیمی‌ترین Job، درصد تکرار، Bytes دانلود و نرخ خطا/Timeout هر Host هستند. فقط تعداد صفحات در ثانیه کیفیت Crawl را نشان نمی‌دهد.

## تمرین و پاسخ

1. Worker قدیمی پس از Reclaim نتیجه ثبت کند. — Token قدیمی رد می‌شود.
2. دو URL با Fragment متفاوت وارد کن. — در قرارداد مثال یک Job ایجاد می‌شود؛ Query متفاوت همچنان Job جداست.
3. Queue خالی باشد چه برمی‌گردد؟ — `None`؛ Worker باید با انتظار/Backoff محدود دوباره امتحان کند.
4. Job کامل را دوباره Complete کن. — State دیگر Running نیست؛ تغییری نمی‌کند.

**مرز اجرا:** Queue، Lease و Token محلی واقعی‌اند؛ دانلود وب، Robots Scheduler و محدودیت Host در این بسته اجرا نمی‌شوند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
