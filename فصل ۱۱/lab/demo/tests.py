from django.test import TestCase
from django.contrib.auth.models import User
from .models import Post,Follow,FeedEntry
from .services import read_feed,fanout_post,read_push_feed
class FeedTests(TestCase):
    def setUp(self):
        self.reader=User.objects.create_user("reader");self.author=User.objects.create_user("author")
        self.stranger=User.objects.create_user("stranger")
        Follow.objects.create(follower=self.reader,author=self.author)
        self.a=Post.objects.create(author=self.author,body="a")
        self.b=Post.objects.create(author=self.author,body="b")
        Post.objects.create(author=self.stranger,body="hidden by follow rule")
    def test_pull_order_and_cursor(self):
        self.assertEqual([p.pk for p in read_feed(self.reader.pk)],[self.b.pk,self.a.pk])
        self.assertEqual([p.pk for p in read_feed(self.reader.pk,self.b.pk)],[self.a.pk])
    def test_fanout_retry_is_idempotent(self):
        fanout_post(self.a.pk,batch_size=1);fanout_post(self.a.pk,batch_size=1)
        self.assertEqual(FeedEntry.objects.count(),1)
        self.assertEqual([p.pk for p in read_push_feed(self.reader.pk)],[self.a.pk])
        self.assertEqual(read_push_feed(self.stranger.pk),[])
    def test_unfollow_filters_existing_entry(self):
        fanout_post(self.a.pk);Follow.objects.all().delete()
        self.assertEqual(FeedEntry.objects.count(),1)
        self.assertEqual(read_push_feed(self.reader.pk),[])
