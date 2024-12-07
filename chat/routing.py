#similar to url file but for websockets
from . import consumers
from django.urls import re_path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter


#this is the first point of contact as this is in the asgi file, which routes to the consumer
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<groupname>\w+)/$', consumers.GroupConsumer.as_asgi())
]

#this is necessary as we have JWT token in the consumers connect method, what this does is it routes WebSocket connections without additional middleware for authentication.
#application is defined in the asgi.py file, it knows this due to consumers.GroupConsumer.as_asgi() defined in websocket_urlpatterns.

# application = ProtocolTypeRouter({
#     'websocket': URLRouter(websocket_urlpatterns)
# })







# application = ProtocolTypeRouter({
#     'websocket': AuthMiddlewareStack(
#         URLRouter(websocket_urlpatterns)
#     ),
# })
