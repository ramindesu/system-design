# فصل ۱۲ — Chat، ترتیب پیام و اتصال دائم

**عنوان کتاب:** Design A Chat System · صفحات ۱۷۸ تا ۱۹۹ PDF.

## WebSocket فقط مسیر انتقال است

Polling مرتب سراغ پیام می‌رود. Long Polling اتصال را تا پیام یا Timeout نگه می‌دارد. WebSocket ارتباط دوطرفهٔ دائم می‌دهد. اما هیچ‌کدام به‌تنهایی پیام را پایدار ذخیره نمی‌کنند یا تحویل به دستگاه آفلاین را تضمین نمی‌کنند. Login و History می‌توانند HTTP باشند؛ پیام زنده WebSocket.

هر دستگاه Cursor آخرین پیام دریافت‌شده را نگه می‌دارد. بعد از Reconnect، پیام‌های بعد از آن را از DB می‌گیرد. اعلان Push برای کاربر آفلاین جای History پایدار را نمی‌گیرد. Presence با Heartbeat و TTL تقریبی است؛ بسته نشدن تمیز Socket نباید کاربر را برای همیشه Online نگه دارد.

## Django: ذخیره و ترتیب پیام داخل Room

در این نمونه همهٔ مدل‌ها در یک PostgreSQL هستند. Room Lock ترتیب محلی اتاق را هماهنگ می‌کند. قید Client ID جلوی اثر تکراری Retry را می‌گیرد.

```python
from django.conf import settings
from django.db import models, transaction

class Room(models.Model):
    next_seq = models.PositiveBigIntegerField(default=1)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL)

class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    client_id = models.UUIDField()
    seq = models.PositiveBigIntegerField()
    body = models.CharField(max_length=4000)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["room", "seq"], name="room_seq"),
            models.UniqueConstraint(fields=["room", "sender", "client_id"], name="message_retry"),
        ]

def store_message(room_id, user_id, client_id, body):
    if not isinstance(body, str) or not 1 <= len(body) <= 4000:
        raise ValueError("invalid message")
    with transaction.atomic(using="default"):
        room = Room.objects.using("default").select_for_update().get(pk=room_id)
        if not room.members.using("default").filter(pk=user_id).exists():
            raise PermissionError("not a member")
        old = Message.objects.using("default").filter(
            room=room, sender_id=user_id, client_id=client_id).first()
        if old:
            if old.body != body:
                raise ValueError("client_id was reused with a different body")
            return old
        message = Message.objects.using("default").create(
            room=room, sender_id=user_id, client_id=client_id,
            seq=room.next_seq, body=body)
        room.next_seq += 1
        room.save(using="default", update_fields=["next_seq"])
        return message
```

Client برای Retry همان UUID را می‌فرستد؛ پیام جدید UUID جدید می‌گیرد. این Transaction فقط در یک دیتابیس است. هماهنگی تغییر Membership هم باید سیاست Transaction مشخصی داشته باشد؛ چک عضویت بدون هماهنگی با حذف همزمان عضو، مجوز لحظه‌ای قطعی نمی‌دهد.

History پس از احراز هویت و بررسی عضویت:

```python
messages = list(Message.objects.using("default")
    .filter(room_id=room_id, seq__gt=last_seq)
    .order_by("seq")[:100])
```

اگر فقط Auto-increment عمومی را به‌عنوان Cursor Commit استفاده کنیم، تراکنش همزمان می‌تواند ID کوچک‌تر را دیرتر Commit کند و Client آن را جا بیندازد. Sequence داخل Room با Lock این مثال را قابل کنترل‌تر می‌کند، به شرط اینکه همهٔ نویسندگان همین مسیر را طی کنند.

## اتصال به Django Channels

با نصب Channels و تنظیم ASGI، می‌توان `JsonWebsocketConsumer` نوشت. نمونهٔ زیر فقط اتصال و عضویت را نشان می‌دهد؛ دریافت، ذخیره و Broadcast باید به Service بالا متصل شوند.

```python
from channels.generic.websocket import JsonWebsocketConsumer

class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope["user"]  # AuthMiddlewareStack must be configured
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        if not user.is_authenticated or not Room.objects.filter(
                pk=self.room_id, members=user).exists():
            self.close(code=4403)
            return
        self.accept()
```

برای ORM همگام، Consumer همگام در Thread اجرا می‌شود. برای Consumer غیرهمگام، ORM همگام را مستقیم داخل Event Loop صدا نزن. ASGI Routing، کنترل Origin با `AllowedHostsOriginValidator`، Auth، اندازهٔ پیام و Rate Limit لازم‌اند. برای Broadcast بین Processها Channel Layer مشترک مثل Redis نیاز داری؛ Backend حافظه‌ای فقط برای توسعه است.

ابتدا Commit، سپس Broadcast کن. اگر Broadcast از دست رفت، Client باید با Cursor و DB جبران کند. Channel Layer به‌تنهایی صندوق پیام پایدار کاربر نیست. برای اتاق خیلی پررفت‌وآمد، Lock هر پیام سقف Throughput ایجاد می‌کند؛ Partitioning بر اساس Room و Sequencer تخصصی گزینهٔ رشدند.

**تمرین:** کاربر یک پیام را سه بار Retry می‌کند. **پاسخ:** همان `client_id` باید یک Message ایجاد کند؛ Ack باید شناسه و Sequence همان پیام را برگرداند.

