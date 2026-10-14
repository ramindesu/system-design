# فصل ۱ — از یک سرور تا میلیون‌ها کاربر

**عنوان کتاب:** Scale From Zero To Millions Of Users · **منبع:** صفحات ۵ تا ۳۳ PDF.

این فصل مسیر رشد یک سیستم را توضیح می‌دهد. مثال ما فروشگاه کتاب است: کاربر جزئیات کتاب را می‌بیند، مدیر قیمت را تغییر می‌دهد و بعداً کارهای جانبی مثل ارسال ایمیل انجام می‌شوند. کدهای این جزوه افزودهٔ آموزشی‌اند؛ کتاب کد Django ارائه نمی‌کند.

## ۱. درخواست کاربر دقیقاً کجا می‌رود؟

```text
Browser → DNS → Load Balancer → Django → Cache / Database
                                      → Queue → Worker
Browser → CDN → static files / images
```

DNS نام دامنه را به مقصد شبکه تبدیل می‌کند. مرورگر درخواست HTTP می‌فرستد. Django مسیر را در `urls.py` پیدا می‌کند، View را اجرا می‌کند و پاسخ می‌دهد. در شروع، Django و دیتابیس می‌توانند روی یک ماشین باشند. جدا کردن آن‌ها اجازه می‌دهد منابع، خرابی و رشد هرکدام را مستقل مدیریت کنیم.

برای داده‌های فروشگاه، رابطهٔ سفارش، کاربر و پرداخت و نیاز به Transaction معمولاً دلیل خوبی برای PostgreSQL است. NoSQL انتخابی برای الگوی دسترسی و نیاز مشخص است؛ زیاد شدن کاربران به‌تنهایی دلیل کنار گذاشتن SQL نیست.

**اجرای کوچک:** در آزمایشگاه همراه، `Book` سه دادهٔ اصلی دارد: عنوان، قیمت و زمان تغییر. `GET /books/1/` قیمت را برمی‌گرداند. تغییر قیمت در Service انجام می‌شود تا View فقط HTTP، دسترسی و اعتبارسنجی ورودی را مدیریت کند.

## ۲. چه وقت سرور بیشتر اضافه کنیم؟

Vertical Scaling یعنی CPU/RAM ماشین را بیشتر کنیم. ساده است ولی سقف دارد و خرابی همان ماشین مشکل ایجاد می‌کند. Horizontal Scaling یعنی چند نمونهٔ برنامه اجرا کنیم. قبل از اضافه کردن سرور باید Session، فایل‌ها و کارهای صف در محل مشترک باشند.

مثال Nginx زیر درخواست را بین دو نمونهٔ Django تقسیم می‌کند. هرکدام باید پشت یک سرور کاربردی مثل Gunicorn اجرا شوند. این تنظیم نمونه است و TLS و تنظیمات Proxy پروژه را کامل نمی‌کند.

```nginx
upstream django_pool {
    server 127.0.0.1:8001 max_fails=3 fail_timeout=10s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=10s;
}
server {
    listen 80;
    location / {
        proxy_pass http://django_pool;
        proxy_set_header Host $host;
    }
}
```

این `max_fails` تشخیص خرابی بر اساس درخواست‌های واقعی است. داشتن Load Balancer به‌تنهایی همهٔ خطاها را برطرف نمی‌کند؛ خود آن هم باید طرح دسترس‌پذیری داشته باشد. تعداد Worker را با اندازه‌گیری Latency، CPU، حافظه و اتصال دیتابیس تعیین کن؛ بیشتر کردن Worker همیشه سرعت را بیشتر نمی‌کند.

## ۳. Replica چیست و چه مشکلی را حل می‌کند؟

فرض کن از هر ۱۰۰ درخواست، ۹۵ مورد مشاهدهٔ اطلاعات است. Primary تغییرات را ثبت می‌کند و Replica نسخه‌ای از داده را دریافت می‌کند. بعضی خواندن‌ها را می‌توان به Replica فرستاد تا بار Primary کم شود. **Primary هم می‌تواند بخواند و هم بنویسد.** Replica در این طراحی برای خواندن است.

