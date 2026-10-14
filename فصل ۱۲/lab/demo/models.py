from django.conf import settings
from django.db import models, transaction

class Room(models.Model):
    next_seq = models.PositiveBigIntegerField(default=1)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL)

class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    client_id = models.UUIDField()
    seq = models.PositiveBigIntegerField()
    body = models.CharField(max_length=4000)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["room", "seq"], name="room_seq"),
            models.UniqueConstraint(fields=["room", "sender", "client_id"], name="message_retry"),
        ]
