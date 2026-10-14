# فصل ۱۴ — سرویس ویدئو و مسیر Upload تا Playback

**عنوان کتاب:** Design YouTube · صفحات ۲۲۰ تا ۲۴۳ PDF.

## Django کدام بخش را انجام می‌دهد؟

Django مجوز Upload، Metadata، وضعیت پردازش و مجوز Playback را مدیریت می‌کند. فایل حجیم بهتر است مستقیم به Object Storage برود. Worker تخصصی Transcoding، Thumbnail و نسخه‌های مختلف را تولید می‌کند؛ CDN ویدئو را به بیننده می‌رساند. عبور تمام ویدئو از Worker وب، ظرفیت و هزینهٔ برنامه را بی‌دلیل درگیر می‌کند.

در کتاب، Upload و Streaming جدا هستند؛ Pipeline پردازش می‌تواند DAG داشته باشد: Inspection سپس Video/Audio Encoding و Thumbnail؛ وظیفه‌های مستقل موازی و وابستگی‌ها مشخص‌اند. Codec، Container، Resolution و Bitrate مفاهیم متفاوت‌اند. HLS/DASH با Segment و Manifest اجازه می‌دهند Player کیفیت را متناسب با شبکه تغییر دهد.

## Django: اجازهٔ Upload مستقیم

نمونهٔ Service زیر برای اپ مستقل است. به `boto3`، Bucket خصوصی و Credentials سرور نیاز دارد؛ هیچ حساب یا سرویس پولی در این بسته ایجاد نشده است.

```python
import os
import uuid
import boto3
from django.conf import settings
from django.db import models

class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    object_key = models.CharField(max_length=300, unique=True)
    status = models.CharField(max_length=16, default="pending")

def start_video_upload(user, size):
    if not user.is_authenticated:
        raise PermissionError("login required")
    if not isinstance(size, int) or not 1 <= size <= 500_000_000:
        raise ValueError("invalid size")
    video_id = uuid.uuid4()
    key = f"raw/{user.pk}/{video_id}.mp4"
    video = Video.objects.using("default").create(
        id=video_id, owner=user, object_key=key)
    s3 = boto3.client("s3")
    upload = s3.generate_presigned_post(
        Bucket=os.environ["VIDEO_BUCKET"], Key=key,
        Fields={"Content-Type": "video/mp4"},
        Conditions=[{"Content-Type": "video/mp4"},
                    ["content-length-range", 1, size]],
        ExpiresIn=300,
    )
    return {"video_id": str(video.pk), "upload": upload}
```

Client فایل را با Form Fields برگشتی به URL Storage POST می‌کند. MIME اعلام‌شده محتوای واقعی را ثابت نمی‌کند. پس از Upload، Backend با اطلاعات Storage و بررسی فایل باید اندازه و نوع واقعی را تأیید کند. اعلام «آپلود تمام شد» توسط Client دلیل آماده بودن ویدئو نیست.

## تکمیل Workflow

وضعیت‌های پیشنهادی: `pending → uploaded → processing → ready / failed`. در یک Transaction، وضعیت Upload تأییدشده و Outbox پردازش را ثبت کن. Worker فایل را با Timeout و منابع محدود Inspect می‌کند، نسخه‌ها را می‌سازد و Manifest را فقط پس از آماده شدن خروجی معتبر منتشر می‌کند. Output Key می‌تواند شامل Video ID و نسخهٔ Pipeline باشد تا Retry خروجی نامرتبط نسازد.

برای ویدئوی خصوصی، مالکیت و دسترسی را روی درخواست Playback بررسی کن و URL دانلود/پخش با انقضا بده. Upload Key را از ورودی آزاد Client نگیر. Upload ناقص، خام بدون Metadata و خروجی شکست‌خورده به Cleanup دوره‌ای نیاز دارند.

نمونه این فصل Transcoder یا CDN واقعی راه‌اندازی نمی‌کند؛ نقطهٔ اتصال کد Django به Storage را نشان می‌دهد. در اجرای واقعی، کارایی Encoding، هزینهٔ Egress، طول صف، زمان تا Ready و خطاهای Playback را اندازه بگیر. قابلیت Live Streaming خارج از Scope این مثال است.

**تمرین:** چرا ساخت Thumbnail را داخل POST اصلی انجام نمی‌دهیم؟ **پاسخ:** CPU و زمان متغیرش Worker وب را اشغال می‌کند؛ پاسخ Upload باید سریع باشد و پردازش با وضعیت قابل پیگیری انجام شود.