دو کار جدا داریم:

1. PostgreSQL یا سرویس دیتابیس باید واقعاً Replication را برقرار کند.
2. Django باید مشخص کند هر Query به کدام اتصال برود.

تعریف دو اتصال در Django کار اول را انجام نمی‌دهد. دو دیتابیس مستقل با نام یکسان هم Replica نیستند.

### قدم اول: دو اتصال

نمونهٔ PostgreSQL در فایل `lab/config/postgres_settings.py` قرار دارد. خلاصهٔ آن:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "bookshop", "HOST": "primary.internal",
        "USER": "app_writer", "PASSWORD": "from-environment",
    },
    "replica": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "bookshop", "HOST": "replica.internal",
        "USER": "app_reader", "PASSWORD": "from-environment",
    },
}
```

نام `default` در Django اهمیت دارد؛ اتصال پیش‌فرض است. `replica` نام انتخابی ماست. در فایل واقعی همراه، رمز از Environment خوانده می‌شود. کاربر Replica باید در خود دیتابیس اجازهٔ نوشتن نداشته باشد؛ Router به‌تنهایی تضمین امنیتی نیست.

### قدم دوم: صریح مشخص کنیم کجا بخوانیم

```python
# Reading that tolerates some delay:
book = Book.objects.using("replica").get(pk=1)

# Reading that must observe a just-committed change:
book = Book.objects.using("default").get(pk=1)

# Writing:
book.price = "150.00"
book.save(using="default", update_fields=["price"])
```

`using` فقط اتصال را انتخاب می‌کند. داده را منتقل نمی‌کند، تأخیر را رفع نمی‌کند و Failover انجام نمی‌دهد. بعد از خواندن یک Object از Replica، نوشتن همان Object را هم صریح به Primary بفرست. در پروژهٔ همراه Router تمام نوشتن‌های معمول را به Primary می‌فرستد؛ بااین‌حال `.using("replica")` صریح می‌تواند آن را دور بزند.

### قدم سوم: انتخاب خودکار با Router

در پروژهٔ همراه، فقط دادهٔ اپ `catalog` می‌تواند از Replica خوانده شود. Auth و Session از Primary خوانده می‌شوند. این انتخاب جلوی مشکل‌هایی مثل دیده نشدن کاربر تازه‌ثبت‌شده در Login را می‌گیرد.

```python
DATABASE_ROUTERS = ["catalog.routing.CatalogRouter"]
```

منطق اصلی Router:

```python
def db_for_read(self, model, **hints):
    if model._meta.app_label != "catalog":
        return "default"
    if (not settings.REPLICA_ENABLED or _primary_reads.get()
            or connections["default"].in_atomic_block):
        return "default"
    return "replica"

def db_for_write(self, model, **hints):
    return "default"
```

`_primary_reads` یک `ContextVar` است: وضعیت موقت این جریان اجرا را نگه می‌دارد و بین درخواست‌های مستقل مثل یک Global ساده مشترک نمی‌شود. کد کامل، Context Manager و قوانین Relation/Migration در `catalog/routing.py` هستند.

```python
from catalog.routing import primary_reads

with primary_reads():
    books = list(Book.objects.filter(price__lt=200))
```

`list` را داخل Context اجرا کردیم چون QuerySet معمولاً Lazy است: ساختنش الزاماً Query را اجرا نمی‌کند. اگر بیرون Context ارزیابی شود ممکن است مسیر دیگری انتخاب شود.

### قدم چهارم: Replication Lag را تجربه کن

در Replication غیرهمزمان، Primary ممکن است قیمت ۱۵۰ را ثبت کرده باشد ولی Replica هنوز ۱۰۰ نشان بدهد:

```text
write primary: 150 → read replica immediately: 100
                  → read primary:             150
