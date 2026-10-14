import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
from django.core.asgi import get_asgi_application
django_app=get_asgi_application()
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter,URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from demo.consumers import ChatConsumer
application=ProtocolTypeRouter({
    "http":django_app,
    "websocket":AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter([
        path("ws/rooms/<int:room_id>/",ChatConsumer.as_asgi()),
    ]))),
})
