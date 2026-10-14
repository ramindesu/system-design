from django.conf import settings
from django.db import models

from .models import Follow, Post

def read_feed(user_id, before_id=None):
    authors = Follow.objects.using("default").filter(
        follower_id=user_id).values("author_id")
    qs = Post.objects.using("default").filter(author_id__in=authors)
    if before_id is not None:
        qs = qs.filter(id__lt=before_id)
    return list(qs.select_related("author").order_by("-id")[:20])

from .models import FeedEntry

def fanout_post(post_id, batch_size=100):
    if type(batch_size) is not int or batch_size < 1:raise ValueError("positive batch size required")
    post=Post.objects.get(pk=post_id)
    ids=Follow.objects.filter(author_id=post.author_id).values_list("follower_id",flat=True).iterator(chunk_size=batch_size)
    batch=[]
    for user_id in ids:
        batch.append(FeedEntry(user_id=user_id,post_id=post_id))
        if len(batch)==batch_size:
            FeedEntry.objects.bulk_create(batch,ignore_conflicts=True);batch=[]
    if batch:FeedEntry.objects.bulk_create(batch,ignore_conflicts=True)

def read_push_feed(user_id, before_id=None):
    authors=Follow.objects.filter(follower_id=user_id).values("author_id")
    qs=FeedEntry.objects.filter(user_id=user_id,post__author_id__in=authors)
    if before_id is not None:qs=qs.filter(post_id__lt=before_id)
    return [e.post for e in qs.select_related("post__author").order_by("-post_id")[:20]]
