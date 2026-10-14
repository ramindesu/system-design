import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from demo.models import PublicDocument
from demo.algorithms import Snowflake
a=PublicDocument.objects.create(title="demo-a");b=PublicDocument.objects.create(title="demo-b")
gen=Snowflake(7);values=[gen.next_id() for _ in range(3)]
print("distinct UUIDs:",a.pk!=b.pk)
print("snowflake values:",values,"worker:",(values[0]>>12)&1023)
