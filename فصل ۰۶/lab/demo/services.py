from django.db import models
from django.db.models import F

from .models import Entry

def compare_and_set(key, expected_version, new_value):
    changed = Entry.objects.using("default").filter(
        key=key, version=expected_version,
    ).update(value=new_value, version=F("version") + 1)
    return changed == 1

def clock_relation(left, right):
    keys=set(left)|set(right)
    less=any(left.get(k,0)<right.get(k,0) for k in keys)
    more=any(left.get(k,0)>right.get(k,0) for k in keys)
    if less and more: return "concurrent"
    if less: return "before"
    if more: return "after"
    return "equal"
