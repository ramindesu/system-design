from django.conf import settings
from django.db import models, transaction

from .models import DriveFile, Revision

class SyncConflict(Exception):
    pass

def publish_revision(file_id, user_id, expected_version, verified_key):
    with transaction.atomic(using="default"):
        file = DriveFile.objects.using("default").select_for_update().get(
            pk=file_id, owner_id=user_id)
        if file.version != expected_version:
            raise SyncConflict(file.version)
        Revision.objects.using("default").get_or_create(
            file=file, version=file.version,
            defaults={"blob_key": file.blob_key})
        file.version += 1
        file.blob_key = verified_key
        file.save(using="default", update_fields=["version", "blob_key"])
        Revision.objects.using("default").create(
            file=file, version=file.version, blob_key=verified_key)
    return file.version
