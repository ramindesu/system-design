# فصل ۴ — محدود کردن تعداد درخواست‌ها

**عنوان کتاب:** Design A Rate Limiter · صفحات ۵۱ تا ۷۰ PDF.

## چه زمانی لازم است؟

برای جلوگیری از فشار بیش از حد، مصرف بی‌رویهٔ منابع و بعضی سوءاستفاده‌ها، تعداد درخواست را برای User، API Key یا IP محدود می‌کنیم. محدودیت Client قابل دور زدن است؛ تصمیم معتبر باید در سمت Server یا Gateway باشد. «۱۰ بار در دقیقه» باید مشخص کند برای کدام عملیات و کدام هویت است.

| روش | رفتار | هزینه یا محدودیت |
|---|---|---|
| Token Bucket | Burst تا ظرفیت؛ سپس Refill با نرخ ثابت | اندازهٔ Bucket و نرخ باید انتخاب شوند |
| Leaky Bucket | خروجی یکنواخت از صف محدود | انتظار و Drop هنگام پر شدن صف |
| Fixed Window | شمارش در بازه‌های ثابت | Burst دو طرف مرز بازه |
| Sliding Log | نگهداری Timestampهای پنجرهٔ اخیر | حافظه متناسب با درخواست‌ها |
| Sliding Counter | تقریب وزنی دو پنجره | دقت کمتر ولی حافظه کم |

## اول الگوریتم را بفهم

`TokenBucket` در `examples/algorithms.py` با Lock و ساعت Monotonic کار می‌کند:

```python
bucket = TokenBucket(capacity=10, rate=2)
allowed, retry_after = bucket.take()
```

یعنی ابتدا ۱۰ درخواست سریع مجاز است و بعد در هر ثانیه ۲ Token اضافه می‌شود. این Object فقط داخل یک Process معتبر است. اگر هر Worker یک Bucket داشته باشد، سهمیهٔ کل بیشتر از مقدار مورد انتظار می‌شود.

## Django چند Worker: شمارندهٔ مشترک و اتمیک

نمونهٔ زیر **Fixed Window** با Redis است، نه Token Bucket. کل عملیات افزایش و TTL در Lua اتمیک انجام می‌شود. با `GET` و سپس `SET` جدا، دو درخواست همزمان ممکن است سهمیه را غلط حساب کنند.

```python
import os
import redis
from django.http import JsonResponse

r = redis.Redis.from_url(os.environ["REDIS_URL"],
                         socket_connect_timeout=0.2, socket_timeout=0.2)
check = r.register_script("""
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {n, redis.call('TTL', KEYS[1])}
""")

def limited_search(request):
    # Mount after authentication; this example limits authenticated users.
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login required"}, status=401)
    n, ttl = check(keys=[f"limit:search:{request.user.pk}"], args=[60])
    if n > 30:
        response = JsonResponse({"error": "too many requests"}, status=429)
        response["Retry-After"] = str(max(1, ttl))
        return response
    return JsonResponse({"accepted": True})
```

پنجره از اولین درخواست شروع می‌شود. نزدیک پایان آن و شروع پنجرهٔ بعد، Burst بزرگ‌تری از ۳۰ در هر ۶۰ ثانیهٔ دلخواه ممکن است مجاز شود. اگر شرط دقیق پنجرهٔ لغزان داری، این الگوریتم مناسب نیست. درخواست‌های ردشده در این مثال شمارنده را زیاد می‌کنند ولی TTL را تمدید نمی‌کنند.

**تکمیل برای پروژه:** `redis` نصب کن، Redis مشترک تنظیم کن، خطای اتصال را با سیاست مشخص مدیریت کن و کلید را براساس User/Endpoint انتخاب کن. IP پشت Proxy را فقط از Proxy مورد اعتماد بپذیر. محدودیت محلی روی هر Region الزاماً محدودیت دقیق جهانی نیست.

**خرابی و معیار:** برای عملیات گران ممکن است Fail-closed بخواهی؛ برای صفحهٔ عمومی شاید Fail-open با محافظت جایگزین. نرخ ۴۲۹، Latency Redis و تعداد کاربران معتبرِ محدودشده را اندازه بگیر. این مثال Redis در این بسته اجرا نشده؛ الگوریتم محلی تست شده است.

**تمرین:** با سه Worker و Bucket محلی ۱۰تایی، Burst کل ممکن است چقدر شود؟ **پاسخ:** حدود ۳۰؛ برای سهمیهٔ مشترک باید هماهنگی مشترک داشته باشی.

