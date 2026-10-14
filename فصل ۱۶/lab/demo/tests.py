import uuid
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Stock,Order,OrderEvent
from .services import checkout,publish_events
class CapstoneTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("reader");self.stock=Stock.objects.create(available=2)
        self.key=uuid.uuid4()
    def test_replay_has_one_effect(self):
        a=checkout(self.stock.pk,self.user.pk,1,self.key);b=checkout(self.stock.pk,self.user.pk,1,self.key)
        self.assertEqual(a.pk,b.pk);self.stock.refresh_from_db()
        self.assertEqual(self.stock.available,1);self.assertEqual(OrderEvent.objects.count(),1)
    def test_event_failure_rolls_back_order_and_stock(self):
        with patch("demo.services.OrderEvent.objects.create",side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):checkout(self.stock.pk,self.user.pk,1,self.key)
        self.stock.refresh_from_db();self.assertEqual(self.stock.available,2)
        self.assertEqual(Order.objects.count(),0);self.assertEqual(OrderEvent.objects.count(),0)
    def test_publish_retry_contract(self):
        checkout(self.stock.pk,self.user.pk,1,self.key)
        def broken(message):raise RuntimeError("broker offline")
        with self.assertRaises(RuntimeError):publish_events(broken)
        self.assertIsNone(OrderEvent.objects.get().published_at)
        queue=[];self.assertEqual(publish_events(queue.append),1);self.assertEqual(publish_events(queue.append),0)
        self.assertEqual(len(queue),1)