```

برای صفحهٔ فهرست عمومی، کمی تأخیر ممکن است پذیرفتنی باشد. برای پاسخ تغییر قیمت، سفارش، موجودی و مجوز دسترسی معمولاً باید سیاست دقیق‌تری داشته باشی. بعد از Write می‌توانی همان Object به‌روزشده را در پاسخ برگردانی یا دوباره از Primary بخوانی. «تا ۵ ثانیه بعد از Write فقط Primary» یک راهکار عملی تقریبی است؛ اگر Lag بیشتر شود تضمین ندارد.

### قدم پنجم: Transaction را هم به اتصال درست بفرست

```python
with transaction.atomic(using="default"):
    book = Book.objects.using("default").select_for_update().get(pk=1)
    book.price = "150.00"
    book.save(using="default", update_fields=["price", "updated_at"])
```

این Transaction روی Primary است. در PostgreSQL، قفل سطر تغییرات همزمان همان کتاب را هماهنگ می‌کند. `atomic` به‌خودی‌خود همهٔ Routerهای دلخواه را وادار به خواندن از Primary نمی‌کند؛ Router ما این سیاست را اضافه کرده است و `using` صریح هم انتخاب را روشن می‌کند. بین دو دیتابیس مستقل، یک `atomic` معمولی Transaction توزیع‌شده ایجاد نمی‌کند.

Migration در کلاستر واقعی روی Primary اجرا می‌شود؛ تغییر Schema طبق نوع Replication و عملیات زیرساخت به Replica می‌رسد. `migrate --database=replica` در آزمایشگاه فقط برای ساخت SQLite مستقل شبیه‌سازی است؛ روی Standby واقعی اجرا نکن.

**هنگام خرابی Replica:** سیاست Fallback را متناسب با بار Primary طراحی کن. اگر همهٔ درخواست‌ها ناگهان به Primary برسند، ممکن است کل سیستم از کار بیفتد. ارتقای Replica به Primary، جلوگیری از دو Primary و کنترل از دست رفتن داده، وظیفهٔ مدیریت کلاستر است؛ با یک `except` داخل Django حل نمی‌شود.

## ۴. Cache را کجا وارد کد کنیم؟

Replica تعداد Query را کم نمی‌کند؛ فقط محل اجرای آن را عوض می‌کند. Cache می‌تواند برای درخواست تکراری اصلاً Query انجام ندهد. الگوی این مثال **Cache-aside** است: برنامه اول Cache را می‌خواند و اگر نبود از دیتابیس پر می‌کند.

```python
def get_book(pk, *, fresh=False):
    if fresh:
        return serialize_book(Book.objects.using("default").get(pk=pk))
    missing = object()
    data = cache.get(book_key(pk), missing)
    if data is not missing:
        return data
    data = serialize_book(Book.objects.using("default").get(pk=pk))
    cache.set(book_key(pk), data, timeout=30)
    return data
