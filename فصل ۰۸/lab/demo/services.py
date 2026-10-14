from django.db import models, transaction
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect, Http404
from .encoding import base62

from .models import ShortLink

def create_link(target):
    URLValidator(schemes=["http", "https"])(target)
    if len(target) > 2000:
        raise ValueError("URL too long")
    with transaction.atomic(using="default"):
        link = ShortLink.objects.using("default").create(target=target)
        link.code = base62(link.pk)
        link.save(using="default", update_fields=["code"])
    return link

def redirect_link(request, code):
    try:
        link = ShortLink.objects.using("default").get(code=code)
    except ShortLink.DoesNotExist:
        raise Http404
    return HttpResponseRedirect(link.target)
