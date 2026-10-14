import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Room,Message
from .services import store_message,history
class ChatTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("member");self.other=User.objects.create_user("other")
        self.room=Room.objects.create();self.room.members.add(self.user)
    def test_retry_keeps_one_message_and_sequence(self):
        key=uuid.uuid4();a=store_message(self.room.pk,self.user.pk,key,"hello")
        b=store_message(self.room.pk,self.user.pk,key,"hello")
        self.assertEqual(a.pk,b.pk);self.assertEqual(Message.objects.count(),1)
        c=store_message(self.room.pk,self.user.pk,uuid.uuid4(),"next")
        self.assertEqual(c.seq,2)
        self.assertEqual([m.seq for m in history(self.room.pk,self.user.pk,1)],[2])
    def test_reused_key_with_different_text_is_rejected(self):
        key=uuid.uuid4();store_message(self.room.pk,self.user.pk,key,"hello")
        with self.assertRaises(ValueError):store_message(self.room.pk,self.user.pk,key,"changed")
    def test_nonmember_cannot_read_or_write(self):
        with self.assertRaises(PermissionError):store_message(self.room.pk,self.other.pk,uuid.uuid4(),"hello")
        with self.assertRaises(PermissionError):history(self.room.pk,self.other.pk)
        self.assertEqual(Message.objects.count(),0)
