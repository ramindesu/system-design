from django.conf import settings
from django.db import models, transaction

from .models import Room, Message

def store_message(room_id, user_id, client_id, body):
    if not isinstance(body, str) or not 1 <= len(body) <= 4000:
        raise ValueError("invalid message")
    with transaction.atomic(using="default"):
        room = Room.objects.using("default").select_for_update().get(pk=room_id)
        if not room.members.using("default").filter(pk=user_id).exists():
            raise PermissionError("not a member")
        old = Message.objects.using("default").filter(
            room=room, sender_id=user_id, client_id=client_id).first()
        if old:
            if old.body != body:
                raise ValueError("client_id was reused with a different body")
            return old
        message = Message.objects.using("default").create(
            room=room, sender_id=user_id, client_id=client_id,
            seq=room.next_seq, body=body)
        room.next_seq += 1
        room.save(using="default", update_fields=["next_seq"])
        return message

def history(room_id,user_id,last_seq=0):
    if type(last_seq) is not int or last_seq < 0:raise ValueError("invalid cursor")
    room=Room.objects.get(pk=room_id)
    if not room.members.filter(pk=user_id).exists():raise PermissionError("not a member")
    return list(Message.objects.filter(room_id=room_id,seq__gt=last_seq).order_by("seq")[:100])
