import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from io import BytesIO
from django.contrib.auth.models import User
from demo.models import DriveFile
from demo.services import publish_revision,SyncConflict
from demo.blocks import iter_blocks
user,_=User.objects.get_or_create(username="demo-owner")
file=DriveFile.objects.create(owner=user,name="demo-notes",blob_key="blob/v1")
print("new version:",publish_revision(file.pk,user.pk,1,"blob/v2"))
try:publish_revision(file.pk,user.pk,1,"blob/conflict")
except SyncConflict as exc:print("conflict, current version:",exc.args[0])
a=list(iter_blocks(BytesIO(b"aabbcc"),2));b=list(iter_blocks(BytesIO(b"aazzcc"),2))
print("unchanged blocks:",[x[1]==y[1] for x,y in zip(a,b)])
