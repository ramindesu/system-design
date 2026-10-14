from django.db import models, transaction
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect, Http404
from .encoding import base62

class ShortLink(models.Model):
    target = models.URLField(max_length=2000)
    code = models.CharField(max_length=22, unique=True, null=True)
