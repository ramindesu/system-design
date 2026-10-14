# فصل ۸ — ساخت URL Shortener

**عنوان کتاب:** Design A URL Shortener · صفحات ۱۱۹ تا ۱۳۱ PDF.

## مسیر داده

کاربر URL بلند می‌دهد؛ سرویس یک Code می‌سازد و Mapping را نگه می‌دارد. در درخواست کوتاه، Code به URL اصلی تبدیل می‌شود و Redirect برمی‌گردد. این سرویس معمولاً Read بسیار بیشتر از Write دارد، پس Cache Mapping مفید است.

کتاب Hash با رسیدگی به Collision و تبدیل ID به Base62 را مقایسه می‌کند. Base62 فشرده‌سازی عدد در الفبای ۶۲کاراکتری است، نه رمزنگاری. `62**7` حدود ۳٫۵ تریلیون حالت دارد. Hash کوتاه Collision ممکن دارد؛ «اول چک کن بعد Insert کن» به‌تنهایی در Concurrent Request امن نیست و قید Unique DB لازم است.

## یک پیاده‌سازی کوچک Django

این مدل و View را در یک اپ مستقل بگذار و Migration بساز. برای تابع Base62 از `examples/algorithms.py` استفاده کن و آن را داخل اپ پروژه کپی کن.

```python
from django.db import models, transaction
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect, Http404
from .encoding import base62

class ShortLink(models.Model):
    target = models.URLField(max_length=2000)
    code = models.CharField(max_length=22, unique=True, null=True)

def create_link(target):
    URLValidator(schemes=["http", "https"])(target)
    if len(target) > 2000:
        raise ValueError("URL too long")
    with transaction.atomic(using="default"):
        link = ShortLink.objects.using("default").create(target=target)
        link.code = base62(link.pk)
        link.save(using="default", update_fields=["code"])
    return link

def redirect_link(request, code):
    try:
        link = ShortLink.objects.using("default").get(code=code)
    except ShortLink.DoesNotExist:
        raise Http404
    return HttpResponseRedirect(link.target)  # 302
```

برای Create، یک POST View با احراز هویت، اعتبارسنجی JSON و Rate Limit فصل ۴ اضافه کن. اینجا Service و Redirect را نشان دادیم. قید Unique روی Code جلوی تکرار را می‌گیرد و PK یک DB منبع تخصیص عدد است. در چند Shard مستقل، این PK دیگر لزوماً جهانی Unique نیست؛ فصل ۷ لازم می‌شود.

`null=True` اجازه می‌دهد ابتدا ID تولید شود و سپس Code در همان Transaction ثبت شود. Code قابل حدس است و این طراحی برای لینک عمومی است؛ برای لینک خصوصی باید Permission و احتمالاً Token مستقل داشته باشی. این نسخه یک URL را می‌تواند چند بار با Codeهای مختلف ثبت کند؛ Deduplication تصمیم محصول جداست.

## ۳۰۱ یا ۳۰۲؟

۳۰۱ می‌گوید انتقال دائمی است و ممکن است Cache شود؛ برای مقصد قابل تغییر یا تحلیل کلیک در سمت سرویس، ۳۰۲ معمولاً کنترل بیشتری می‌دهد. رفتار Cache به Header و Client هم وابسته است. افزایش شمارندهٔ کلیک را در مسیر Redirect سنگین نکن؛ Event را غیرهمزمان پردازش کن.

**تمرین:** چرا URL اصلی را از Base62 نمی‌توان به‌تنهایی بازیابی کرد؟ **پاسخ:** Base62 فقط ID را برمی‌گرداند؛ Mapping ID→URL در DB است. حذف رکورد، مقصد را از بین می‌برد.


## ID تا Code را قدم‌به‌قدم حساب کن

الفبای نمونه ابتدا ۰ تا ۹، بعد a تا z و بعد A تا Z است. مقدار ۶۲ تقسیم بر ۶۲، خارج‌قسمت ۱ و باقی‌مانده ۰ دارد؛ پس Code آن `10` می‌شود. مقدار ۶۱ آخرین کاراکتر الفباست. این قرارداد الفبا باید ثابت بماند؛ عوض کردن ترتیب آن Codeهای قبلی را ناسازگار می‌کند.

در آزمایشگاه مدل `ShortLink` در `demo/models.py` و Service در `demo/services.py` قرار دارد. نیازی به کپی دستی مدل از جزوه نیست؛ Migration همراه است. در Shell:

```python
from demo.services import create_link

link = create_link("https://example.com/articles/system-design")
print(link.pk, link.code, link.target)
```

