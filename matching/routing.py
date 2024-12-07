#similar to url file but for websockets
from . import consumers
from django.urls import re_path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter


#this is the first point of contact as this is in the asgi file, which routes to the consumer
websocket_urlpatterns = [
    re_path(r'ws/queue/', consumers.QueueConsumer.as_asgi())
]

