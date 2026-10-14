from django.conf import settings
from django.db import models, transaction

class DriveFile(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    version = models.PositiveBigIntegerField(default=1)
    blob_key = models.CharField(max_length=300)

class Revision(models.Model):
    file = models.ForeignKey(DriveFile, on_delete=models.CASCADE)
    version = models.PositiveBigIntegerField()
    blob_key = models.CharField(max_length=300)
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["file", "version"], name="unique_file_revision")]
