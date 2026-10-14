# فصل ۱۱ — ساخت News Feed

**عنوان کتاب:** Design A News Feed System · صفحات ۱۶۶ تا ۱۷۷ PDF.

## خواندن و منتشر کردن دو مسیر جدا هستند

وقتی کاربر Post می‌سازد، می‌توان ID آن را از قبل در Feed دنبال‌کننده‌ها گذاشت: **Fanout-on-write**. هنگام خواندن، Feed آماده است ولی نوشتن برای نویسندهٔ پرطرفدار گران می‌شود. در **Fanout-on-read**، هنگام خواندن Postهای نویسندگان دنبال‌شده را جمع می‌کنیم؛ نوشتن ساده‌تر و خواندن گران‌تر است. طراحی Hybrid برای نویسندگان معمولی Write Fanout و برای افراد بسیار پرطرفدار Read Fanout دارد.

## Django: ابتدا Pull قابل فهم

مدل‌های زیر فقط Post عمومی و Follow ساده را پوشش می‌دهند. آن‌ها را در اپ مستقل با Migration قرار بده. Block، Privacy و الگوریتم Ranking در این نسخه نیستند.

```python
from django.conf import settings
from django.db import models

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="following_edges")
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="follower_edges")
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["follower", "author"], name="unique_follow")]

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["author", "-id"])]

def read_feed(user_id, before_id=None):
    authors = Follow.objects.using("default").filter(
        follower_id=user_id).values("author_id")
    qs = Post.objects.using("default").filter(author_id__in=authors)
    if before_id is not None:
        qs = qs.filter(id__lt=before_id)
    return list(qs.select_related("author").order_by("-id")[:20])
```

`author_id__in` با QuerySet، Subquery SQL می‌سازد؛ همهٔ Author IDها را ابتدا در Python بار نمی‌گیریم. `select_related` جلوی Query جداگانه برای هر نویسنده را می‌گیرد. `before_id` یک Cursor ساده است؛ برای ترتیب زمانی دقیق از `(created_at, id)` استفاده کن. Auto-increment ترتیب Commit همزمان را تضمین نمی‌کند؛ این مثال Feed عمومی با ترتیب ID نزولی دارد.

Offset بزرگ ممکن است با رشد Feed گران شود و با Insert جدید صفحه‌ها جابه‌جا شوند. Keyset Pagination با کلید مرتب‌سازی ثابت معمولاً مناسب‌تر است. Cursor باید با همین قرارداد ساخته شود.

## تبدیل به Push

مدل `FeedEntry(user, post)` با قید Unique روی همان دو فیلد بساز. پس از ثبت Post، یک Outbox ایجاد کن. Worker دنبال‌کننده‌ها را دسته‌دسته می‌گیرد و Entry می‌سازد. مثلاً در هر Batch با `bulk_create` صدها رکورد می‌نویسد؛ قید Unique باعث می‌شود تکرار Task رکورد تکراری تولید نکند. در PostgreSQL، `ignore_conflicts=True` می‌تواند درج تکراری را رد کند؛ مدل و داده باید همچنان اعتبارسنجی شوند.

در این مدل FeedEntry بهتر است ID/ارجاع نگه دارد؛ اگر تمام متن Post را کپی کنی، Edit و Delete باید همهٔ کپی‌ها را هم اصلاح کنند. قبل از پاسخ، Visibility و Block را بررسی کن؛ داشتن ID در Cache یا FeedEntry مجوز نمایش نیست.

## تصمیم مقیاس

برای ۱۰۰ دنبال‌کننده، Fanout نوشتن ممکن است ارزان باشد. برای میلیون‌ها دنبال‌کننده، همزمان میلیون‌ها Insert یا Job می‌سازد و Queue را اشباع می‌کند. Hybrid، Batch و محدود کردن مقدار Feed نگهداری‌شده راه‌های رشدند. Graph DB برای همهٔ پروژه‌ها لازم نیست؛ Follow رابطه‌ای با Index مناسب نقطهٔ شروع خوبی است.

**تمرین:** اگر کاربر Unfollow کرد Entryهای قبلی چه می‌شوند؟ **پاسخ:** یا پاک می‌شوند یا هنگام خواندن فیلتر می‌شوند؛ باید قرارداد محصول مشخص باشد. بدون این تصمیم، Cache قدیمی ممکن است Post ناخواسته نشان دهد.


## مسیر Pull را با داده اجرا کن

در آزمایشگاه، User معمولی از طریق `Follow` نویسنده‌ها را دنبال می‌کند. `read_feed` فقط Postهای آن نویسنده‌ها را می‌خواند. هر Post در DB اصلی یک رکورد دارد؛ خواندن Feed Join/Subquery لازم را انجام می‌دهد. برای شروع کوچک، همین طراحی ساده می‌تواند مناسب باشد؛ زود وارد صدها میلیون Fanout نشو.

