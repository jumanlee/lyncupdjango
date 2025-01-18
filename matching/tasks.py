from celery import shared_task
# from chat.utils import create_chat_room
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from users.models import AppUser
import redis
from django.conf import settings
import logging
import pandas as pd
import os


#import all the necessary functions for the matching algo
from matching.matching import match_in_cluster, run_batch_matching
from matching.queue_manager import ClusterQueueManager, UserEntry
from matching.build_clusters_annoy import create_similarity_matrix, create_clusters_and_annoy

logger = logging.getLogger(__name__)

#@shared_task decorator does not make the task available in all modules of project. 
#it only registers the task with Celery's task registry.
@shared_task
def build_clusters_annoy():
        try:
            # Get the directory of the current Python file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Construct the full path to likes_df.csv
            likes_df = os.path.join(base_dir, "likes_df.csv")
            # Use the global CSV file path from settings
            likes_df = pd.read_csv(likes_df)
            # Process the DataFrame
            print("CSV File Loaded Successfully")

        except FileNotFoundError as e:
            print(f"File not found: {e}")
        except Exception as e:
            print(f"Error loading CSV file: {e}")

        # likes_df = likes_df.iloc[:int(len(likes_df) * 0.2)]

        create_clusters_and_annoy(likes_df, 5, None)



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

    print("users.count() before conditon < 2")

    if users.count() < 2:
        return

    logger.info("users.count()")
    logger.info(users.count())
    # matched_groups = [
    #     {"chatroom_id": 123, "user_ids": [1, 2, 3, 4]},
    #     {"chatroom_id": 124, "user_ids": [5, 6, 7, 8]},
    #     ...
    # ]

    #just some dummy thing, i'm not concerned about the matching algo for now, just will input dummy data
    matched_groups = [{"room_id": 123, "user_ids": [3, 4]}]

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
            