[منبع رسمی: اجرای اتمیک Lua در Redis](https://redis.io/docs/latest/develop/programmability/eval-intro/)


## Token Bucket را روی خط زمان اجرا کن

Bucket با ظرفیت ۳ و نرخ یک Token در ثانیه در زمان صفر، سه درخواست را می‌پذیرد. درخواست چهارم همان لحظه رد می‌شود. بعد از نیم‌ثانیه فقط نیم Token داریم و هنوز یک درخواست کامل مجاز نیست. بعد از یک ثانیه، یک Token جمع شده است. اگر ده ثانیه بگذرد، تعداد از ظرفیت ۳ بالاتر نمی‌رود؛ Refill به معنی مجوز Burst نامحدود نیست.

نمونهٔ Python به‌جای Thread جدا برای Refill، هنگام درخواست مقدار اضافه‌شده را حساب می‌کند: `min(capacity, tokens + elapsed * rate)`. از Monotonic برای مدت سپری‌شده استفاده می‌کنیم تا تغییر ساعت سیستم محاسبهٔ محلی را خراب نکند. Lock دور کل Read/Calculate/Consume است؛ Lock فقط دور `tokens -= 1` شکاف Race را برطرف نمی‌کند.

## آزمایشگاه Django و HTTP 429

در `lab/demo/services.py` تابعی داریم که تصمیم Bucket را به پاسخ Django تبدیل می‌کند:

```python
from demo.algorithms import TokenBucket
from demo.services import rate_limit_response

bucket = TokenBucket(capacity=3, rate=1)
response = rate_limit_response(bucket)
# None means: continue to the normal view.
# A JsonResponse with status 429 means: stop this request.
```

تست با Clock کنترل‌شده می‌گذارد بدون Sleep ببینی سه درخواست پذیرفته می‌شوند، چهارمی 429 دارد و بعد از گذشت زمان درخواست دوباره مجاز می‌شود. این یک ابزار آموزشی تک‌Process است؛ برای اجرای وب واقعی باید Bucket را براساس User/Endpoint نگه داری و Registry را هم با انقضا و سقف حافظه مدیریت کنی. صرف ساختن Bucket داخل هر View تمام درخواست‌ها را مجاز می‌کند، چون با هر بار اجرا Bucket تازه پر می‌شود.

## تبدیل به معماری چند سرور

برای محدودیت دقیق مشترک، Token، آخرین زمان و مصرف باید در Store مشترک با عملیات اتمیک نگه داشته شوند. نمونهٔ Redis بالا Fixed Window را نشان می‌دهد. برای Token Bucket توزیع‌شده، همان محاسبهٔ Refill و Consume را در یک Lua Script ببر؛ ساعت یک مرجع مشترک، زمان انقضا، تغییر Rule و رفتار Clock باید مشخص باشند.

Rule را Versionدار کن: نرخ جدید ممکن است با State قدیمی نامتناسب باشد. Client نباید با عوض کردن Endpoint Alias همان محدودیت را دور بزند. محدودیت per-user برای فرد Loginشده و per-IP برای مسیر عمومی دو سیاست متفاوت‌اند؛ IP مشترک می‌تواند چند کاربر معتبر را محدود کند و تعداد IPهای زیاد هم آن را کم‌اثر می‌کند.

در Sliding Counter اگر در بازهٔ قبل ۵ درخواست و در بازهٔ فعلی ۳ درخواست بوده و ۳۰٪ از بازهٔ فعلی گذشته، تخمین برابر `3 + 5 × 0.7 = 6.5` است. در چاپ کتاب کنار این ضریب علامت درصد اشتباه دیده می‌شود؛ ۰٫۷ ضریب است، نه ۰٫۷٪. گرد کردن و مرز تصمیم را صریح انتخاب کن.

## خرابی را به قرارداد تبدیل کن

اگر Redis برای جست‌وجوی عمومی قطع شود، شاید Fail-open با سقف محلی مناسب باشد. اگر عملیات هزینهٔ Provider بالایی دارد، شاید Fail-closed با 503 مناسب‌تر باشد. 429 یعنی سهمیه پر شده؛ 503 یعنی زیرساخت محدودکننده در دسترس نیست. این دو را برای Client قاطی نکن. Retry-After برآورد انتظار است و نباید باعث Retry همزمان همهٔ Clientها شود؛ Client به Backoff/Jitter هم نیاز دارد.

## تمرین و پاسخ

1. Bucket را داخل View بساز و چهار درخواست بفرست. — هرکدام State تازه دارد؛ این Rate Limit نیست.
2. ظرفیت را ۱۰ و نرخ را ۲ کن؛ چه چیزی عوض می‌شود؟ — Burst اولیه ۱۰ است، نرخ پایدار ۲ در ثانیه؛ این دو مستقل‌اند.
3. همزمانی باعث Read مقدار ۱ توسط دو درخواست شود چه رخ می‌دهد؟ — بدون هماهنگی ممکن است هر دو همان Token را مصرف کنند؛ عملیات کل تصمیم باید اتمیک باشد.
4. آیا Rate Limit جلوی همهٔ DoSها را می‌گیرد؟ — خیر؛ درخواست پیش از رسیدن به Django هم منابع مصرف می‌کند. حفاظت شبکه/Gateway و سقف Body/Timeout موضوع جداست.

**مرز تست:** رفتار Token Bucket و 429 محلی بررسی می‌شود؛ Script Redis و سهمیهٔ بین Regionها در این تست اجرا نمی‌شوند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 2 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
