import uuid
from django.conf import settings
from django.db import models
class Video(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    object_key=models.CharField(max_length=300,unique=True)
    max_size=models.PositiveBigIntegerField()
    generation=models.CharField(max_length=100,blank=True)
    status=models.CharField(max_length=16,default="pending")
    manifest_key=models.CharField(max_length=300,blank=True)
class ProcessingJob(models.Model):
    video=models.OneToOneField(Video,on_delete=models.CASCADE)
    state=models.CharField(max_length=16,default="pending")