```

چرا Cache Miss از Primary می‌خواند؟ اگر بعد از تغییر قیمت Cache را حذف کنیم ولی آن را از Replica عقب‌مانده پر کنیم، دوباره قیمت قدیمی را Cache کرده‌ایم. این نمونه عمداً برای پر کردن Cache از Primary استفاده می‌کند. Queryهای بدون Cache که تأخیر را می‌پذیرند همچنان می‌توانند Replica را بخوانند.

چرا `if data` نگذاشتیم؟ مقدار معتبر Cache ممکن است `0`، `False` یا لیست خالی باشد. Sentinel نبودن مقدار را از False بودن آن جدا می‌کند. کلید `book:v1:123` هم نوع داده، نسخهٔ قالب و شناسه را مشخص می‌کند.

بعد از تغییر داده، Cache را پس از Commit پاک می‌کنیم:

```python
transaction.on_commit(lambda: cache.delete(book_key(pk)), using="default")
```

اگر Transaction Rollback شود این Callback اجرا نمی‌شود. اما این طراحی Strong Consistency نمی‌دهد: یک درخواست قدیمی ممکن است همزمان با حذف Cache، مقدار قدیمی را دوباره Cache کند. TTL دامنهٔ خطا را محدود می‌کند، به شرط اجرای سالم حذف/انقضا. برای خواندن حساس، `fresh=True` Cache را دور می‌زند؛ برای تضمین‌های بیشتر باید Version، هماهنگی یا طراحی دقیق‌تری اضافه کنی.

آزمایشگاه از LocMem استفاده می‌کند تا بدون سرویس اضافی اجرا شود. برای چند Worker یا چند سرور، Cache مشترک لازم است. مثال تنظیم Redis پس از نصب `redis`:

```python
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": os.environ["REDIS_URL"],
}}
```

Cache پایگاه اصلی داده نیست. برای Cache فروشگاه می‌توان در خرابی Redis با Timeout کوتاه به DB برگشت، ولی اگر بار زیاد است باید محدودیت و حفاظت DB هم داشته باشی. در Rate Limiter یا Lock، خرابی Redis سیاست متفاوتی لازم دارد.

## ۵. Stateless، Session و فایل‌ها

Stateless Web Tier یعنی درخواست بعدی لازم نباشد حتماً به همان Worker برود. اطلاعات کاربر را در متغیر Python یا فایل محلی یک Worker نگه ندار. در آزمایشگاه Session در DB مشترک قرار دارد:

```python
SESSION_ENGINE = "django.contrib.sessions.backends.db"
```

وقتی چند سرور داری، تصاویر Uploadشده هم باید در Storage مشترک باشند. فایل‌های CSS/JS و تصاویر عمومی را می‌توان از CDN داد. `collectstatic` فایل‌ها را جمع می‌کند؛ خودش CDN نمی‌سازد. Storage باید فایل‌ها را به مقصد انتشار منتقل کند و `STATIC_URL` به همان مقصد اشاره کند. Version در نام فایل کمک می‌کند مرورگر پس از Deploy نسخهٔ درست را بگیرد.

## ۶. Queue و کارهای پس‌زمینه

ارسال ایمیل یا ساخت تصویر Preview را داخل مسیر اصلی درخواست طولانی نگه ندار. View دادهٔ اصلی را ثبت می‌کند؛ Worker کار جانبی را انجام می‌دهد. مثال Celery با مدل `Book` آزمایشگاه، پس از تنظیم App، Broker و Worker:

```python
from celery import shared_task
from django.db import transaction

@shared_task
def build_book_preview(book_id):
    book = Book.objects.using("default").get(pk=book_id)
    # Render a preview and save it under a deterministic storage key.
    return book.title

with transaction.atomic():
    book = Book.objects.create(title="New book", price="100.00")
    transaction.on_commit(lambda: build_book_preview.delay(book.pk))
```

`on_commit` جلوی دیدن رکوردی که هنوز Commit نشده را می‌گیرد. ولی اگر بعد از Commit و پیش از ارسال پیام، Process بمیرد کار گم می‌شود. برای کار ضروری مثل اعلان پرداخت، **Transactional Outbox** فصل ۱۰ را ببین. Queue هم فقط با Persistence، Ack، Retry و Worker درست قابل اتکاست. کارها ممکن است دوباره اجرا شوند؛ طراحی Idempotent یعنی اجرای تکراری اثر مخرب تکراری ایجاد نکند.

## ۷. Sharding را با Replica اشتباه نگیر

Replica نسخهٔ همان داده است. Shard فقط بخشی از داده را دارد. اگر کاربرهای مختلف را روی DBهای مختلف تقسیم کنیم:

```python
def shard_for_user(user_id: int) -> str:
    return f"shard_{user_id % 4}"

alias = shard_for_user(123)
# In a separate sharded project with configured aliases:
# Order.objects.using(alias).filter(user_id=123)
```

این فقط انتخاب Shard است، نه مهاجرت داده یا مدیریت کلاستر. تغییر عدد ۴ به ۵ بیشتر داده‌ها را جابه‌جا می‌کند؛ فصل ۵ علت را توضیح می‌دهد. کلید Shard را با Queryهای غالب انتخاب کن. ForeignKey واقعی بین دیتابیس‌های مستقل در Django پشتیبانی نمی‌شود؛ Join و Transaction بین Shardها طراحی جدا می‌خواهد. برای این فروشگاه کوچک، قبل از Sharding باید Queryها، Index، Cache و ظرفیت DB را اندازه بگیریم.

چند مرکز داده هم فقط «چند Django» نیست: مسیر ترافیک، Replication بین منطقه‌ها، Latency، Failover و جلوگیری از Writeهای ناسازگار باید طراحی شوند.

## ۸. اجرا و آزمایش عملی

از پوشهٔ `lab`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --database=default
python manage.py migrate --database=replica
python manage.py seed_demo
python manage.py snapshot_replica
REPLICA_ENABLED=1 python manage.py shell
```

