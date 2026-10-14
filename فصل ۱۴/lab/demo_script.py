import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from demo.models import Video
from demo.storage import DemoStorage
from demo.services import start_upload,finish_upload,mark_ready,playback_key
user,_=User.objects.get_or_create(username="demo-owner")
storage=DemoStorage();upload=start_upload(user,1000,storage)
storage.put(upload["key"],b"sample bytes - not a real video")
finish_upload(upload["video_id"],user.pk,storage)
video=Video.objects.get(pk=upload["video_id"])
mark_ready(video.pk,video.generation,"encoded/demo.m3u8")
print("metadata playback key:",playback_key(video.pk,user.pk))
print("Metadata simulation only: no real encoding, CDN, or cloud account.")
