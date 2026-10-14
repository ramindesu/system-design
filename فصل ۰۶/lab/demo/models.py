from django.db import models
from django.db.models import F

class Entry(models.Model):
    key = models.CharField(max_length=200, primary_key=True)
    value = models.JSONField()
    version = models.PositiveBigIntegerField(default=1)
