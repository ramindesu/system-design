# فصل ۱۳ — Autocomplete سریع و فارسی

**عنوان کتاب:** Design A Search Autocomplete System · صفحات ۲۰۰ تا ۲۱۹ PDF.

## دو مسیر مستقل

مسیر Online با هر Prefix باید چند پیشنهاد را سریع برگرداند. مسیر Offline از رویدادهای جست‌وجو فراوانی و کیفیت پیشنهادها را محاسبه می‌کند. لازم نیست برای هر Keypress کل Ranking را دوباره بسازیم.

فصل ابتدا جدول Query/Frequency و سپس Trie را بررسی می‌کند. در Trie مسیر کاراکترهای Prefix مشترک است. اگر برای هر Node از قبل Top-k ذخیره شود، هنگام خواندن نیاز به پیمایش همهٔ فرزندان نداریم. پیمایش Prefix به طول آن وابسته است؛ O(1) در بیان فصل بر فرض سقف ثابت طول Prefix تکیه دارد.

## شروع عملی با Django و Cache

مدل و تابع زیر در اپ مستقل قرار می‌گیرند. `term` شکل نمایش و `normalized` شکل جست‌وجوست. هنگام Import/Update، Normalize را با همین تابع انجام بده.

```python
import hashlib
import unicodedata
from django.db import models
from django.core.cache import cache

def normalize(text):
    return unicodedata.normalize("NFC", text).replace("ي", "ی").replace("ك", "ک").strip().casefold()

class Suggestion(models.Model):
    term = models.CharField(max_length=200)
    normalized = models.CharField(max_length=200, unique=True)
    score = models.PositiveBigIntegerField(default=0)

def suggest(raw_prefix):
    prefix = normalize(raw_prefix)
    if not 2 <= len(prefix) <= 40:
        return []
    digest = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
    key = f"suggest:v1:{digest}"
    missing = object()
    result = cache.get(key, missing)
    if result is not missing:
        return result
    result = list(Suggestion.objects.using("default")
        .filter(normalized__startswith=prefix)
        .order_by("-score", "normalized").values_list("term", flat=True)[:5])
    cache.set(key, result, timeout=60)
    return result
```

کلید Hash طول ورودی را کنترل می‌کند و متن را در اسم کلید نمی‌گذارد؛ ابزار جمع‌آوری داده همچنان باید سیاست حریم خصوصی داشته باشد. این نسخه SQL+Cache است و Trie پیاده نمی‌کند. کارایی Prefix Query به Index، Collation و Query Plan وابسته است؛ Unique بودن فیلد به‌تنهایی تضمین سرعت این Query نیست.

برای شروع، Query Plan را ببین. اگر داده و QPS بزرگ شدند، Job دوره‌ای Top-k هر Prefix را بسازد و به شکل Snapshot نسخه‌دار منتشر کند. همهٔ Workerها باید نسخهٔ فعال را هماهنگ عوض کنند؛ عوض کردن Prefix Key به `v2` بدون ساخت دادهٔ آن نتیجهٔ خالی می‌دهد.

## جزئیات فارسی و کیفیت

نیم‌فاصله، اعراب، شکل‌های مختلف ی/ک و زبان انتخاب‌شده روی Normalization اثر دارند. همهٔ این‌ها را کورکورانه حذف نکن؛ شکل نمایشی کاربر را نگه دار. محبوبیت به‌تنهایی کیفیت نیست؛ Queryهای Spam، اطلاعات شخصی و موارد نامناسب نباید خودکار به پیشنهاد عمومی تبدیل شوند.

Debounce در مرورگر تعداد درخواست را کم می‌کند ولی Server همچنان Rate Limit و سقف Prefix لازم دارد. زبان، Tenant یا پیشنهاد شخصی باید در Cache Key وارد شود تا دادهٔ کاربر/زبان دیگر برنگردد. دادهٔ Ranking می‌تواند کمی دیرتر به‌روز شود؛ حذف فوری یک پیشنهاد ممنوع‌شده نباید منتظر Snapshot هفتهٔ بعد بماند.

**تمرین:** کاربر `ك` عربی می‌زند ولی داده با `ک` فارسی است؛ چرا نتیجه نیست؟ **پاسخ:** ورودی و داده باید قرارداد Normalize یکسان داشته باشند. نمونه هر دو را به شکل فارسی تبدیل می‌کند.


## SQL ساده را اول واقعاً اجرا کن

آزمایشگاه `Suggestion`، Normalize و Cache دارد. در Shell دادهٔ مرتب‌سازی را آماده کن:

```python
from demo.models import Suggestion
from demo.services import normalize, suggest

Suggestion.objects.create(term="کتاب جنگو", normalized=normalize("کتاب جنگو"), score=100)
Suggestion.objects.create(term="کتاب پایتون", normalized=normalize("کتاب پایتون"), score=80)
print(suggest("كت"))  # Arabic kaf is normalized to Persian kaf.
```

