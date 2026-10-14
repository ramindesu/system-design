import uuid
from urllib.parse import urlsplit,urlunsplit
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import CrawlJob

def enqueue(url):
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname!="example.com" or p.username or p.password or p.port not in (None,443):
        raise ValueError("only https://example.com is allowed in this lab")
    canonical=urlunsplit(("https","example.com",p.path or "/",p.query,""))
    if len(canonical)>2000:raise ValueError("URL too long")
    return CrawlJob.objects.get_or_create(url=canonical)[0]

def claim_job():
    with transaction.atomic():
        job=CrawlJob.objects.select_for_update(skip_locked=True).filter(state="pending").order_by("-priority","id").first()
        if job is None:return None
        job.state="running"; job.claim_token=uuid.uuid4(); job.lease_until=timezone.now()+timedelta(minutes=2)
        job.save(update_fields=["state","claim_token","lease_until"])
        return {"id":job.pk,"url":job.url,"token":job.claim_token}

def complete_job(job_id, token):
    return CrawlJob.objects.filter(pk=job_id,state="running",claim_token=token,lease_until__gt=timezone.now()).update(state="done",lease_until=None)==1

def requeue_expired():
    return CrawlJob.objects.filter(state="running",lease_until__lte=timezone.now()).update(state="pending",claim_token=None,lease_until=None)
