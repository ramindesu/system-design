import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from demo.models import Entry
from demo.services import compare_and_set,clock_relation
Entry.objects.update_or_create(key="demo:likes",defaults={"value":{"likes":10},"version":1})
print("first write:",compare_and_set("demo:likes",1,{"likes":11}))
print("stale write:",compare_and_set("demo:likes",1,{"likes":99}))
print("clock relation:",clock_relation({"A":3,"B":1},{"A":2,"B":2}))
