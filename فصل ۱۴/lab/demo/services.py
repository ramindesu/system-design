import uuid
from django.db import transaction
from .models import Video,ProcessingJob

def start_upload(user,max_size,storage):
    if not user.is_authenticated:raise PermissionError("login required")
    if type(max_size) is not int or not 1<=max_size<=500000000:raise ValueError("invalid size")
    video_id=uuid.uuid4();key=f"raw/{user.pk}/{video_id}.mp4"
    grant=storage.sign_upload(key,max_size)
    video=Video.objects.create(id=video_id,owner=user,object_key=key,max_size=max_size)
    return {"video_id":str(video.pk),"key":key,"upload":grant}

def finish_upload(video_id,user_id,storage):
    candidate=Video.objects.get(pk=video_id,owner_id=user_id)
    metadata=storage.head(candidate.object_key)
    if not 1<=metadata["size"]<=candidate.max_size:raise ValueError("size outside grant")
    with transaction.atomic():
        video=Video.objects.select_for_update().get(pk=video_id,owner_id=user_id)
        if video.status!="pending":return video.pk
        video.status="uploaded";video.generation=metadata["generation"]
        video.save(update_fields=["status","generation"])
        ProcessingJob.objects.get_or_create(video=video)
    return video.pk

def mark_ready(video_id,generation,manifest_key):
    if not isinstance(manifest_key,str) or not manifest_key or len(manifest_key)>300:
        raise ValueError("manifest key required")
    return Video.objects.filter(pk=video_id,generation=generation,status="uploaded").update(status="ready",manifest_key=manifest_key)==1

def playback_key(video_id,user_id):
    video=Video.objects.get(pk=video_id,owner_id=user_id)
    if video.status!="ready":raise ValueError("not ready")
    return video.manifest_key
