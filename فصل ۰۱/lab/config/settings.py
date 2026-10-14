import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Local teaching setup. Supply a separate secret and disable DEBUG in deployment.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-study-only-do-not-deploy")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.staticfiles", "catalog",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "primary.sqlite3"},
    "replica": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "replica.sqlite3"},
}
REPLICA_ENABLED = os.environ.get("REPLICA_ENABLED", "0") == "1"
# Only the simulation may migrate its independent SQLite snapshot.
SIMULATED_REPLICA = True
DATABASE_ROUTERS = ["catalog.routing.CatalogRouter"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "study"}}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
