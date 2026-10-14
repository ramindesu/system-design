from django.test import TestCase
from django.db import transaction
from .models import Notification,Outbox
from .services import request_email,publish_batch,deliver,DemoProvider
class NotificationTests(TestCase):
    def test_outer_rollback_removes_outbox(self):
        try:
            with transaction.atomic():
                request_email("reader@example.com","a","b")
                raise RuntimeError()
        except RuntimeError: pass
        self.assertEqual(Notification.objects.count(),0); self.assertEqual(Outbox.objects.count(),0)
    def test_publish_failure_retains_pending_event(self):
        request_email("reader@example.com","a","b")
        def broken(message):raise RuntimeError("broker offline")
        with self.assertRaises(RuntimeError):publish_batch(broken)
        self.assertIsNone(Outbox.objects.get().published_at)
        queue=[]; self.assertEqual(publish_batch(queue.append),1)
        self.assertEqual(publish_batch(queue.append),0);self.assertEqual(len(queue),1)
    def test_provider_retry_after_crash(self):
        pk=request_email("reader@example.com","a","b"); provider=DemoProvider()
        with self.assertRaises(RuntimeError):deliver(pk,provider,simulate_crash=True)
        self.assertEqual(Notification.objects.get(pk=pk).status,"pending")
        deliver(pk,provider)
        self.assertEqual(len(provider.accepted),1)
        self.assertEqual(Notification.objects.get(pk=pk).status,"accepted")
