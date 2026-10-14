# فصل ۶ — طراحی Key-Value Store و انتخاب Consistency

**عنوان کتاب:** Design A Key-Value Store · صفحات ۸۷ تا ۱۰۹ PDF.

## از Dictionary تا سیستم توزیع‌شده

یک `dict` در Python برای فهم `get(key)` و `put(key, value)` خوب است، ولی با پایان Process از بین می‌رود و بین Workerها مشترک نیست. Store واقعی باید دربارهٔ حجم، Persistence، Replication، Latency و رفتار هنگام قطع شبکه تصمیم بگیرد.

فصل، Partitioning با حلقه، Replication روی چند Node، Quorum، Version و Vector Clock، Gossip، Hinted Handoff، Merkle Tree و مسیر خواندن/نوشتن با Log و SSTable را کنار هم قرار می‌دهد. این‌ها اجزای ساخت موتور ذخیره‌سازی‌اند؛ با یک Model ساده همهٔ آن‌ها ساخته نمی‌شوند.

## CAP دقیقاً چه می‌گوید؟

وقتی Partition شبکه رخ دهد، نمی‌توان هم پاسخ موفق به تمام درخواست‌ها داد و هم تضمین کرد همهٔ خواندن‌ها آخرین نوشتن را می‌بینند. باید رفتار آن وضعیت را انتخاب کنیم. CAP یک قانون «همیشه از سه مورد فقط دو مورد» برای همهٔ تصمیم‌های روزمره نیست؛ Latency و Durability سؤال‌های دیگری‌اند.

در Quorum، `N` تعداد Replica، `W` تعداد تأیید لازم برای Write و `R` تعداد Replica خوانده‌شده است. `R + W > N` باعث هم‌پوشانی مجموعه‌ها می‌شود، ولی به‌تنهایی هر پیاده‌سازی را Linearizable نمی‌کند؛ عضویت ثابت، نسخه‌بندی، شکست‌های همزمان و روش خواندن/نوشتن اهمیت دارند. این Quorum مربوط به طراحی این فصل است؛ Router معمول Django آن را پیاده نمی‌کند.

## تمرین عملی Django: جلوگیری از Lost Update

به‌جای ساخت Cassandra، یک KV کوچک روی دیتابیس رابطه‌ای می‌سازیم. این مثال **تک‌دیتابیس** است و مفهوم Version را نشان می‌دهد. مدل زیر را در یک اپ مستقل قرار بده، Migration بساز و اجرا کن:

```python
from django.db import models
from django.db.models import F

class Entry(models.Model):
    key = models.CharField(max_length=200, primary_key=True)
    value = models.JSONField()
    version = models.PositiveBigIntegerField(default=1)

def compare_and_set(key, expected_version, new_value):
    changed = Entry.objects.using("default").filter(
        key=key, version=expected_version,
    ).update(value=new_value, version=F("version") + 1)
    return changed == 1
```

دو Client مقدار با Version برابر ۳ را خوانده‌اند. Client اول Update می‌کند و Version به ۴ می‌رود. Client دوم با شرط Version=3 صفر سطر تغییر می‌دهد؛ باید Conflict برگرداند، دوباره بخواند یا Merge کند. چون شرط و Update یک دستور SQL هستند، شکاف جداگانهٔ Read سپس Write نداریم. `save()` عادی بدون این شرط می‌تواند تغییر قبلی را بازنویسی کند.

Version عددی این نمونه **Vector Clock نیست**. Vector Clock شمارندهٔ چند نویسنده را نگه می‌دارد تا تغییرهای مستقل و رابطهٔ علت‌ومعلولی مشخص شود. Conflict واقعی باید سیاست محصول داشته باشد؛ برای موجودی، «آخرین Write برنده است» ممکن است غلط باشد.

## موتور ذخیره‌سازی چه می‌کند؟

Write ابتدا در Log پایدار و ساختار حافظه ثبت می‌شود، بعد دادهٔ مرتب روی دیسک نوشته می‌شود. Read از حافظه یا فایل‌ها می‌آید؛ Bloom Filter می‌تواند بگوید کلید قطعاً در یک فایل نیست، ولی پاسخ مثبت آن الزاماً وجود کلید را ثابت نمی‌کند. Merkle Tree برای پیدا کردن بخش‌های متفاوت بین Replicaها مفید است؛ Backup جای آن را نمی‌گیرد.

**تمرین:** دو درخواست همزمان با `expected_version=1` بفرست. **پاسخ:** فقط یکی باید `True` بگیرد؛ دیگری Conflict دارد. این را روی دیتابیس واقعی با دو اتصال مستقل تست کن؛ موفقیت SQLite آزمایشگاه، Quorum یا Partition شبکه را اثبات نمی‌کند.

