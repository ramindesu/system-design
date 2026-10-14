import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from demo.models import Follow,Post,FeedEntry
from demo.services import read_feed,fanout_post,read_push_feed
reader,_=User.objects.get_or_create(username="demo-reader")
author,_=User.objects.get_or_create(username="demo-author")
Follow.objects.get_or_create(follower=reader,author=author)
post=Post.objects.create(author=author,body="Hello feed")
fanout_post(post.pk);fanout_post(post.pk)
print("entries for this post:",FeedEntry.objects.filter(post=post,user=reader).count())
print("pull ids:",[p.pk for p in read_feed(reader.pk)])
print("push ids:",[p.pk for p in read_push_feed(reader.pk)])
