from django.test import SimpleTestCase
from django.core.cache import caches
from .algorithms import HashRing
from .services import ShardedCache
class RingTests(SimpleTestCase):
    def setUp(self):
        for alias in ("cache-a","cache-b","cache-c","cache-d"): caches[alias].clear()
    def test_membership_order_is_stable(self):
        a=HashRing(["cache-a","cache-b"]); b=HashRing(["cache-b","cache-a"])
        self.assertEqual([a.owner(str(i)) for i in range(100)], [b.owner(str(i)) for i in range(100)])
    def test_added_node_only_takes_new_range(self):
        a=HashRing(["cache-a","cache-b"]); b=HashRing(["cache-a","cache-b","cache-c"])
        changes=[str(i) for i in range(1000) if a.owner(str(i)) != b.owner(str(i))]
        self.assertTrue(changes)
        self.assertTrue(all(b.owner(k)=="cache-c" for k in changes))
    def test_removed_node_only_moves_its_keys(self):
        a=HashRing(["cache-a","cache-b","cache-c"]); b=HashRing(["cache-a","cache-c"])
        for i in range(1000):
            if a.owner(str(i)) != b.owner(str(i)): self.assertEqual(a.owner(str(i)),"cache-b")
    def test_django_cache_destination(self):
        client=ShardedCache(["cache-a","cache-b"])
        client.set("book:1", {"price":"150"})
        self.assertEqual(client.get("book:1"),{"price":"150"})
        owner=client.ring.owner("book:1")
        other="cache-b" if owner=="cache-a" else "cache-a"
        self.assertIsNone(caches[other].get("book:1"))
