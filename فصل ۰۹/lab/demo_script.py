import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from datetime import timedelta
from django.utils import timezone
from demo.models import CrawlJob
from demo.services import enqueue,claim_job,requeue_expired,complete_job
job=enqueue("https://example.com/demo#section")
CrawlJob.objects.filter(pk=job.pk).update(state="pending",claim_token=None,lease_until=None,priority=10000)
old=claim_job()
CrawlJob.objects.filter(pk=old["id"]).update(lease_until=timezone.now()-timedelta(seconds=1))
requeue_expired();new=claim_job()
print("old token accepted:",complete_job(old["id"],old["token"]))
print("new token accepted:",complete_job(new["id"],new["token"]))
print("No web pages were downloaded.")
