import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from demo.models import Customer,Purchase
from demo.services import measure,capacity
customer,_=Customer.objects.get_or_create(name="demo-reader")
Purchase.objects.filter(customer=customer).delete()
Purchase.objects.bulk_create([Purchase(customer=customer,total="100") for _ in range(3)])
print(capacity(100000,20,.1,2000,365,5))
slow=measure(lambda:[p.customer.name for p in Purchase.objects.all()])
fast=measure(lambda:[p.customer.name for p in Purchase.objects.select_related("customer")])
print("queries: slow",slow["queries"],"optimized",fast["queries"])
