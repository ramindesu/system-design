from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "study-only-local-key-do-not-deploy"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "demo"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "study.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "config.urls"
MIDDLEWARE = []
USE_TZ = True
CACHES = {name: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": name}
          for name in ("default", "cache-a", "cache-b", "cache-c", "cache-d")}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
