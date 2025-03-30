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
from users.models import Like


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
            
            #retrieve the likes data from the database.
            likes_data = Like.objects.select_related("user_from", "user_to").all()

            likes_df = pd.DataFrame.from_records(likes_data.values("user_from_id", "user_to_id", "like_count"))

            if likes_df.empty:
                print("no Like data found in database.")
                return

            likes_df.rename(columns={
                "user_from_id": "user_from",
                "user_to_id": "user_to"
            }, inplace=True)


            print("Like data retrieved from database successfully.")

        except Exception as error:
            print(f"Error loading Like data: {error}")
            return

        #use the default base_dir
        create_node2vec_annoy(likes_df, embed_dimensions=128, num_trees=10)


@shared_task
def run_matching_algo():
    print("entered run matching algo")

    #check for Annoy directory and required files
    base_dir = os.path.join(os.path.dirname(__file__), "Annoy")
    ann_file = os.path.join(base_dir, "cluster_global.ann")
    json_file = os.path.join(base_dir, "global_map.json")

    #if ann file not found, skip the run_matcing_algo early
    if not (os.path.exists(base_dir) and os.path.exists(ann_file) and os.path.exists(json_file)):
        print("run_matching_algo() skipped as Annoy directory or required files missing.")
        return

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

    #to double check if these ids actually do exist.
    #users is in QuerySet, not yet hit the database
    users_queryset = AppUser.objects.filter(id__in=user_ids)

    #convert to list, this is when Queryset hits the database due to both list and values_list
    #flat true makes the tuples into plain list
    retrieved_user_ids = list(users_queryset.values_list('id', flat=True))
    print(f"users: {retrieved_user_ids}")

    #commented out to enable easier testing (using fewer users) in development mode. 
    #comment out in production mode!
    # if len(retrieved_user_ids) < 2:
    #     return

    logger.info("user_ids length")
    logger.info(len(retrieved_user_ids))

    #this automatically initialises "global" and "leftover" queues
    queue_manager = ClusterQueueManager()

    for user_id in retrieved_user_ids:
        queue_manager.add("global", int(user_id))
    
    #run the batch matching algo
    grouped_users = run_batch_matching(queue_manager)
    print(f"grouped_users: {grouped_users}")
    
    #distribute grouped users to rooms
    #format of matched_groups
    # matched_groups = [{"room_id": 123, "user_ids": [1,2,3,4]}, {"room_id": 555, "user_ids": [5,6,7,8]}]
    matched_groups, users_in_matched_groups = distribute_rooms(grouped_users, redis_client)


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

    # matched_groups in this format:
    #  Tuple[List[Dict[str, object]], List[int]]
    # [
    #     {"room_id": 5, "user_ids": [1, 2, 3, 4]},
    #     {"room_id": 2, "user_ids": [5, 6, 7, 8]}
    # ]


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
    #only remove if its not empty:
    if success_matched_userIds:
        print(f"success_matched_userIds is not empty:{success_matched_userIds}")
        redis_client.srem("queue",*success_matched_userIds)
            