[منبع رسمی: QuerySet update](https://docs.djangoproject.com/en/5.2/ref/models/querysets/)


## از دست رفتن Update را با عدد ببین

دو Client مقدار `{"likes": 10}` با Version=1 را می‌خوانند. هر دو محلی یک واحد اضافه می‌کنند و ۱۱ می‌نویسند. نتیجه باید ۱۲ باشد ولی با Read/Write ساده ۱۱ می‌شود. در Compare-and-set، اولی شرط Version=1 را می‌برد؛ دومی دیگر حق نوشتن همان Snapshot را ندارد. باید Version=2 را بخواند و تصمیم را تکرار کند. این روش **Optimistic Concurrency** است.

در آزمایشگاه:

```python
from demo.models import Entry
from demo.services import compare_and_set

Entry.objects.create(key="book:1", value={"likes": 10})
print(compare_and_set("book:1", 1, {"likes": 11}))  # True
print(compare_and_set("book:1", 1, {"likes": 11}))  # False
current = Entry.objects.get(key="book:1")
print(current.version, current.value)  # 2, {'likes': 11}
```

برای Counter صرف، `F("count") + 1` روی یک فیلد عددی می‌تواند هر افزایش را اتمیک انجام دهد؛ برای JSON پیچیده باید منطق Merge/Version روشن باشد. Retry بی‌نهایت روی کلید داغ باعث فشار می‌شود؛ تعداد تلاش و Backoff را محدود کن.

## Quorum با یک مثال روشن

سه Replica به نام A، B، C داریم و `W=2` است. Write پس از تأیید A و B موفق تلقی می‌شود. اگر `R=2` باشد، Read هر جفت Replica حداقل با یک عضو این Write مشترک است. اما Read باید نسخهٔ جدید را تشخیص دهد؛ جمع‌آوری دو پاسخ بدون سیاست انتخاب نسخه، کافی نیست. در Sloppy Quorum ممکن است Node جایگزین خارج از مجموعهٔ اصلی پاسخ دهد و فرض سادهٔ هم‌پوشانی تغییر کند.

برای Django متصل به PostgreSQL معمولی، این منطق در لایهٔ Cluster/Engine است؛ اجرای `.using("replica")` فقط یک Node را می‌خواند. ساختن Quorum با سه Query و انتخاب جدیدترین `updated_at` به‌تنهایی تضمین صحیح نیست، چون ساعت‌ها و Writeهای همزمان می‌توانند اختلاف داشته باشند.

## Vector Clock یعنی تشخیص رابطه، نه انتخاب برنده

Versionهای `{"A": 2, "B": 1}` و `{"A": 3, "B": 1}` قابل مقایسه‌اند؛ دومی ادامهٔ اولی است. ولی `{"A": 3, "B": 1}` و `{"A": 2, "B": 2}` همزمان/مستقل‌اند: یکی شمارندهٔ A بیشتری دارد و دیگری B بیشتری. در `demo/services.py` تابع `clock_relation` این چهار حالت را برمی‌گرداند: Equal، Before، After و Concurrent.

این تابع مقدار را Merge نمی‌کند. در سبد خرید شاید اجتماع بعضی تغییرات قابل انجام باشد؛ در پرداخت همین سیاست ممکن است غلط باشد. Vector Clock با افزایش تعداد نویسندگان هزینهٔ Metadata دارد و برای حذف/فشرده‌سازی تاریخچه به سیاست نیاز دارد.

## مسیر پایدار نوشتن و بازیابی

Memtable دادهٔ مرتب در حافظه است؛ Commit Log برای بازیابی پس از Crash نگه داشته می‌شود. Flush داده را به SSTable تغییرناپذیر می‌برد؛ Compaction نسخه‌های قدیمی و فایل‌ها را ترکیب می‌کند. طراحی زمان Ack تعیین می‌کند کدام Write پس از Crash تضمین بقا دارد؛ نوشتن در RAM یا Cache الزاماً Durable نیست.

در Read، ابتدا وضعیت جدیدتر حافظه و سپس فایل‌ها بررسی می‌شوند. Bloom Filter برای حذف جست‌وجوی بیهوده است؛ Merkle Tree برای مقایسهٔ بازه‌های داده بین Nodeهاست. Gossip خبر عضویت/خرابی را پخش می‌کند، اما «گزارش عدم پاسخ» لزوماً مرگ قطعی Node نیست. Network Partition را با Node Failure اشتباه نگیر.

## تمرین و پاسخ

1. CAS روی کلید ناموجود چه می‌دهد؟ — False؛ این تابع عملیات Create نیست. برای ساختن کلید از قید یکتای DB و Insert استفاده کن.
2. `N=3, W=1, R=1` چه محدودیتی دارد؟ — ممکن است Read از Nodeی بیاید که Write جدید را ندیده؛ تازگی فوری تضمین نمی‌شود.
3. دو Vector Clock مستقل را با Timestamp انتخاب کنیم؟ — یک سیاست حل Conflict اضافه کرده‌ایم، ولی ساعت، ترتیب علت‌ومعلولی و معنای محصول همچنان مهم‌اند.
4. آیا Replica جای Backup است؟ — خیر؛ حذف اشتباه می‌تواند Replicate شود. بازیابی تاریخی و نگهداری نسخه موضوع جداست.

**مرز پیاده‌سازی:** آزمایشگاه CAS واقعی SQL و مقایسهٔ Vector Clock را اجرا می‌کند؛ موتور LSM، Gossip و کلاستر Quorum را نمی‌سازد.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 2 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