```python
from demo.services import read_feed, fanout_post, read_push_feed

posts = read_feed(user_id=reader.pk)
fanout_post(post.pk)
ready_posts = read_push_feed(reader.pk)
```

برای تمرین، Userها و Follow/Post را در Shell بساز؛ نام Modelها در `demo/models.py` است. `FeedEntry` هم از قبل آماده است. `fanout_post` دنبال‌کننده‌ها را با Iterator می‌خواند و در Batchهای ۱۰۰تایی Entry می‌سازد؛ همهٔ دنبال‌کننده‌ها را یک‌باره در حافظه بار نمی‌کند.

## چرا Fanout باید Idempotent باشد؟

Worker ممکن است بعد از ساخت چند Batch بمیرد. اجرای بعدی دوباره از ابتدا می‌رود. قید یکتا روی `(user, post)` اجازه نمی‌دهد همان Post دو بار در Feed همان کاربر ثبت شود. `bulk_create(ignore_conflicts=True)` در این تمرین برای درج تکراری استفاده می‌شود. اعتبار داده را قبل از Batch بررسی کن؛ به رفتار حذف خطا در Backendهای مختلف تکیه نکن.

بعد از Unfollow، Entry قدیمی هنوز در DB ممکن است باقی باشد. `read_push_feed` Followهای فعلی را هنگام خواندن بررسی می‌کند تا آن را نمایش ندهد. این قرارداد مثال است؛ برخی محصولات Feed تاریخی را حفظ می‌کنند. برای Private Post، Block و حذف محتوا، یک مرحلهٔ مستقل Visibility لازم است و تست این نسخه آن قواعد را اثبات نمی‌کند.

## Hybrid را چگونه به کد تبدیل کنیم؟

یک فهرست نویسندگان با Fanout گران داشته باش. Worker برای آن‌ها Entry میلیونی نسازد؛ هنگام Read، Postهای تازهٔ آن‌ها با Feed آماده Merge شوند. همهٔ منابع باید کلید مرتب‌سازی یکسان، Deduplication و Cursor سازگار داشته باشند. «دو List را بچسبان» Feed مرتب و صفحه‌بندی‌شده نمی‌سازد.

انتخاب مرز Celebrity صرفاً عدد Follower نیست؛ نرخ Publish و تعداد دنبال‌کنندگان فعال هم مهم است. نویسنده با یک میلیون Follower و یک Post در سال، هزینهٔ متفاوتی از نویسنده با صد Post روزانه دارد. حالت Hybrid باید هنگام عوض شدن طبقهٔ نویسنده، دادهٔ قدیمی و Cursor را هم مدیریت کند.

## Cache و Edit/Delete

Cache می‌تواند IDهای Feed و دادهٔ Post را جدا نگه دارد. اگر متن را در همهٔ Feedها کپی کنیم، Edit میلیون‌ها کپی لازم دارد. ذخیرهٔ ID اجازه می‌دهد متن را از مرجع مرکزی بگیریم؛ ولی تعداد Read بیشتری ممکن است داشته باشیم، پس Batch Fetch/Cache Post مفید است. Delete باید Visibility در Read را هم قطع کند تا کپی قدیمی Cache نمایش داده نشود.

در Cache شخصی، کلید باید User را شامل شود. TTL مساوی روی همهٔ Userها ممکن است Cache Stampede بدهد؛ Jitter و پر کردن هماهنگ کمک می‌کنند. Hit Rate خوب ممکن است Feed خیلی قدیمی بدهد؛ تازگی و زمان Fanout را جدا اندازه بگیر.

## ترتیب و Pagination

آزمایشگاه با ID نزولی مرتب می‌کند؛ قراردادش دقیقاً همین است. برای ترتیب زمان واقعی، `(created_at, id)` و Cursor شامل هر دو لازم است. برای Ranking، امتیازها عوض می‌شوند؛ ممکن است Snapshot یا Session Feed لازم باشد تا بین صفحه‌ها رکورد تکرار یا حذف نشود. Offset عمیق هم هزینهٔ Scan و رفتار نامطلوب هنگام Insert دارد.

## تمرین و پاسخ

1. Fanout یک Post را دو بار اجرا کن. — تعداد Entry ثابت می‌ماند.
2. User دنبال‌کننده نیست. — در Push Entry نمی‌گیرد و در Pull هم Post را نمی‌بیند.
3. Follow را حذف کن ولی Entry را نگه دار. — تابع Read این نسخه آن را فیلتر می‌کند.
4. یک Post تازه بین صفحهٔ اول و دوم ایجاد شود. — Cursor مبتنی بر `before_id` رکوردهای قدیمی‌تر را دنبال می‌کند؛ قرارداد ID را با ترتیب Commit اشتباه نگیر.

**مرز آزمایش:** Pull، Push دسته‌ای و Retry محلی اجرا می‌شوند. Worker توزیع‌شده، Ranking و Privacy کامل ساخته نشده‌اند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
