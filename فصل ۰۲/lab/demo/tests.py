from django.test import TestCase
from .models import Customer, Purchase
from .services import measure, capacity
class EstimationTests(TestCase):
    def test_units(self):
        result = capacity(100000, 20, .1, 2000, 365, 5)
        self.assertAlmostEqual(result["read_qps"], 23.148148, places=6)
        self.assertEqual(result["raw_storage_bytes"], 7300000000)
    def test_query_growth_and_join(self):
        customer = Customer.objects.create(name="Reader")
        Purchase.objects.bulk_create([Purchase(customer=customer, total="100.00") for _ in range(3)])
        slow = measure(lambda: [p.customer.name for p in Purchase.objects.all()])
        fast = measure(lambda: [p.customer.name for p in Purchase.objects.select_related("customer")])
        self.assertEqual(slow["queries"], 4)
        self.assertEqual(fast["queries"], 1)
        self.assertEqual(slow["result"], fast["result"])
