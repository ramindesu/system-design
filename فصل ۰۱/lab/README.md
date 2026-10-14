# آزمایشگاه فصل اول

Python 3.12 و Django 5.2.18. از همین پوشه اجرا کن:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --database=default
python manage.py migrate --database=replica
python manage.py seed_demo
python manage.py snapshot_replica
python manage.py test
python manage.py runserver
```

سپس `http://127.0.0.1:8000/books/1/` را باز کن. `?fresh=1` Cache را دور می‌زند.

## Replica را در Shell ببین

```bash
REPLICA_ENABLED=1 python manage.py shell
```

```python
from catalog.models import Book
from catalog.services import update_price

Book.objects.get(pk=1).price                      # replica: 100.00
update_price(1, "150.00")                         # primary write
Book.objects.get(pk=1).price                      # replica: 100.00
Book.objects.using("default").get(pk=1).price      # primary: 150.00
```

بعد از خروج از Shell، `python manage.py snapshot_replica` را دوباره اجرا کن. این کپی دستی فقط برای آموزش است و در اتصال واقعی Standby عمداً ممنوع شده است.

## تغییر قیمت از HTTP

`POST /books/1/price/` به کاربر Loginشده با Permission `catalog.change_book` و CSRF Token معتبر نیاز دارد. به همین دلیل برای اولین تمرین از Service در Shell استفاده می‌کنیم. تست‌ها مسیر مجوز، JSON نامعتبر، دادهٔ ناموجود و CSRF را بررسی می‌کنند. Endpoint عمومی Write بدون مجوز نیست.

## اتصال واقعی اختیاری

یک PostgreSQL Primary/Standby واقعی باید قبلاً آماده باشد. نصب `psycopg[binary]`، تنظیم `PGDATABASE` و متغیرهای زیر لازم است:

```text
PRIMARY_HOST, PRIMARY_USER, PRIMARY_PASSWORD, PRIMARY_PORT (optional)
REPLICA_HOST, REPLICA_USER, REPLICA_PASSWORD, REPLICA_PORT (optional)
```

سپس با `--settings=config.postgres_settings` اجرا کن. Migration را روی Primary اجرا کن. این فایل فقط اتصال‌ها را تعریف می‌کند و Replication را راه نمی‌اندازد. برای Read Replica از DB Role فقط‌خواندنی استفاده کن.

## نتیجهٔ بررسی

۱۵ تست Django موفق: Routing واقعی در Autocommit، Context و Lazy QuerySet، Read قدیمی، Write روی Primary، Cache Hit/Miss، Commit/Rollback، اعتبارسنجی قیمت، مجوز و CSRF. تست‌ها با SQLite مستقل اجرا شده‌اند؛ Row Lock و Failover واقعی PostgreSQL بررسی نشده‌اند.
