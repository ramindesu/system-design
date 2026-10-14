import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from demo.services import request_email,publish_batch,DemoProvider,deliver
queue=[];pk=request_email("reader@example.com","Demo","Only an in-memory simulation")
publish_batch(queue.append);provider=DemoProvider()
try:deliver(pk,provider,simulate_crash=True)
except RuntimeError:print("simulated crash after provider acceptance")
deliver(pk,provider)
print("provider acceptance count:",len(provider.accepted),"queued events:",len(queue))
print("No email was sent.")
