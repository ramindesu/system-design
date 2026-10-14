import uuid
from django.conf import settings
from django.db import models
class Stock(models.Model):
    available=models.PositiveIntegerField(default=0)
class Order(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    stock=models.ForeignKey(Stock,on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField()
    request_id=models.UUIDField(unique=True)
class OrderEvent(models.Model):
    order=models.OneToOneField(Order,on_delete=models.PROTECT)
    published_at=models.DateTimeField(null=True)
