# فصل ۱۵ — File Sync، نسخه و Conflict

**عنوان کتاب:** Design Google Drive · صفحات ۲۴۴ تا ۲۶۳ PDF.

## فایل و Metadata را جدا نگه دار

Byteهای فایل در Object Storage قرار می‌گیرند؛ مالک، مسیر، Version، وضعیت Upload و فهرست Blockها در DB. وقتی فایل بزرگ فقط کمی تغییر کند، فرستادن کل فایل هزینه‌بر است. Delta Sync بلوک‌های تغییرکرده را منتقل می‌کند؛ Hash محتوا به تشخیص تکرار کمک می‌کند. فشرده‌سازی و Deduplication دو بهینه‌سازی متفاوت‌اند.

دانلود باید از روی یک Manifest مشخص انجام شود تا Blockهای نسخه‌های مختلف مخلوط نشوند. Upload قابل ادامه، History و Client آفلاین به شناسهٔ Upload، شمارهٔ Block، Checksum و Cursor تغییرات نیاز دارند. Notification صرفاً خبر تغییر است؛ Client باید وضعیت معتبر را از Metadata بگیرد.

## Django: جلوگیری از بازنویسی ناخواسته

این نمونه پس از اینکه Blob کامل و معتبر در Storage ثبت شد اجرا می‌شود. `verified_key` باید از رکورد Upload تأییدشدهٔ همین User بیاید، نه متن آزاد درخواست.

```python
from django.conf import settings
from django.db import models, transaction

class DriveFile(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    version = models.PositiveBigIntegerField(default=1)
    blob_key = models.CharField(max_length=300)

class Revision(models.Model):
    file = models.ForeignKey(DriveFile, on_delete=models.CASCADE)
    version = models.PositiveBigIntegerField()
    blob_key = models.CharField(max_length=300)
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["file", "version"], name="unique_file_revision")]

class SyncConflict(Exception):
    pass

def publish_revision(file_id, user_id, expected_version, verified_key):
    with transaction.atomic(using="default"):
        file = DriveFile.objects.using("default").select_for_update().get(
            pk=file_id, owner_id=user_id)
        if file.version != expected_version:
            raise SyncConflict(file.version)
        Revision.objects.using("default").get_or_create(
            file=file, version=file.version,
            defaults={"blob_key": file.blob_key})
        file.version += 1
        file.blob_key = verified_key
        file.save(using="default", update_fields=["version", "blob_key"])
        Revision.objects.using("default").create(
            file=file, version=file.version, blob_key=verified_key)
    return file.version
```

دو دستگاه Version=4 را دیده‌اند. اولی Version=5 ثبت می‌کند؛ دومی Conflict می‌گیرد و View باید HTTP 409 و نسخهٔ فعلی را برگرداند. محصول می‌تواند «نسخهٔ متعارض» نگه دارد یا اجازهٔ Merge بدهد. Last-write-wins ممکن است فایل کاربر را بی‌خبر از بین ببرد.

این قفل در PostgreSQL هماهنگی همان فایل را انجام می‌دهد. نمونه History را نگه می‌دارد ولی DB به‌تنهایی تغییرناپذیری Revision را تضمین نکرده؛ API و Permission باید ویرایش History را ممنوع کنند. برای تکرار درخواست پس از Timeout، Upload ID/Idempotency Key جدا لازم است تا Commit موفق به Conflict مبهم تبدیل نشود.

## Strong Consistency در عمل

خواندن Metadata حساس را از Primary انجام بده. Cache و Replica عقب‌مانده می‌توانند Version قدیمی نشان دهند؛ همان Router عمومی فصل ۱ را بدون سیاست جدید استفاده نکن. Transaction DB، Write به Object Storage را اتمیک نمی‌کند: اول Blob معتبر، سپس ارجاع Metadata؛ Blobهای بدون ارجاع را بعداً با مهلت امن Cleanup کن.

برای Blockها، فهرست مرتب `(position, hash)` و اندازه را در Manifest نگه دار. Hash برابر دلیل مجوز دانلود نیست. Deduplication بین کاربران نباید دسترسی به فایل خصوصی ایجاد کند. حذف Block مشترک هم باید فقط پس از بررسی ارجاع‌ها و سیاست نگهداری انجام شود.

Sync لحظه‌ای چند نویسنده روی متن با Conflict فایل متفاوت است؛ OT/CRDT موضوع جداست. این نمونه Google Docs همزمان نمی‌سازد.

**تمرین:** دستگاه دوم با Version قدیمی فایل می‌فرستد. **پاسخ:** Upload می‌تواند انجام شده باشد، اما انتشار Metadata باید 409 بدهد؛ تصمیم Merge/Conflict با محصول است و Blob بلااستفاده باید Cleanup شود.


## دو دستگاه و یک فایل: نتیجه را پیش‌بینی کن

فایل در Version=1 است. موبایل و لپ‌تاپ همین Version را می‌خوانند. موبایل نسخهٔ تازه را با `expected_version=1` منتشر می‌کند و DB به ۲ می‌رود. لپ‌تاپ هنوز ۱ می‌فرستد؛ Service به‌جای بازنویسی خاموش، `SyncConflict` می‌دهد. Client باید نسخهٔ تازه را بگیرد، Merge کند یا فایل متعارض جدا بسازد.

