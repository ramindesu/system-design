from contextlib import contextmanager
from contextvars import ContextVar
from django.conf import settings
from django.db import connections

_primary_reads = ContextVar("catalog_primary_reads", default=False)


@contextmanager
def primary_reads():
    token = _primary_reads.set(True)
    try:
        yield
    finally:
        _primary_reads.reset(token)


class CatalogRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label != "catalog":
            return "default"  # auth/session/contenttypes stay on the primary
        if (not settings.REPLICA_ENABLED or _primary_reads.get()
                or connections["default"].in_atomic_block):
            return "default"
        return "replica"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db in {"default", "replica"} and obj2._state.db in {"default", "replica"}

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "default":
            return True
        return settings.SIMULATED_REPLICA and app_label == "catalog"