[منبع رسمی: Presigned URL/POST در Boto3](https://docs.aws.amazon.com/boto3/latest/guide/s3-presigned-urls.html)


## مستقیم Upload کردن یعنی چه؟

Client ابتدا از Django مجوز می‌گیرد. Django مالک، سقف حجم و Object Key را تعیین می‌کند و اجازهٔ کوتاه‌مدت می‌دهد. Client Byteها را به Storage می‌فرستد؛ Django در این مسیر حامل فایل نیست. سپس Client درخواست Finish می‌دهد، اما Server باید وجود و اندازهٔ Object را از Storage تأیید کند، نه از ادعای Client.

نمونهٔ Boto3 ابتدای فصل Connector واقعی را نشان می‌دهد؛ آزمایشگاه `lab` همین مرز را با `DemoStorage` محلی اجرا می‌کند تا حساب ابری لازم نباشد. این Storage فقط شبیه‌ساز قرارداد است، نه ویدئوپلیر یا S3 محلی. داده را در RAM نگه می‌دارد و در Restart از بین می‌رود.

```python
from demo.services import start_upload, finish_upload, mark_ready, playback_key
from demo.storage import DemoStorage

storage = DemoStorage()
result = start_upload(user, max_size=1000, storage=storage)
storage.put(result["key"], b"example bytes")
finish_upload(result["video_id"], user.pk, storage)
# A real worker would inspect/transcode the uploaded object before mark_ready.
```

`finish_upload` Metadata را روی Primary قفل می‌کند، وضعیت را Uploaded می‌کند و `ProcessingJob` پایدار می‌سازد. OneToOne روی Job برای هر Video در این Scope جلوی Job تکراری ناشی از Retry Finish را می‌گیرد. Pipeline نسخه‌دار یا Reprocess چندباره به Model گسترده‌تر و Unique روی `(video, pipeline_version)` نیاز دارد.

## نسخهٔ Object و نتیجهٔ Worker قدیمی

Storage می‌تواند اجازه دهد یک Key دوباره نوشته شود. برای پردازش معتبر باید دقیقاً بدانیم کدام Version/Object Generation پردازش شده است. آزمایشگاه Generation را هنگام Finish ثبت می‌کند و `mark_ready` فقط با همان Generation نتیجه را منتشر می‌کند. نسخهٔ واقعی باید Worker را به همان Object Version مقید کند یا Key غیرقابل بازنویسی داشته باشد؛ ثبت یک رشته در DB به‌تنهایی محتوای Storage را Freeze نمی‌کند.

Jobهای مختلف ممکن است با Retry چند بار اجرا شوند. Output Key بهتر است به Video ID، نسخهٔ Pipeline و Generation مربوط باشد. Manifest نهایی فقط بعد از موفقیت خروجی‌های لازم منتشر شود. اگر Worker قدیمی خروجی نسل قبلی را دیرتر برگرداند، نباید نسخهٔ فعال جدید را بازنویسی کند.

## Transcoding را به مراحل قابل مشاهده تقسیم کن

Inspection نوع واقعی، Codec، Duration و سالم بودن فایل را بررسی می‌کند. مرحلهٔ Encoding کیفیت‌های مناسب را می‌سازد. Thumbnail یک وظیفهٔ مستقل است. بسته‌بندی HLS/DASH، Segmentها و Manifest پخش را می‌سازد. یک مرحلهٔ شکست‌خورده باید وضعیت، Retry و Cleanup خودش را داشته باشد؛ «Task اجرا شد» کافی نیست.

در خط فرمان می‌توان FFmpeg را با `subprocess.run` و آرگومان‌های List، Timeout و Resource Limit اجرا کرد؛ ورودی کاربر را به Command Shell تبدیل نکن. نام فایل داخل Storage با Path فایل موقت Worker فرق دارد. این آزمایشگاه FFmpeg، بررسی محتوای واقعی و Encoding را اجرا نمی‌کند؛ انتشار Metadata را تمرین می‌کند.

## Playback و هزینهٔ مقیاس

وقتی Video هنوز Ready نیست، URL پخش برنگردان. برای ویدئوی خصوصی، Owner/Permission را بررسی و اجازهٔ کوتاه‌مدت Playback صادر کن. در ویدئوی عمومی، CDN می‌تواند Segmentهای مشترک را Cache کند. مسیر Manifest و سیاست Cache باید با نسخهٔ خروجی سازگار باشد تا Segmentهای نسل‌های مختلف ترکیب نشوند.

Throughput Upload، زمان صف Encoding، CPU Worker، نسبت خطای Pipeline و حجم Egress را جدا ببین. چند نسخهٔ کیفیت برای هر ویدئو Storage بیشتری می‌گیرد؛ ساخت همهٔ کیفیت‌ها برای ویدئوی کم‌تماشا همیشه انتخاب اقتصادی مناسبی نیست. قابلیت Live Streaming با تولید و مصرف همزمان Segment و Latency هدف متفاوت، طراحی تازه‌ای می‌خواهد.

## تمرین و پاسخ

1. Finish قبل از Upload صدا زده شود. — Object وجود ندارد؛ وضعیت Pending باقی می‌ماند.
2. حجم از سقف مجاز بیشتر باشد. — Finish رد می‌شود؛ اعتماد به Content-Type یا JSON کافی نیست.
3. Finish دوبار برسد. — در این Scope یک Job باقی می‌ماند.
4. Worker با Generation قدیمی Ready اعلام کند. — Update پذیرفته نمی‌شود.
5. کاربر دیگر Playback Key را بخواهد. — مجوز رد می‌شود، حتی اگر UUID ویدئو را بداند.

**تست‌ها:** قرارداد محلی Upload/Finish، مالکیت، سقف حجم، یک Job و انتشار نسل درست بررسی می‌شوند. Provider واقعی، CDN و Transcoding آزمایش نشده‌اند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
