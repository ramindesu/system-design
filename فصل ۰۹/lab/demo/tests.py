from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from .models import CrawlJob
from .services import enqueue,claim_job,complete_job,requeue_expired
class CrawlerTests(TestCase):
    def test_fragment_dedup_and_host_contract(self):
        self.assertEqual(enqueue("https://example.com/a#one").pk,enqueue("https://example.com/a#two").pk)
        with self.assertRaises(ValueError):enqueue("https://other.example/a")
    def test_reclaim_fences_old_worker(self):
        enqueue("https://example.com/a"); old=claim_job()
        CrawlJob.objects.filter(pk=old["id"]).update(lease_until=timezone.now()-timedelta(seconds=1))
        self.assertEqual(requeue_expired(),1)
        new=claim_job(); self.assertNotEqual(old["token"],new["token"])
        self.assertFalse(complete_job(old["id"],old["token"]))
        self.assertTrue(complete_job(new["id"],new["token"]))
        self.assertFalse(complete_job(new["id"],new["token"]))
    def test_empty_queue(self): self.assertIsNone(claim_job())
