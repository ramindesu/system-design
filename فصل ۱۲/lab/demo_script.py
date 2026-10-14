import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

import uuid
from django.contrib.auth.models import User
from demo.models import Room
from demo.services import store_message,history
user,_=User.objects.get_or_create(username="demo-member")
room=Room.objects.create();room.members.add(user)
key=uuid.uuid4();a=store_message(room.pk,user.pk,key,"hello")
b=store_message(room.pk,user.pk,key,"hello")
store_message(room.pk,user.pk,uuid.uuid4(),"next")
print("same message:",a.pk==b.pk,"history:",[m.seq for m in history(room.pk,user.pk)])