بعد از تغییر Ranking، نتیجهٔ Cache تا TTL ممکن است قدیمی باشد. این نسخه Eventual است؛ اگر حذف فوری لازم است، Version یا Filter مستقل لازم داری. Cache Missها را بدون محدودیت Prefix به Queryهای گران تبدیل نکن. برای Query فارسی، Collation، نیم‌فاصله و الفبای داده باید قرارداد مشترک داشته باشند.

## Trie با Top-k پیش‌محاسبه‌شده

در `demo/trie.py` پیاده‌سازی کوچک Trie آماده است. داده‌ها یک بار براساس Score نزولی و متن Normalized مرتب می‌شوند. در مسیر هر Term، Nodeهای Prefix ساخته و فقط نخستین k Term برتر ثبت می‌شوند. در Query، به Node Prefix می‌رویم و List آماده را می‌گیریم:

```python
from demo.trie import TopKTrie

snapshot = TopKTrie([("کتاب جنگو", 100), ("کتاب پایتون", 80)], k=5)
print(snapshot.suggest("كت"))
```

این ساختار برای Snapshot تغییرناپذیر خوب است. با هر Keypress Counter همهٔ Nodeها را تغییر نمی‌دهیم. هزینهٔ ساخت و حافظه را باید حساب کرد؛ ذخیرهٔ Top-k در Prefixهای زیاد می‌تواند بزرگ شود. خود پیاده‌سازی Python هم Overhead Object و Dictionary دارد؛ اندازهٔ متن‌ها به‌تنهایی اندازهٔ RAM نیست.

## از Trie محلی تا سرویس چند Worker

Trie محلی Process بعد از Restart باید از Snapshot بارگذاری شود. اگر همهٔ Workerها خودشان همزمان DB را Scan کنند، Deploy می‌تواند به DB فشار بدهد. Snapshot را مستقل بساز، با Checksum/Version منتشر کن، قبل از فعال‌سازی بارگذاری و بررسی کن و سپس Pointer نسخهٔ فعال را عوض کن. نسخهٔ قبلی مدتی برای Rollback بماند.

اگر Trie بزرگ شد، Partition براساس Prefix و بار واقعی لازم است. تقسیم صرف بر حرف اول می‌تواند نابرابر باشد: حرف‌های پرکاربرد Node داغ می‌سازند. نقشهٔ Shard می‌تواند Prefixهای پرترافیک را ریزتر کند؛ تمام Query Workerها باید همین نسخهٔ نقشه را ببینند.

## Pipeline جمع‌آوری داده

Search Event با زمان و زبان وارد Log می‌شود؛ Aggregator پنجرهٔ زمانی را جمع می‌کند؛ Worker امتیاز/فیلتر را می‌سازد؛ Snapshot منتشر می‌شود. Raw Queryها ممکن است اطلاعات خصوصی داشته باشند. عمومی کردن هر عبارت تایپ‌شده، رفتار مناسب Autocomplete نیست. معیار کیفیت فقط تعداد کلیک نیست؛ نرخ انتخاب، پیشنهاد بی‌ربط، Query ناموفق و تازگی را هم ببین.

برای Term تازه/Trending، Snapshot دیرهنگام ممکن است نامناسب باشد. می‌توان یک لایهٔ تازهٔ کوچک روی Snapshot پایه Merge کرد؛ همان قرارداد Ranking و Deduplication لازم است. لغو فوری پیشنهاد ممنوع باید مسیر مستقل قابل کنترل داشته باشد، چون Cache/Snapshot قدیمی هنوز آن را نگه می‌دارد.

## تمرین و پاسخ

1. «كتاب» و «کتاب» در دادهٔ مختلف ثبت شوند. — قبل از ثبت Normalize کن و دربارهٔ Deduplication معنایی تصمیم بگیر؛ قید یکتا روی Normalized جلوی دو نسخهٔ یکسان را می‌گیرد.
2. نتیجهٔ خالی دوباره درخواست شود. — باید Cache Hit باشد؛ `if result` نتیجهٔ خالی معتبر را Miss حساب می‌کند.
3. Prefix خیلی کوتاه بده. — نمونه کمتر از دو کاراکتر را رد می‌کند تا Query گسترده نسازد.
4. Score یک Term بعد از Snapshot عوض شود. — Trie قبلی خودبه‌خود به‌روز نمی‌شود؛ Snapshot جدید بساز.

**تست‌ها:** Query SQL، شکل‌های ی/ک، ترتیب Score، Cache نتیجهٔ خالی و Snapshot Trie بررسی می‌شوند؛ کیفیت مدل Ranking و Sharding توزیع‌شده ارزیابی نشده‌اند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
