import json 
import jwt
from users.models import AppUser
from django.conf import settings
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as redis
from urllib.parse import parse_qs

class GroupConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("entered connect method")

        #connect to the Redis
        # self.redis = await aioredis.create_redis_pool(settings.REDIS_URL)
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

        #self.scope is a dict object which contains metadata about the incoming client connection such as headers, query string, path, etc . query_string is part of the metadata in self.scope. Since "query_string" is expected to be a byte string, the default value is also a byte string (b"") to maintain consistency.

# scope.get("key", default_value)
# key: The key you want to retrieve (e.g., "query_string").
# default_value: A fallback value to return if the key does not exist in the dictionary.
        #decode so that it becomes string now for easier processing, this will need to be encded back later to bytes
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        print(f"Query string: {query_string}") 

#example query_string: "token=abcd1234&room_name=general"

        query_params = parse_qs(query_string)
        # query_params will be:
        # {
        #     "token": ["abc123"],
        # }
        token = query_params.get("token", [None])[0]

        if token:

            #get user
            try:
                user = await self.get_token_user(token)

                if not user:
                    print("Invalid user")
                    await self.close(code=4123)
                    return

                #By setting self.scope["user"] = user, we are linking the authenticated user to this WebSocket connection. This makes it easy to access the user information later in the code for this connection. 
                #self.scope is a buiklt in property of AsyncWebsocketConsumer
                self.scope["user"] = user

                #save the first name and last name of the user to scope
                self.scope["firstname"] = user.firstname
                self.scope["lastname"] = user.lastname

                # self.groupname is defined on the fly
                # By setting self.groupname once during initialisation we can refer to self.groupname throughout the code without repeatedly diving into the nested structure of self.scope.
                self.groupname = self.scope['url_route']['kwargs'].get('groupname')
                if not self.groupname:
                    print("No group name provided")
                    await self.close(code=4123)
                    return

                #add the WebSocket connection to the groupname. self.channel_name  is the WebSocket connection.
                await self.channel_layer.group_add(
                    self.groupname,
                    self.channel_name 
                    #channel_name is automatically generated by Django Channels for each WebSocket connection
                    #this is like: take this specific WebSocket connection (self.channel_name) and add it to the group (self.groupname).
                )

                #to accept the incoming WebSocket connection from React
                await self.accept()

                #risk of race conditions: when for example multiple users connect at nearly the same time, there's a chance that one user's update might miss another user's data if the timing isn't perfect. May have to implement lock_key = f"lock:members:{self.groupname}" later
                await self.add_and_update_member_list()

            except Exception as error:
                print(error)
                await self.close(code=4123)

        else:
            print("No token provided, closing connection")
            await self.close(code=4123)
            return

    async def disconnect(self, disconnect_code):
        try:
            if hasattr(self, 'groupname') and self.groupname:
                await self.channel_layer.group_discard(
                    self.groupname,
                    self.channel_name
                )

            else:
                print("No groupname to discard")

            await self.remove_and_update_member_list()

            #must close redis for this consumer instance
            if self.redis:
                await self.redis.aclose()

        except Exception as error:
            print(error)

    #The receive method sends a message to the Redis group.
    #Django Channels expects the receive method to have this signature:
    #async def receive(self, text_data=None, bytes_data=None):
    #IMPORTANT: cannot rename text_data, must be as they are stated in the documentation
    #coded based on documentation: https://channels.readthedocs.io/en/latest/topics/consumers.html

    async def receive(self, text_data):

        #message_json comes in form of: {"text": "...", "user": "John"}
        #convert to python dict
        message_dict = json.loads(text_data)
        #check for error
        # if 'text' not in message_dict or 'firstname' not in message_dict or 'lastname' not in message_dict:
        #     raise ValueError("Invalid data received")

        text = message_dict['text']

        firstname = self.scope["user"].firstname
        lastname = self.scope["user"].lastname

        try:
            await self.channel_layer.group_send(
                self.groupname,
                {
                    #type key in this dictionary specifies the name of the method that Django Channels should call when this event is received by a consumer in the group. The type method takes in "event" as parameter.
                    'type': 'handle_message',
                    'text': text,
                    'firstname': firstname,
                    'lastname': lastname
                }
            )
            
        except Exception as error:
            print("error in receive method")
            print(error)

    #this is for adding new member to the member list sent to React for display. This is used in connect().
    async def add_and_update_member_list(self):
        #risk of race conditions: when for example multiple users connect and using redis at nearly the same time, there's a chance that one user's update might miss another user's data if the timing isn't perfect. Have to implement redis_lock is that only one instance, even across multiple processes, is executing the block at a time. This prevents two connections from trying to read and broadcast the member list concurrently.
        redis_lock = f"redislock:members:{self.groupname}"

        #we are using "async with" to lock Redis while updating it, so two users don’t update at the same time. this is like "opening a door and making sure it's closed when I leave". async with starts something before the block runs, cleans it up after the block finishes.
        #redis lock based on code taken from: https://compileandrun.com/redis-distrubuted-locks-with-heartbeats/
        async with self.redis.lock(redis_lock, timeout=5):
            try:
                #saved members into Redis for each chatroom, this will be sent to each member in the chatroom to let them know all members in the chatroom.
                await self.redis.sadd(
                    self.groupname,
                    json.dumps([
                        self.scope["user_id"],
                        self.scope["firstname"],
                        self.scope["lastname"]
                    ])
                )
                #the list of members in this groupname from Redis
                #this returns a set! 
                membersSet = await self.redis.smembers(self.groupname)
                #convert back to json object from the returned Set
                decoded_members = [json.loads(member) for member in membersSet]
                #format is: [[1, "Mary", "HadALittleLamb"], [2, "Jane", "Monster"], ...]
            except Exception as error:
                print(error)
                membersSet = set() #default to empty set

            # decoded_members = [member.decode('utf-8') for member in membersByteString]

            try:
                await self.channel_layer.group_send(
                    self.groupname,
                    {
                        #type key in this dictionary specifies the name of the method that Django Channels should call when this event is received by a consumer in the group. The type method takes in "event" as parameter.
                        'type': 'handle_members',
                        'members': decoded_members,
                    }
                )
                
            except Exception as error:
                print("error in send")
                print(error)

    #similar to add_and_update_member_list() but removing user instead of adding. this is for when user leaves the chatroom. Used in disconnect.
    async def remove_and_update_member_list(self):
        redis_lock = f"redislock:members:{self.groupname}"
        async with self.redis.lock(redis_lock, timeout=5):
            #remember redis.exists is async function, must call await!
            if await self.redis.exists(self.groupname):
                await self.redis.srem(self.groupname, json.dumps([
                        self.scope["user_id"],
                        self.scope["firstname"],
                        self.scope["lastname"]
                    ]))

            try:
                #check what's left in Redis
                membersSet = await self.redis.smembers(self.groupname)
                print("whats left in Redis:")
                print(membersSet)
                #convert back to json object from the returned Set
                decoded_members = [json.loads(member) for member in membersSet]
                #format is: [[1, "Mary", "HadALittleLamb"], [2, "Jane", "Monster"], ...]
            except Exception as error:
                print(error)
                membersSet = set() #default to empty set

        # decoded_members = [member.decode('utf-8') for member in membersByteString]

            try:
                await self.channel_layer.group_send(
                    self.groupname,
                    {
                        #type key in this dictionary specifies the name of the method that Django Channels should call when this event is received by a consumer in the group. The type method takes in "event" as parameter.
                        'type': 'handle_members',
                        'members': decoded_members,
                    }
                )
                
            except Exception as error:
                print("error in send")
                print(error)

            #if no one is left in the group, we must delete the groupname from Redis user tracking
            if not membersSet:
                await self.redis.delete(self.groupname)

    #this is used by receive method ( a built in method in consumer class) to retrieve the broadcasted message from the Redis group and send the message to the websocket client so the message appears in the chat interface.
    #the reason why its event here is cuz this is something that is sent by .channel_layer.group_send
    async def handle_message(self, event):
        text = event['text']
        firstname = event['firstname']
        lastname = event['lastname']

        #self.channel_layer.group_send is not enough on its own because it only sends the event to the Redis channel layer or the group, not directly to the WebSocket client. Thats why we need self.send.
        #self.send method is part of Django channels and is inherited from the AsyncWebsocketConsumer class
        await self.send(text_data=json.dumps({
            'text': f"{firstname} {lastname}: {text}"
        }))

    async def handle_members(self, event):
        members = event['members']

        await self.send(text_data=json.dumps({
            'members': members
        }))


    #the decorator converts sychronouse function to asynchronous, more suitable for WebSocket.
    @database_sync_to_async
    def get_token_user(self, token):

        print("entered get_token_user method")

        try:

            data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            print(data)

            self.scope["user_id"] = data['user_id']

            return AppUser.objects.get(id=data['user_id'])

        except jwt.ExpiredSignatureError:
            print("Token has expired")
            return None
        except Exception as error:
            print(error)
            return None