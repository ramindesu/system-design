"""Small educational algorithms. No production cluster management is implied."""
import hashlib
import math
import threading
import time
from bisect import bisect_left


def capacity(dau, reads_per_user, writes_per_user, bytes_per_write, days, peak_factor=3):
    if min(dau, reads_per_user, writes_per_user, bytes_per_write, days) < 0 or peak_factor < 1:
        raise ValueError("counts must be nonnegative and peak_factor >= 1")
    writes_daily = dau * writes_per_user
    return {
        "read_qps": dau * reads_per_user / 86400,
        "write_qps": writes_daily / 86400,
        "peak_read_qps": dau * reads_per_user / 86400 * peak_factor,
        "raw_storage_bytes": writes_daily * bytes_per_write * days,
    }


class TokenBucket:
    """One process only; monotonic clock and a lock prevent local refill races."""
    def __init__(self, capacity, rate, clock=time.monotonic):
        if capacity <= 0 or rate <= 0:
            raise ValueError("positive capacity/rate required")
        self.capacity, self.rate, self.clock = capacity, rate, clock
        self.tokens, self.last = float(capacity), clock()
        self.lock = threading.Lock()

    def take(self):
        with self.lock:
            now = self.clock()
            self.tokens = min(self.capacity, self.tokens + max(0, now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True, 0
            return False, math.ceil((1 - self.tokens) / self.rate)


def stable_hash(text):
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest(), "big")


class HashRing:
    def __init__(self, nodes, replicas=64):
        nodes = sorted(set(nodes))
        if not nodes or replicas <= 0:
            raise ValueError("nonempty nodes and positive replicas required")
        self.points = sorted((stable_hash(f"{node}:{i}"), node) for node in nodes for i in range(replicas))
        self.positions = [point for point, _ in self.points]

    def owner(self, key):
        index = bisect_left(self.positions, stable_hash(key)) % len(self.points)
        return self.points[index][1]


class Snowflake:
    """A single live instance per worker_id; reject rollback and sequence exhaustion."""
    EPOCH = 1704067200000  # 2024-01-01 UTC

    def __init__(self, worker_id, clock_ms=None):
        if not 0 <= worker_id < 1024:
            raise ValueError("worker_id must fit 10 bits")
        self.worker_id = worker_id
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self.last, self.sequence = -1, 0
        self.lock = threading.Lock()

    def next_id(self):
        with self.lock:
            stamp = self.clock_ms() - self.EPOCH
            if stamp < self.last:
                raise RuntimeError("clock moved backwards")
            if not 0 <= stamp < 2**41:
                raise RuntimeError("timestamp out of range")
            sequence = self.sequence + 1 if stamp == self.last else 0
            if sequence >= 4096:
                raise RuntimeError("sequence exhausted: wait for the next millisecond")
            self.last, self.sequence = stamp, sequence
            return (stamp << 22) | (self.worker_id << 12) | sequence


def base62(number):
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if number < 0:
        raise ValueError("nonnegative integer required")
    if number == 0:
        return "0"
    chars = []
    while number:
        number, remainder = divmod(number, 62)
        chars.append(alphabet[remainder])
    return "".join(reversed(chars))
