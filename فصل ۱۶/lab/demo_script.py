import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

import uuid
from django.contrib.auth.models import User
from demo.models import Stock
from demo.services import checkout,publish_events
user,_=User.objects.get_or_create(username="demo-reader")
stock=Stock.objects.create(available=2);key=uuid.uuid4()
a=checkout(stock.pk,user.pk,1,key);b=checkout(stock.pk,user.pk,1,key)
queue=[];publish_events(queue.append);stock.refresh_from_db()
print("same order:",a.pk==b.pk,"remaining stock:",stock.available,"queue:",queue)
print("No payment or email was sent.")