سپس `python manage.py runserver` را اجرا کن و مسیر `/s/<code>/` را باز کن. View فقط Redirect را انجام می‌دهد. ساخت لینک در این آزمایشگاه از Shell است؛ Endpoint عمومی Create و Login کامل پیاده نشده‌اند. این تفکیک جلوی اشتباه گرفتن Service تمرینی با محصول آمادهٔ انتشار را می‌گیرد.

## چرا Transaction اینجا مهم است؟

قبل از Insert، PK نداریم. رکورد ایجاد می‌شود، Code از PK ساخته می‌شود و رکورد Update می‌شود. اگر مرحلهٔ دوم شکست بخورد، Transaction رکورد ناقص را Rollback می‌کند. قید Unique برای Code در DB است. هرکدام از این‌ها هدف جدا دارند؛ `atomic` بدون قید Unique جلوی همهٔ Collisionهای منطقی را نمی‌گیرد.

برای لینک تازه، Redirect فوری از Replica ممکن است 404 بدهد چون Mapping هنوز نرسیده است. در نسخهٔ ساده از Primary می‌خوانیم. اگر بعداً Replica اضافه کردی، قرارداد «لینک تازه فوراً قابل استفاده است» را با Primary Routing یا Fallback محدود پوشش بده. Cache منفی 404 هم می‌تواند مشکل را طولانی کند؛ TTL و سیاست لینک تازه را جدا انتخاب کن.

## نسخهٔ Cache‌شده و تغییر مقصد

می‌توان `short:<code>` را Cache کرد. اگر مقصد قابل تغییر است، Update باید Cache را پس از Commit حذف کند. TTL طولانی بدون Invalidation مقصد قدیمی نشان می‌دهد. اگر لینک Expiry دارد، زمان انقضا باید هنگام Redirect بررسی و TTL Cache به زمان باقی‌مانده محدود شود. حذف Record بدون توجه به Cache ممکن است لینک را همچنان زنده نگه دارد.

Hash کوتاه و Base62 دو راه متفاوت‌اند. در Hash کوتاه، Collision با Unique Constraint و ساخت Candidate جدید رسیدگی می‌شود؛ Bloom Filter فقط احتمال وجود را سریع بررسی می‌کند و مرجع نهایی یکتایی نیست. در Base62، یکتایی از ID منبع می‌آید. کلید اعداد متوالی اطلاعات حجم و امکان Enumeration می‌دهد؛ برای لینک محرمانه Token تصادفی و Permission جدا لازم است.

## Logging و تحلیل کلیک

اطلاعات Auth را در Query String URL کوتاه قرار نده. ثبت کلیک بهتر است Event سبک با Timestamp و Code باشد؛ نگهداری IP و دستگاه باید با نیاز واقعی و سیاست داده محدود شود. اگر Redirect را ۳۰۱ کنیم، بعضی درخواست‌های بعدی مستقیماً به مقصد می‌روند و Server تمام کلیک‌ها را نمی‌بیند. ۳۰۲ هم بدون قرارداد Cache، تضمین شمارش دقیق همهٔ رفتار مرورگر نیست.

## تمرین و پاسخ

1. `javascript:` را به Create بده. — URLValidator فقط HTTP/HTTPS را می‌پذیرد؛ لینک ذخیره نمی‌شود.
2. یک Code ناموجود را باز کن. — 404؛ نباید به یک مقصد پیش‌فرض ناشناس فرستاده شود.
3. یک URL را دو بار ثبت کن. — در این نسخه دو رکورد داریم؛ Deduplication خودکار جزء Scope نیست.
4. اگر میلیاردها ID بخواهیم چه می‌شود؟ — طول Code افزایش می‌یابد؛ برای چند مرجع تخصیص باید ID جهانی Unique داشته باشیم.

**تست‌ها:** Validation، Code متفاوت، Mapping درست، پاسخ 302 و 404 بررسی می‌شوند؛ Analytics و Cache توزیع‌شده در این آزمایشگاه نیستند.

## شروع عملی این فصل

پوشهٔ `lab` همین فصل یک پروژهٔ مستقل است. فایل `lab/README.md` روش نصب و اجرا را توضیح می‌دهد. پس از نصب Django و اجرای Migration، دستور `python demo_script.py` مثال اصلی را با دادهٔ تمرینی اجرا می‌کند؛ `python manage.py test` هم تست‌های رفتاری را اجرا می‌کند. در این مسیر فقط محیط محلی استفاده می‌شود و حساب سرویس خارجی لازم نیست. کدهای Connector اختیاری در متن، نیازهای جدا دارند.

**نتیجهٔ بررسی:** 3 تست این فصل با SQLite پاس شده است. این نتیجه، عملکرد کلاستر، Provider واقعی یا تست همزمانی PostgreSQL نیست.
