# فصل ۱۰ — اعلان قابل اتکا با Outbox

**عنوان کتاب:** Design A Notification System · صفحات ۱۵۱ تا ۱۶۵ PDF.

## مسئله فقط send_mail نیست

اعلان می‌تواند Email، SMS یا Push باشد. API درخواست را می‌پذیرد، ترجیح کاربر و قالب را بررسی می‌کند، کار را در Queue کانال مناسب می‌گذارد و Worker به Provider می‌فرستد. اتصال‌های Provider، Retry، محدودیت نرخ و وضعیت Delivery باید جدا مدیریت شوند.

«پذیرفته‌شدن توسط Provider» الزاماً «دیده‌شدن توسط کاربر» نیست. Pending، Accepted، Delivered و Failed وضعیت‌های متفاوت‌اند. همچنین یک Queue برای کانال کند نباید همهٔ کانال‌ها را متوقف کند.

## شکاف بین Commit و Queue

اگر اول DB را Commit کنیم و بعد `.delay()` بزنیم، ممکن است برنامه وسط این دو بمیرد. اگر قبل از Commit پیام بدهیم، Worker شاید داده را نبیند یا Transaction بعداً Rollback شود. `on_commit` زمان‌بندی را بهتر می‌کند، اما شکافِ از دست رفتن پیام را حذف نمی‌کند.

**Outbox:** درخواست اعلان و Event آن را در یک Transaction DB ذخیره کن. یک Publisher مستقل Eventهای ارسال‌نشده را مرتب به Broker بفرستد.

```python
import uuid
from django.db import models, transaction

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=16, default="pending")

class Outbox(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(Notification, on_delete=models.PROTECT)
    published_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

def request_email(recipient, subject, body):
    with transaction.atomic(using="default"):
        item = Notification.objects.using("default").create(
            recipient=recipient, subject=subject, body=body)
        Outbox.objects.using("default").create(notification=item)
    return item.pk
```

این مدل‌ها در یک اپ مستقل با Migration قرار می‌گیرند. اگر اعلان نتیجهٔ یک عملیات مهم مثل ثبت سفارش است، **همان Transaction سفارش** باید Outbox را هم ایجاد کند، نه Transaction جدا بعد از سفارش.

## Publisher و Delivery

برای فهم رفتار، Publisher زیر ساده و تک‌پردازشی است. به Celery App، Broker و Task پیکربندی‌شده نیاز دارد:

```python
from django.utils import timezone
from .tasks import deliver_email

def publish_batch():
    events = list(Outbox.objects.using("default")
                  .filter(published_at__isnull=True).order_by("created_at")[:100])
    for event in events:
        deliver_email.delay(str(event.notification_id))
        Outbox.objects.using("default").filter(
            pk=event.pk, published_at__isnull=True
        ).update(published_at=timezone.now())
```

اگر پس از ارسال به Broker و پیش از Update برنامه بمیرد، Event دوباره ارسال می‌شود. پس Outbox **At-least-once** ایجاد می‌کند، نه Exactly-once. نسخهٔ چند Publisher به Claim/Lease فصل ۹ نیاز دارد. تأیید Broker و دوام تنظیمات آن نیز شرط مهمی است.

برای آزمایش ارسال در Django می‌توان از `django.core.mail.send_mail` و Console Email Backend استفاده کرد. اما چک سادهٔ `status == "sent"` قبل از ارسال، جلوی همهٔ تکرارها را نمی‌گیرد: Worker ممکن است ایمیل را بفرستد و پیش از ثبت وضعیت بمیرد. اگر Provider پشتیبانی می‌کند، `notification.id` را به‌عنوان **Idempotency Key** همان درخواست بده؛ اگر SMTP معمولی است، احتمال ارسال تکراری را باید در طراحی بپذیری و کاهش دهی.

Retry را محدود و با Exponential Backoff و Jitter انجام بده؛ خطای دائمی آدرس نامعتبر را بی‌نهایت تکرار نکن. پیام‌های شکست‌خورده به Dead Letter و ابزار بررسی نیاز دارند. Eventهای Outbox موفق را با سیاست نگهداری پاک‌سازی کن.

**تمرین:** چرا `transaction.on_commit` به‌تنهایی اعلان پرداخت را تضمین نمی‌کند؟ **پاسخ:** پس از Commit هنوز ممکن است Process پیش از Publish بمیرد. Outbox قصد ارسال را در DB پایدار نگه می‌دارد.