در آزمایشگاه `publish_revision` از قبل آماده است. ابتدا `DriveFile` را بساز و Blob Key معتبر اولیه بده. Blob Key در این تمرین فقط ارجاع است؛ انتقال فایل واقعی داخل این Service نیست.

```python
from demo.services import publish_revision, SyncConflict

version = publish_revision(file.pk, owner.pk, 1, "verified/blob-v2")
try:
    publish_revision(file.pk, owner.pk, 1, "verified/laptop-copy")
except SyncConflict as conflict:
    print("server version:", conflict.args[0])  # 2
```

فقط رکورد Upload تأییدشدهٔ همان Owner باید `verified_key` را تولید کند. اگر View این پارامتر را مستقیم از JSON بگیرد، ممکن است کاربر به Blob دیگری ارجاع بدهد. Transaction DB نمی‌تواند مالکیت یک رشتهٔ Storage Key را جادویی تضمین کند.

## Block و Delta Sync را عملی ببین

در `demo/blocks.py` فایل به Blockهای ثابت خوانده می‌شود؛ برای هر Block شماره، SHA-256 و Byteها برمی‌گردد. خروجی Generator است تا کل فایل یک‌جا در RAM قرار نگیرد. نمونهٔ کوچک با اندازهٔ دو Byte فقط برای دیدن تغییرات:

```python
from io import BytesIO
from demo.blocks import iter_blocks

before = list(iter_blocks(BytesIO(b"aabbcc"), block_size=2))
after = list(iter_blocks(BytesIO(b"aazzcc"), block_size=2))
print([a[1] == b[1] for a, b in zip(before, after)])  # [True, False, True]
```

در این تغییر، فقط Block وسط متفاوت است. اگر ابتدای فایل یک Byte Insert شود، مرز Block ثابت ممکن است بخش بزرگی از Blockهای بعدی را تغییر دهد. Content-defined Chunking می‌تواند برای برخی الگوها بهتر باشد ولی پیچیدگی بیشتری دارد؛ نمونهٔ ما آن را پیاده نمی‌کند.

Manifest باید ترتیب Blockها، Hash، طول و Version را نگه دارد. هنگام Download، Client بلوک‌ها را با همان Manifest مرتب وصل و Checksum را بررسی می‌کند. فقط مجموعهٔ Hashها کافی نیست؛ ترتیب متفاوت، فایل متفاوت می‌سازد.

## Resumable Upload و انتشار اتمیک Metadata

Upload Session باید Owner، هدف فایل، تعداد/اندازهٔ Blockها، زمان انقضا و وضعیت داشته باشد. هر Block با شماره/Checksum ثبت می‌شود تا Retry همان بخش دوباره اثر نامطلوب ندهد. بعد از تکمیل و بررسی همهٔ Blockها، Version فایل در DB منتشر می‌شود. تا آن لحظه فایل قبلی باید قابل خواندن بماند.

اگر انتشار Metadata Rollback شود، Blob آپلودشده ممکن است بدون ارجاع بماند. Cleanup فوری خطرناک است چون Upload دیگر شاید هنوز در حال Commit باشد؛ مهلت امن و بررسی ارجاع‌ها لازم است. برای History، Retention و Quota را روی نسخه‌ها هم حساب کن. Deduplication فضای Byte را کم می‌کند ولی Metadata و Backup همچنان هزینه دارند.

## Sync خبر تغییر را چگونه می‌گیرد؟

برای نسخهٔ کوچک، Client می‌تواند با Cursor تغییرات را Poll کند. Long Polling یا WebSocket تأخیر خبر را کم می‌کند؛ پیام خبر، جای مرجع Metadata نیست. Client آفلاین پس از برگشت باید از Cursor پایدار تغییرها را بگیرد، نه فقط آخرین اعلان زنده را. ترتیب تغییرها، Tombstone حذف و نگهداری تاریخچهٔ Cursor باید تعریف شوند.

Strong Consistency در فایل به معنی نمایش یک Version معتبر است؛ دو Client شبکه‌ای لزوماً در یک لحظهٔ دیواری UI یکسان نشان نمی‌دهند. سرویس باید عملیات Metadata را با قرارداد خواندن/نوشتن و نسخهٔ فایل سازگار پاسخ دهد. Cache Replica قدیمی می‌تواند این قرارداد را بشکند؛ Read حساس را به Primary بفرست.

## تمرین و پاسخ

1. کاربر غیرمالک Version تازه منتشر کند. — Query مالکیت رکوردی پیدا نمی‌کند؛ مجوز برقرار نیست.
2. Version قبلی را دوباره بفرست. — Conflict؛ برای Retry پس از پاسخ گم‌شده Idempotency Key جدا لازم است. این نسخه آن را پیاده نکرده است.
3. Hash دو Block برابر باشد. — محتوا در این قرارداد برابر است ولی مجوز استفاده/دانلود همچنان جداست.
4. Revision قدیمی را تغییر بدهیم؟ — API باید منع کند؛ Model به‌تنهایی Append-only نیست. سیاست DB و دسترسی برای الزام سخت‌تر لازم است.

**تست‌ها:** History، Conflict، مالکیت و تشخیص Block تغییرکرده بررسی می‌شوند؛ Object Storage، Resume شبکه و ویرایش همزمان متن OT/CRDT اجرا نشده‌اند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
