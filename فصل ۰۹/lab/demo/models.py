import uuid
from django.db import models
class CrawlJob(models.Model):
    url=models.URLField(max_length=2000,unique=True)
    state=models.CharField(max_length=16,default="pending")
    priority=models.IntegerField(default=0)
    lease_until=models.DateTimeField(null=True)
    claim_token=models.UUIDField(null=True)
    class Meta:
        indexes=[models.Index(fields=["state","-priority","id"])]
