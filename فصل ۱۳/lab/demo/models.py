import hashlib
import unicodedata
from django.db import models
from django.core.cache import cache

class Suggestion(models.Model):
    term = models.CharField(max_length=200)
    normalized = models.CharField(max_length=200, unique=True)
    score = models.PositiveBigIntegerField(default=0)
