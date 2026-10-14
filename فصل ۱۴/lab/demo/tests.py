from django.contrib.auth.models import User
from django.test import TestCase
from .models import Video,ProcessingJob
from .storage import DemoStorage
from .services import start_upload,finish_upload,mark_ready,playback_key
class VideoTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("owner");self.other=User.objects.create_user("other")
        self.storage=DemoStorage();self.upload=start_upload(self.user,10,self.storage)
    def test_missing_or_oversized_blob_not_published(self):
        with self.assertRaises(KeyError):finish_upload(self.upload["video_id"],self.user.pk,self.storage)
        self.storage.put(self.upload["key"],b"x"*11)
        with self.assertRaises(ValueError):finish_upload(self.upload["video_id"],self.user.pk,self.storage)
        self.assertEqual(ProcessingJob.objects.count(),0)
    def test_retry_and_generation(self):
        self.storage.put(self.upload["key"],b"small")
        for _ in range(2):finish_upload(self.upload["video_id"],self.user.pk,self.storage)
        self.assertEqual(ProcessingJob.objects.count(),1)
        video=Video.objects.get()
        self.assertFalse(mark_ready(video.pk,"wrong","encoded/a.m3u8"))
        self.assertTrue(mark_ready(video.pk,video.generation,"encoded/a.m3u8"))
        self.assertEqual(playback_key(video.pk,self.user.pk),"encoded/a.m3u8")
    def test_owner_check_and_pending_playback(self):
        with self.assertRaises(Video.DoesNotExist):finish_upload(self.upload["video_id"],self.other.pk,self.storage)
        with self.assertRaises(ValueError):playback_key(self.upload["video_id"],self.user.pk)
