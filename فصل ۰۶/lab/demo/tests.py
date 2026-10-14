from django.test import TestCase
from .models import Entry
from .services import compare_and_set, clock_relation
class KVTests(TestCase):
    def test_stale_snapshot_cannot_overwrite(self):
        Entry.objects.create(key="book:1",value={"likes":10})
        self.assertTrue(compare_and_set("book:1",1,{"likes":11}))
        self.assertFalse(compare_and_set("book:1",1,{"likes":99}))
        item=Entry.objects.get(key="book:1")
        self.assertEqual((item.version,item.value),(2,{"likes":11}))
    def test_missing_key_and_clock_conflict(self):
        self.assertFalse(compare_and_set("missing",1,{}))
        self.assertEqual(clock_relation({"A":3,"B":1},{"A":2,"B":2}),"concurrent")
        self.assertEqual(clock_relation({"A":2},{"A":3}),"before")
        self.assertEqual(clock_relation({"A":2},{"A":2,"B":0}),"equal")
