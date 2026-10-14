import time
from django.db import connections
from django.test.utils import CaptureQueriesContext
from .algorithms import capacity

def measure(fn):
    start = time.perf_counter()
    with CaptureQueriesContext(connections["default"]) as queries:
        result = fn()
    return {"result": result, "queries": len(queries), "elapsed_ms": (time.perf_counter()-start)*1000}