در Shell:

```python
from catalog.models import Book
from catalog.services import update_price

print(Book.objects.get(pk=1).price)                 # 100.00, replica
update_price(1, "150.00")
print(Book.objects.get(pk=1).price)                 # 100.00, replica
print(Book.objects.using("default").get(pk=1).price) # 150.00, primary
```

Shell را ببند و دوباره `snapshot_replica` اجرا کن؛ حالا Replica هم ۱۵۰ دارد. **دو SQLite با کپی دستی صرفاً تأخیر را شبیه‌سازی می‌کنند؛ Replication واقعی نیستند.** تست‌ها رفتار مسیریابی، Cache، Rollback، قیمت نامعتبر، Permission و CSRF را بررسی می‌کنند. Row Lock واقعی PostgreSQL و Failover در این آزمایشگاه تأیید نشده‌اند.

```bash
python manage.py test
python manage.py runserver
# Open http://127.0.0.1:8000/books/1/
```

## ۹. چه چیزی را اندازه بگیریم؟

میانگین کافی نیست. `p95/p99` زمان پاسخ، درصد خطا، تعداد اتصال DB، Slow Query، Cache Hit Rate، Lag Replica و عمر قدیمی‌ترین کار صف را ببین. مثلاً اگر p95 بالا رفته ولی CPU کم است، شاید انتظار دیتابیس یا سرویس شبکه مشکل باشد. Log باید شناسهٔ درخواست و خطا داشته باشد، نه رمز و Token و بدنهٔ کامل اطلاعات شخصی.

## تمرین و پاسخ کوتاه

1. بعد از تغییر قیمت، چرا صفحهٔ عمومی مقدار قدیمی نشان می‌دهد؟ — مسیر Read را پیدا کن؛ Replica و Cache دو منبع مستقل تأخیرند. برای نتیجهٔ حساس Primary و عبور از Cache لازم است.
2. دو Worker داریم؛ چرا کاربر گاهی Logout می‌شود؟ — اگر Session محلی باشد Worker دوم آن را ندارد. Session مشترک و Secret/تنظیمات یکسان لازم است.
3. حذف Cache قبل از Commit چه مشکلی دارد؟ — ممکن است Commit شکست بخورد یا درخواست دیگر قبل از Commit دادهٔ قبلی را Cache کند. `on_commit` مشکل زمان Commit را حل می‌کند، نه همهٔ Raceها.
4. اگر QuerySet را داخل `primary_reads` بسازیم ولی بیرون آن بخوانیم چه می‌شود؟ — چون Lazy است، انتخاب اتصال می‌تواند هنگام اجرا انجام شود. آن را داخل Context ارزیابی کن یا `.using("default")` بده.
5. ۱۰ سرور Django داریم ولی DB هنوز کند است؛ قدم بعد چیست؟ — Query Plan، Index، N+1، Connectionها و Cache را بررسی کن. اضافه کردن Web Server ممکن است DB را بیشتر تحت فشار بگذارد.

## منابع تکمیلی رسمی

- [Django: multiple databases](https://docs.djangoproject.com/en/5.2/topics/db/multi-db/)
- [Django: transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
- [Django: cache](https://docs.djangoproject.com/en/5.2/topics/cache/)
- [Django: sessions](https://docs.djangoproject.com/en/5.2/topics/http/sessions/)
- [PostgreSQL: streaming replication](https://www.postgresql.org/docs/16/warm-standby.html)
- [Django: static deployment](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/)
- [Celery: Django integration](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Nginx: upstream](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)
