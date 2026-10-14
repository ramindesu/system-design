import uuid
from django.db import models, transaction

from .models import Notification, Outbox

def request_email(recipient, subject, body):
    with transaction.atomic(using="default"):
        item = Notification.objects.using("default").create(
            recipient=recipient, subject=subject, body=body)
        Outbox.objects.using("default").create(notification=item)
    return item.pk

from django.utils import timezone

def publish_batch(publish):
    events=list(Outbox.objects.filter(published_at__isnull=True).order_by("created_at")[:100])
    for event in events:
        publish(str(event.notification_id))
        Outbox.objects.filter(pk=event.pk,published_at__isnull=True).update(published_at=timezone.now())
    return len(events)

class DemoProvider:
    """In-memory provider simulator; no email or network is used."""
    def __init__(self): self.accepted={}
    def send(self, key, recipient, subject, body):
        payload=(recipient,subject,body)
        if key in self.accepted and self.accepted[key]!=payload:
            raise ValueError("idempotency key payload mismatch")
        self.accepted[key]=payload
        return key

def deliver(notification_id, provider, simulate_crash=False):
    item=Notification.objects.get(pk=notification_id)
    if item.status=="accepted":return item.pk
    provider.send(str(item.pk),item.recipient,item.subject,item.body)
    if simulate_crash:raise RuntimeError("crash after provider accepted")
    Notification.objects.filter(pk=item.pk).update(status="accepted")
    return item.pk
