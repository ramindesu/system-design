import hashlib
import unicodedata
from django.db import models
from django.core.cache import cache

from .models import Suggestion

def normalize(text):
    return unicodedata.normalize("NFC", text).replace("ي", "ی").replace("ك", "ک").strip().casefold()

def suggest(raw_prefix):
    prefix = normalize(raw_prefix)
    if not 2 <= len(prefix) <= 40:
        return []
    digest = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
    key = f"suggest:v1:{digest}"
    missing = object()
    result = cache.get(key, missing)
    if result is not missing:
        return result
    result = list(Suggestion.objects.using("default")
        .filter(normalized__startswith=prefix)
        .order_by("-score", "normalized").values_list("term", flat=True)[:5])
    cache.set(key, result, timeout=60)
    return result