[منبع رسمی: Django Channels Consumers](https://channels.readthedocs.io/en/stable/topics/consumers.html)


## یک پیام را از Sender تا Receiver دنبال کن

Client یک UUID برای پیام تازه تولید می‌کند و همراه متن می‌فرستد. Server هویت و عضویت Room را بررسی می‌کند؛ پیام و Sequence را در DB ذخیره می‌کند؛ بعد از Commit، Ack شامل `client_id` و `seq` برمی‌گرداند. اگر Ack گم شد، Client همان UUID را Retry می‌کند. Server همان Message را می‌دهد و دوباره Sequence مصرف نمی‌کند.

در Shell آزمایشگاه:

```python
import uuid
from demo.services import store_message, history

key = uuid.uuid4()
message = store_message(room.pk, sender.pk, key, "سلام")
again = store_message(room.pk, sender.pk, key, "سلام")
print(message.pk == again.pk, message.seq)  # True, 1 for a new room
print(history(room.pk, sender.pk, last_seq=0))
```

User و Room را با Modelهای `demo.models` بساز و `room.members.add(sender)` بزن. `history` هم عضویت را بررسی می‌کند؛ محافظت فقط در ارسال کافی نیست. در پاسخ عمومی، اطلاعات خصوصی مثل User ID دیگران را متناسب با محصول محدود کن.

## Sequence و Sync چند دستگاه

شمارهٔ پیام داخل هر Room ترتیب دارد؛ Roomهای مختلف لازم نیست یک ترتیب کلی جهانی داشته باشند. موبایل و لپ‌تاپ هرکدام Cursor خود را دارند. Cursor را پس از ثبت محلی پیام‌های دریافت‌شده جلو ببر؛ اگر ابتدا Cursor را ذخیره و سپس ذخیرهٔ Message خراب شود، پیام ممکن است در Sync بعدی جا بیفتد.

اگر ۱۰۰ پیام عقب مانده‌ای، Server تا ۱۰۰ پیام می‌دهد و Client با Cursor آخر آن‌ها دوباره می‌خواند. Ack ارسال، Ack تحویل به دستگاه و Read Receipt سه چیز متفاوت‌اند. وجود رکورد در DB به معنی دیده شدن در UI گیرنده نیست. Group بزرگ، Read Receipt و Fanout هزینهٔ متفاوتی از گفت‌وگوی دونفره دارند.

## نمونهٔ اتصال WebSocket در پوشهٔ کد

`demo/consumers.py` نمونهٔ همگام Channels با Connect، Receive، ذخیره، Ack و Broadcast دارد. `config/asgi.py` Routing، Authentication و کنترل Origin را تعریف می‌کند. نصب وابستگی‌های `requirements-optional.txt` برای این مسیر لازم است؛ تست پیش‌فرض فقط Service DB را اجرا می‌کند.

Channel Layer پیش‌فرض این نمونه حافظه‌ای و تک‌Process است. برای چند Process باید Redis Channel Layer مشترک پیکربندی کنی. Login/Session معتبر از پروژهٔ اصلی باید فراهم شود؛ این آزمایشگاه صفحهٔ Login یا Client کامل Chat ندارد. این فایل‌ها مسیر اتصال به یک پروژهٔ Django موجود را نشان می‌دهند، نه پیام‌رسان آمادهٔ انتشار.

اگر Broadcast شکست بخورد، Message در DB باقی است. Receiver با `history` آن را جبران می‌کند. Channel Layer صف دائمی History نیست و حتی در اجرای صحیح پیام زنده ممکن است دوباره دیده شود؛ Client براساس `(room, seq)` Deduplicate کند. فایل Consumer نمونه کنترل نرخ کامل ندارد؛ از سیاست فصل ۴ استفاده کن و اندازهٔ Frame را در Server هم محدود کن.

## Presence و Discovery

Heartbeat هر دستگاه را با TTL جدا ثبت کن. Online بودن User می‌تواند یعنی حداقل یک Device هنوز معتبر است. Disconnect Callback قطعی نیست؛ قطع برق و شبکه ممکن است هیچ Callback تمیزی ندهد. TTL خبر آفلاین را با کمی تأخیر می‌دهد، که برای Presence معمولاً پذیرفتنی است.

هر Socket به یک Process وصل است؛ Stateless بودن API به معنی Stateless بودن اتصال WebSocket نیست. Gateway، Routing به Chat Server، Registry اتصال و انتقال پیام بین Processها نیاز به طراحی دارند. تعداد اتصال باز، مصرف حافظهٔ هر اتصال، صف ارسال کند و نرخ Reconnect را اندازه بگیر؛ QPS HTTP همهٔ ظرفیت Chat را نشان نمی‌دهد.

## تمرین و پاسخ

1. UUID یکسان با متن متفاوت ارسال شود. — خطای تناقض، نه ساخت پیام تازه.
2. عضویت گیرنده حذف شود. — History باید رد شود؛ اتصال زنده هم نیاز به بازبینی مجوز و خروج از Group دارد. نمونه در ارسال/دریافت مجوز را دوباره بررسی می‌کند ولی Fanout عضویت زیر بار همزمان طراحی تکمیلی می‌خواهد.
3. Process بعد از Commit و قبل از Broadcast بمیرد. — Sync از DB پیام را پیدا می‌کند؛ برای اطلاع‌رسانی قابل اتکاتر Outbox اضافه کن.
4. آیا Sequence Lock مقیاس نامحدود دارد؟ — خیر؛ Room بسیار داغ می‌تواند گلوگاه شود. Partition بر اساس Room، Sequencer و Batch موضوع رشدند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
