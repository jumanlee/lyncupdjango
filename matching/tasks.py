from celery import shared_task
# from chat.utils import create_chat_room
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from users.models import AppUser
import redis
from django.conf import settings


@shared_task
def run_matching_algo():

    #connect to Redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)



    #get all user id's in queue in redis
    try:
        membersIdSet = redis_client.smembers("queue")
    except Exception as error:
        print(error)
        membersIdSet = set()

    if not membersIdSet:
        print("queue is empty (from task.py)")
        return


    #convert the string ids to int
    try:
        user_ids = [int(member_id) for member_id in membersIdSet]
    except ValueError as error:
        print(error)
        user_ids = []

    users = AppUser.objects.filter(id__in=user_ids)

    # matched_groups = [
    #     {"chatroom_id": 123, "user_ids": [1, 2, 3, 4]},
    #     {"chatroom_id": 124, "user_ids": [5, 6, 7, 8]},
    #     ...
    # ]

    #just some dummy thing, i'm not concerned about the matching algo for now, just will input dummy data
    matched_groups = [{"room_id": 123, "user_ids": [1, 2]}]

    #get the channel layer
    channel_layer = get_channel_layer()

    success_matched_userIds = []

    for group in matched_groups:
        room_id = group["room_id"]
        user_ids = group["user_ids"]

        for user_id in user_ids:
            try:
                async_to_sync(channel_layer.group_send)(
                    f'user_queue_{user_id}',
                    {
                        #Note: When Celery task sends a message via the channel layer, it doesn't need direct access to the consumer or its methods. Instead, it uses the channel layer as an intermediary to broadcast messages to any consumers that are subscribed to the relevant group.
                        "type": "send_room_id",
                        "room_id": room_id,
                    }
                )

                success_matched_userIds.append(user_id)

                
            except Exception as error:
                print(error)

        redis_client.srem("queue",*success_matched_userIds)
            







