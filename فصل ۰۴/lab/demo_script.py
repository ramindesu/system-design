import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from demo.algorithms import TokenBucket
from demo.services import rate_limit_response
now=[0.0];bucket=TokenBucket(3,1,clock=lambda:now[0])
for i in range(4):
 response=rate_limit_response(bucket)
 print("request",i+1,"status",200 if response is None else response.status_code)
now[0]=1
print("after one second:",rate_limit_response(bucket) is None)
