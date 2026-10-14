from django.test import SimpleTestCase
from .algorithms import TokenBucket
from .services import rate_limit_response
class LimiterTests(SimpleTestCase):
    def test_burst_refill_and_http_response(self):
        now=[0.0]
        bucket=TokenBucket(3,1,clock=lambda:now[0])
        for _ in range(3): self.assertIsNone(rate_limit_response(bucket))
        rejected=rate_limit_response(bucket)
        self.assertEqual(rejected.status_code,429)
        self.assertEqual(rejected["Retry-After"],"1")
        now[0]=.5
        self.assertEqual(rate_limit_response(bucket).status_code,429)
        now[0]=1
        self.assertIsNone(rate_limit_response(bucket))
    def test_refill_stops_at_capacity(self):
        now=[0.0]; bucket=TokenBucket(2,1,clock=lambda:now[0])
        now[0]=100
        self.assertTrue(bucket.take()[0]); self.assertTrue(bucket.take()[0])
        self.assertFalse(bucket.take()[0])
