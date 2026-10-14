# آزمایشگاه فصل 12

این پوشه یک پروژهٔ مستقل Django 5.2 است. Python 3.12 پیشنهاد می‌شود.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python demo_script.py
python manage.py shell
```

Modelها در `demo/models.py`، منطق در `demo/services.py` و تست‌های رفتاری در `demo/tests.py` هستند. مثال‌های فصل را با همین نام‌ها در Shell تمرین کن. این پروژه API عمومی کامل نیست؛ بخش‌های آموزشی از Shell و تست اجرا می‌شوند. تنظیمات فقط برای توسعهٔ محلی‌اند.

تست پیش‌فرض با SQLite است و همزمانی/قفل/کارایی PostgreSQL یا سرویس بیرونی را اثبات نمی‌کند. نیازهای تکمیلی و محدودیت‌های مخصوص این فصل در جزوه توضیح داده شده‌اند.

## اجرای مثال بدون نوشتن کد اولیه

بعد از Migration، `python demo_script.py` دادهٔ تمرینی لازم را می‌سازد و رفتار اصلی این فصل را چاپ می‌کند. فقط در همین پروژهٔ محلی تمرینی اجرا کن؛ دادهٔ نمونه را ایجاد یا بازنشانی می‌کند. هیچ پیام، پرداخت یا درخواست شبکهٔ خارجی در این Script انجام نمی‌شود. مثال‌های اختیاری Provider/WebSocket جزوه از این مسیر جدا هستند.
