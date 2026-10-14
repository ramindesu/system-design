import unittest
from algorithms import HashRing, Snowflake, TokenBucket, base62, capacity


class AlgorithmTests(unittest.TestCase):
    def test_capacity_units(self):
        result = capacity(86400, 20, 2, 1000, 30)
        self.assertEqual(result["read_qps"], 20)
        self.assertEqual(result["write_qps"], 2)
        self.assertEqual(result["raw_storage_bytes"], 5_184_000_000)

    def test_bucket_burst_and_refill(self):
        now = [0.0]
        bucket = TokenBucket(2, 1, clock=lambda: now[0])
        self.assertEqual(bucket.take(), (True, 0))
        self.assertEqual(bucket.take(), (True, 0))
        self.assertEqual(bucket.take(), (False, 1))
        now[0] = 0.5
        self.assertEqual(bucket.take(), (False, 1))
        now[0] = 1
        self.assertEqual(bucket.take(), (True, 0))

    def test_added_node_only_takes_its_own_new_keys(self):
        old, new = HashRing(["a", "b"]), HashRing(["a", "b", "c"])
        moved = 0
        for i in range(1000):
            key = str(i)
            if old.owner(key) != new.owner(key):
                moved += 1
                self.assertEqual(new.owner(key), "c")
        self.assertGreater(moved, 0)
        self.assertLess(moved, 1000)

    def test_snowflake_uniqueness_and_order(self):
        now = [Snowflake.EPOCH + 100]
        gen = Snowflake(3, clock_ms=lambda: now[0])
        ids = [gen.next_id() for _ in range(4096)]
        self.assertEqual(len(set(ids)), 4096)
        self.assertEqual(ids, sorted(ids))
        with self.assertRaises(RuntimeError):
            gen.next_id()
        now[0] += 1
        self.assertGreater(gen.next_id(), ids[-1])
        now[0] -= 2
        with self.assertRaises(RuntimeError):
            gen.next_id()

    def test_workers_and_base62(self):
        clock = lambda: Snowflake.EPOCH + 100
        self.assertNotEqual(Snowflake(1, clock).next_id(), Snowflake(2, clock).next_id())
        self.assertEqual(base62(0), "0")
        self.assertEqual(base62(62), "10")
        for n in (1, 61, 10000, 2**63-1):
            code = base62(n)
            value = 0
            for char in code:
                value = value * 62 + "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ".index(char)
            self.assertEqual(value, n)


if __name__ == "__main__":
    unittest.main()
