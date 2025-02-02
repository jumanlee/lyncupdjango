import pytest
import jwt
from django.conf import settings
from channels.testing import WebsocketCommunicator
from channels.routing import ProtocolTypeRouter, URLRouter
from django.test import override_settings
from django.urls import path
from users.models import AppUser
from django.urls import re_path

from chat.consumers import GroupConsumer
from channels.db import database_sync_to_async


#application is an ASGI applicatiomn that acts as the entry point for handling incoming socket requests.
#ProtocolTypeRouter is the special routing class provided by Django Channels.
application = ProtocolTypeRouter(
    {
        # "websocket": URLRouter([path("ws/chat/somegroup", GroupConsumer.as_asgi())])
        "websocket": URLRouter([re_path(r"ws/chat/(?P<groupname>\w+)/$", GroupConsumer.as_asgi())])
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
    #does not get permanently saved in postgress database when use the db fixture in a test
    #run tests with pytest and the db fixture (provided by pytest-django), Django creates a temporary test database.
    #this database is completely separate from postgres.
    #IMPORTANT: Django ORM operations are not meant to run in async contexts directly because they rely on synchronous database connections. And because we are using a sync function within async test_valid_token(), therefore we need to use sync_to_async to run ORM operations in async contexts.
    #this is cuz websockets and consumers are naturally asynchronous. their bidirectional connection is only possible with asynchronous.

    @database_sync_to_async
    def create_test_user(email, username, password, firstname, lastname):
        return AppUser.objects.create_user(
        email=email,
        username=username,
        password=password,
        firstname=firstname,
        lastname=lastname,
    )

    test_user = await create_test_user("harry@123.com", "harrypotter", "12345", "Harry", "Potter")
    
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

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_can_send_and_receive_messages():

    @database_sync_to_async
    def create_test_user(email, username, password, firstname, lastname):
        return AppUser.objects.create_user(
        email=email,
        username=username,
        password=password,
        firstname=firstname,
        lastname=lastname,
    )
    
    test_user = await create_test_user("harry2@123.com", "hermionepotter", "12345", "Harry2", "Potter")

    token_data = {"user_id": test_user.id}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

    fake_frontend = WebsocketCommunicator(
        application, f"/ws/chat/somegroup/?token={token}"
    )

    #try to connect
    connected, subprotocol = await fake_frontend.connect()
    assert connected is True, "Unable to connect with valiud token"

    #skip the initial members update (see gorup consumer connection mthod)
    members_response = await fake_frontend.receive_json_from()
    assert "members" in members_response, "expected members update after connection"

    #try to send message to chatroom
    test_message = {"text": "Hello, everyone!"}
    await fake_frontend.send_json_to(test_message)

    #see if the user can see that message in the chatroom
    response = await fake_frontend.receive_json_from()
    expected_message = {"text": "Harry2 Potter: Hello, everyone!"}
    assert response == expected_message, "message not received or incorrect"

    #disconnect
    await fake_frontend.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_can_communicate_between_multiple_users():

    @database_sync_to_async
    def create_test_user(email, username, password, firstname, lastname):
        return AppUser.objects.create_user(
        email=email,
        username=username,
        password=password,
        firstname=firstname,
        lastname=lastname,
    )
    #create two users
    user1 = await create_test_user(email='fake1@123.com', username='fake1', password='test123', firstname='User', lastname='One')
    user2 = await create_test_user(email='fake2@123.com', username='fake2', password='test123', firstname='User', lastname='Two')

    #generate tokens for both users
    token1 = jwt.encode({'user_id': user1.id}, settings.SECRET_KEY, algorithm='HS256')
    token2 = jwt.encode({'user_id': user2.id}, settings.SECRET_KEY, algorithm='HS256')

    #first user connection
    communicator1 = WebsocketCommunicator(
        application,
        path=f"/ws/chat/testgroup/?token={token1}"
    )

    connected1, subprotocol1 = await communicator1.connect()
    assert connected1 is True, "User 1 unable to connect"

    
    #second user connection
    communicator2 = WebsocketCommunicator(
        application,
        path=f"/ws/chat/testgroup/?token={token2}"
    )

    connected2, subprotocol2 = await communicator2.connect()
    assert connected2 is True, "User 2 unable to connect"

    #first test user1 to user2
    await communicator1.send_json_to({"text": "Hello from User1!"})

    #upon connection each communicator receives the following, which needs to be skippped
    # {'members': [[4, 'User', 'Two'], [3, 'User', 'One']]}

    #need to use while loop to skip because all users in a channels group see every message including the sender’s own message. After the first message (“Hello from User1!”), user1 never actually read the echo from that message. So when user2 sends “Hello from User2!”, the first thing user1 reads is still “User One: Hello from User1!” left over in its redis queue.
    while True:
        response2 = await communicator2.receive_json_from()
        if "members" in response2:
            # skip membership updates
            continue
        if response2 == {"text": "User Two: Hello from User2!"}:
            continue
        # else we expect it's the actual chat message
        assert response2 == {"text": "User One: Hello from User1!"}
        break


    #then test user2 to user1
    await communicator2.send_json_to({"text": "Hello from User2!"})

    while True:
        response1 = await communicator1.receive_json_from()
        if "members" in response1:
            # skip membership updates
            continue
        if response1 == {"text": "User One: Hello from User1!"}:
            continue
        # else we expect it's the actual chat message
        assert response1 == {"text": "User Two: Hello from User2!"}
        break



    await communicator1.disconnect()
    # await communicator2.disconnect()






