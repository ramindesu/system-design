import uuid
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from .models import Room
from .services import store_message

class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_id=self.scope["url_route"]["kwargs"]["room_id"]
        user=self.scope["user"]
        if not user.is_authenticated or not Room.objects.filter(pk=self.room_id,members=user).exists():
            self.close(code=4403);return
        self.group=f"room.{self.room_id}"
        async_to_sync(self.channel_layer.group_add)(self.group,self.channel_name)
        self.accept()

    def receive_json(self,content):
        if not isinstance(content,dict):self.send_json({"error":"object required"});return
        try:
            key=uuid.UUID(content["client_id"])
            message=store_message(self.room_id,self.scope["user"].pk,key,content["body"])
        except (KeyError,ValueError,TypeError,AttributeError,PermissionError):
            self.send_json({"error":"invalid or unauthorized message"});return
        payload={"seq":message.seq,"client_id":str(message.client_id),"body":message.body}
        self.send_json({"ack":payload})
        async_to_sync(self.channel_layer.group_send)(self.group,{"type":"chat.message","payload":payload})

    def chat_message(self,event):
        if Room.objects.filter(pk=self.room_id,members=self.scope["user"]).exists():
            self.send_json({"message":event["payload"]})
        else:self.close(code=4403)

    def disconnect(self,code):
        if hasattr(self,"group"):
            async_to_sync(self.channel_layer.group_discard)(self.group,self.channel_name)
