from io import BytesIO
from django.test import TestCase
from django.contrib.auth.models import User
from .models import DriveFile,Revision
from .services import publish_revision,SyncConflict
from .blocks import iter_blocks
class DriveTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user("owner");self.other=User.objects.create_user("other")
        self.file=DriveFile.objects.create(owner=self.owner,name="notes",blob_key="blob/v1")
    def test_revision_history_and_conflict(self):
        self.assertEqual(publish_revision(self.file.pk,self.owner.pk,1,"blob/v2"),2)
        with self.assertRaises(SyncConflict):publish_revision(self.file.pk,self.owner.pk,1,"blob/wrong")
        self.file.refresh_from_db();self.assertEqual(self.file.blob_key,"blob/v2")
        self.assertEqual(list(Revision.objects.order_by("version").values_list("blob_key",flat=True)),["blob/v1","blob/v2"])
    def test_owner_enforced(self):
        with self.assertRaises(DriveFile.DoesNotExist):publish_revision(self.file.pk,self.other.pk,1,"blob/v2")
        self.assertEqual(Revision.objects.count(),0)
    def test_changed_middle_block(self):
        a=list(iter_blocks(BytesIO(b"aabbcc"),2));b=list(iter_blocks(BytesIO(b"aazzcc"),2))
        self.assertEqual([x[1]==y[1] for x,y in zip(a,b)],[True,False,True])
        self.assertEqual(b"".join(row[2] for row in a),b"aabbcc")
