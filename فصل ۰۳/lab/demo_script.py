import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

import uuid
from django.contrib.auth.models import User
from demo.models import Inventory
from demo.services import reserve
user,_=User.objects.get_or_create(username="demo-reader")
item=Inventory.objects.create(available=2)
key=uuid.uuid4()
a=reserve(item.pk,user.pk,key,1);b=reserve(item.pk,user.pk,key,1)
item.refresh_from_db()
print("same reservation:",a.pk==b.pk,"remaining:",item.available)
