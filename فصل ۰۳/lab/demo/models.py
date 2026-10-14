from django.conf import settings
from django.db import models
class Inventory(models.Model):
    available = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(available__gte=0), name="nonnegative_stock")]
class Reservation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    request_id = models.UUIDField(unique=True)
