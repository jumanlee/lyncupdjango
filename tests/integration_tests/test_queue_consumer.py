import pytest
import jwt
from django.conf import settings
from channels.testing import WebsocketCommunicator
from channels.routing import ProtocolTypeRouter, URLRouter
from django.test import override_settings
from django.urls import path
from users.models import AppUser
from django.urls import re_path
from matching.consumers import QueueConsumer
from channels.db import database_sync_to_async


#application is an ASGI applicatiomn that acts as the entry point for handling incoming socket requests.
#if a request comes in for the WebSocket protocol, route it to this specific consumer. 
#ProtocolTypeRouter is the special routing class provided by Django Channels.
application = ProtocolTypeRouter(
    {
        # "websocket": URLRouter([path("ws/chat/somegroup", QueueConsumer.as_asgi())])
        "websocket": URLRouter([re_path(r"ws/chat/(?P<groupname>\w+)/$", QueueConsumer.as_asgi())])
    }
)
@pytest.mark.asyncio
#pytest disables pytest's database access for tests by default, so have to use the @pytest.mark.django_db decorator to enable it.
@pytest.mark.django_db
@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }
)

#test if a connection can be established with a valid token
async def test_valid_token():
    #create a user
    #does not get permanently saved in your postgress database when use the db fixture in a test
    #run tests with pytest and the db fixture (provided by pytest-django), Django creates a temporary test database.
    #this database is completely separate from postgres.
    #thats why we can use the default User model from Django, rather than the AppUser custom model
    #IMPORTANT: Django ORM operations are not meant to run in async contexts directly because they rely on synchronous database connections. And because we are using a sync function within async test_valid_token(), therefore we need to use sync_to_async to run ORM operations in async contexts.
    #this is cuz websockets and consumers are naturally asynchronous. their bidirectional connection is only possible with asynchronous.
    @database_sync_to_async
    def create_test_user():
        return AppUser.objects.create_user(
        email="testing2@testing.com",
        username="harrypotter2",
        password="testing2",
        firstname="Harry2",
        lastname="Potter2",
    )

    test_user = await create_test_user()
    
    #create jwt token for this user
    token_data = {"user_id": test_user.id}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

    #create a websocket communicator, it simulates a websocket client that connects to websocket server, sends messages, and receives responses. Essentially acts as the "frontend".
    fake_frontend = WebsocketCommunicator(
    application,
    f"/ws/chat/somegroup/?token={token}")

    #try to connect. subprotocol is usually none
    connected, subprotocol = await fake_frontend.connect()
    assert connected is True, "fails to connect with token"

    #close connection
    await fake_frontend.disconnect()

#ascertain that if given an invalid token, the system will not connect!
@pytest.mark.asyncio
@pytest.mark.django_db
async def test_with_invalid_token():
    
    token = "TellThemHowImDefyingGravity"

    #create a websocket communicator, it simulates a websocket client that connects to websocket server, sends messages, and receives responses. Essentially acts as the "frontend".
    fake_frontend = WebsocketCommunicator(
    application,
    f"/ws/chat/somegroup/?token={token}")

    #try to connect. subprotocol is usually none
    connected, subprotocol = await fake_frontend.connect()
    assert connected is False, "fails to connect with invalid token"

    #close connection
    await fake_frontend.disconnect()
