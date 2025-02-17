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
import json


#import all the necessary functions for the matching algo
from matching.matching import match_in_cluster, run_batch_matching
from matching.distribute_rooms import distribute_rooms
from matching.queue_manager import ClusterQueueManager, UserEntry
from matching.build_graph_annoy import create_graph_from_likes, create_node2vec_annoy


logger = logging.getLogger(__name__)

#@shared_task decorator does not make the task available in all modules of project. 
#it only registers the task with Celery's task registry.
@shared_task
def build_graph_annoy():
        #get the directory of the current Python file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            
            #construct the full path to likes_df.csv
            likes_df = os.path.join(base_dir, "likes_df.csv")
            #use the global csv file path from settings
            likes_df = pd.read_csv(likes_df)
            #process the dataframe
            print("CSV File Loaded Successfully")

        except FileNotFoundError as e:
            print(f"File not found: {e}")
        except Exception as e:
            print(f"Error loading CSV files: {e}")

        # sample_df = likes_df.iloc[:int(len(likes_df) * 0.2)]

        #use the default base_dir
        create_node2vec_annoy(likes_df, embed_dimensions=128, num_trees=10)


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


    #ensuring user_ids are int
    try:
        user_ids = [int(member_id) for member_id in membersIdSet]
    except ValueError as error:
        print(error)
        user_ids = []

    # #users is in QuerySet, not yet hit the database
    # users = AppUser.objects.filter(id__in=user_ids)

    # #convert to list, this is when Queryset hits the database
    # users = list(users)

    if len(user_ids) < 2:
        return

    logger.info("user_ids length")
    logger.info(len(user_ids))

    #this automatically initialises "global" and "leftover" queues
    queue_manager = ClusterQueueManager()

    for user_id in user_ids:
        queue_manager.add("global", int(user_id))
    
    #run the batch matching algo
    grouped_users = run_batch_matching(queue_manager)
    print(f"grouped_users: {grouped_users}")
    
    #distribute grouped users to rooms
    #format of matched_groups
    # matched_groups = [{"room_id": 123, "user_ids": [1,2,3,4]}, {"room_id": 555, "user_ids": [5,6,7,8]}]
    matched_groups = distribute_rooms(grouped_users, redis_client)


    #remember when this is returned, it is a tuple as two values are returned!
    print(f"matched_groups: {matched_groups}")

    ##this needs amending for robustness
    removed_ids = redis_client.smembers("rooms")
    print(f"removed_ids: {removed_ids}")
    if removed_ids:
        redis_client.srem("rooms", *removed_ids)


    # get the channel layer
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
    #srem command removes one or more members from a set.
    #*unpacks the elements of the collection, so instead of passing the collection as one argument, it passes each element of the collection as a separate argument
    #here is to remove the successfully matched users from the Redis queue.
    redis_client.srem("queue",*success_matched_userIds)
            