[منبع رسمی: رفتار Task و Retry در Celery](https://docs.celeryq.dev/en/stable/userguide/tasks.html)


## Outbox را از ابتدا تا انتها اجرا کن

در آزمایشگاه `request_email` Notification و Outbox را با هم ثبت می‌کند. `publish_batch` یک Callback می‌گیرد که نقش Broker را بازی می‌کند؛ برای تمرین از `list.append` استفاده می‌کنیم. هیچ ایمیل واقعی ارسال نمی‌شود و حساب سرویس خارجی لازم نیست.

```python
from demo.services import request_email, publish_batch, deliver, DemoProvider

messages = []
notification_id = request_email("reader@example.com", "Order", "Your order is ready")
publish_batch(messages.append)
provider = DemoProvider()
for message_id in messages:
    deliver(message_id, provider)
print(provider.accepted)
```

`DemoProvider` درخواست‌های پذیرفته‌شده را با Idempotency Key در حافظه نگه می‌دارد. این جای Provider واقعی نیست؛ ابزاری برای دیدن اثر Retry است. Provider واقعی باید دربارهٔ مدت نگهداری Key، پاسخ Replay و تفاوت Payload قرارداد مشخص داشته باشد. Console Email Backend هم برای دیدن متن مناسب است ولی تضمین Idempotency ندارد.

## خطای بین دو مرحله را عمداً بساز

Publisher را با Callbackای اجرا کن که خطا می‌دهد. `published_at` باید خالی بماند؛ دفعهٔ بعد امکان Retry هست. اگر Callback موفق شد ولی DB Update شکست خورد، احتمال Publish تکراری داریم. این طراحی تک Publisher است؛ نسخهٔ چند Publisher به Lease/Claim و معیار Pending Age نیاز دارد.

در Worker، Provider درخواست را پذیرفته ولی ثبت وضعیت DB انجام نشده است. آزمایشگاه پارامتر `simulate_crash=True` دارد که دقیقاً در این نقطه Exception می‌دهد. اجرای دوباره با همان Key، در Provider تمرینی پذیرش تازه ایجاد نمی‌کند. اگر Provider واقعی این قابلیت را ندارد، DB Status به‌تنهایی این شکاف را نمی‌بندد.

**تفاوت ضمانت‌ها:** Outbox قصد ارسال را حفظ می‌کند؛ Broker دوام و تحویل به Worker را مدیریت می‌کند؛ Idempotency اثر تکرار را کنترل می‌کند؛ Delivery Receipt خبر رسیدن را می‌دهد. یکی را جای دیگری نگذار. حتی پذیرفته شدن درخواست ایمیل به معنی خوانده شدن آن نیست.

## Payload، Template و ترجیح کاربر

برای پیام‌های قراردادی مثل رسید خرید، ثبت نسخهٔ Template و دادهٔ لازم کمک می‌کند Retry همان محتوا را بفرستد. اگر Worker هر بار قیمت امروز را بخواند، رسید خرید دیروز ممکن است عوض شود. برای پیام تبلیغاتی، Preference/Unsubscribe باید هنگام تصمیم ارسال بررسی شود؛ قبول درخواست اولیه مجوز همیشگی ارسال نیست.

Push Token منقضی را از وضعیت خطای Provider تشخیص بده؛ یک User می‌تواند چند Device داشته باشد. SMS، Email و Push صف و Rate Limit جدا می‌خواهند تا کانال کند بقیه را متوقف نکند. Credentials در Environment/Secret Store باشند و متن خصوصی اعلان در Log کامل ثبت نشود.

## Retry، DLQ و مشاهده‌پذیری

Timeout لزوماً به معنی نرسیدن درخواست نیست؛ ممکن است Provider دریافت کرده باشد و فقط پاسخ گم شده باشد. برای Retry همان Key را حفظ کن. Backoff را با Jitter و تعداد تلاش محدود کن. پیام Poison که همیشه خطا دارد باید به حالت قابل بررسی برود، نه اینکه صف را برای همیشه بچرخاند.

سه زمان جدا را اندازه بگیر: از Event تا Publish، از Publish تا اجرای Worker و از Provider Acceptance تا Delivery. Pending Age از طول صف به‌تنهایی مفیدتر است؛ هزار پیام تازه ممکن است طبیعی باشد ولی ده پیام سه‌روزه مشکل است.

## تمرین و پاسخ

1. Transaction بیرونی را Rollback کن. — Notification و Outbox هر دو ناپدید می‌شوند؛ نمونه Service در Atomic بیرونی شرکت می‌کند.
2. Publish شکست بخورد. — Event پاک یا Published نمی‌شود؛ Retry بعدی آن را می‌بیند.
3. بعد از Provider Acceptance برنامه Crash کند. — Key یکسان باید Replay شود؛ در Provider تمرینی یک پذیرش ثبت می‌شود.
4. وضعیت DB را `sent` نام‌گذاری کنیم؟ — فقط اگر معنی آن را دقیق بدانیم؛ این آزمایشگاه `accepted` دارد و ادعای Delivery نمی‌کند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
