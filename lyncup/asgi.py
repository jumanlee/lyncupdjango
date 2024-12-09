"""
ASGI config for lyncup project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# import os
# import django
# from channels.routing import get_default_application
# from django.core.asgi import get_asgi_application


# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lyncup.settings')

# application = get_asgi_application()

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lyncup.settings")
# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# from chat.routing import websocket_urlpatterns

# Import websocket_urlpatterns with aliases to prevent conflicts
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from matching.routing import websocket_urlpatterns as matching_websocket_urlpatterns


combined_websocket_urlpatterns = chat_websocket_urlpatterns + matching_websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(combined_websocket_urlpatterns)
        ),
    }
)

# application = ProtocolTypeRouter(
#     {
#         "http": django_asgi_app,
#         "websocket": 
#             AuthMiddlewareStack(URLRouter(websocket_urlpatterns)
#         ),
#     }
# )
