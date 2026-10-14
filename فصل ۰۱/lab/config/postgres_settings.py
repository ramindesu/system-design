"""Optional real cluster configuration; replication itself is managed outside Django."""
import os
from .settings import *

DATABASES = {
    alias: {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["PGDATABASE"],
        "USER": os.environ[f"{prefix}_USER"],
        "PASSWORD": os.environ[f"{prefix}_PASSWORD"],
        "HOST": os.environ[f"{prefix}_HOST"],
        "PORT": os.environ.get(f"{prefix}_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 3},
    }
    for alias, prefix in (("default", "PRIMARY"), ("replica", "REPLICA"))
}
REPLICA_ENABLED = True
SIMULATED_REPLICA = False
