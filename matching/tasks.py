from celery import shared_task
# from chat.utils import create_chat_room
from asgiref.sync import async_to_sync
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
    try:
        #retrieve the likes data from the database.
        #note: may have to combine .iterator() + batching (stream and chunk) to balance speed and memory when user count gets into the millions as using df like this loads everything into memory.
        likes_data = Like.objects.select_related("user_from", "user_to").all()

        likes_df = pd.DataFrame.from_records(likes_data.values("user_from_id", "user_to_id", "like_count"))

        if likes_df.empty:
            logger.info("No Like data found in database. Injecting dummy data for testing.")

            #inject dummy likes from 3 users
            dummy_data = {
                "user_from": [1, 1, 2],
                "user_to":   [2, 3, 3],
                "like_count": [1, 3, 2]
            }
            likes_df = pd.DataFrame(dummy_data)
        else:
            #Rename columns if real data is used
            likes_df.rename(columns={
                "user_from_id": "user_from",
                "user_to_id": "user_to"
            }, inplace=True)


        logger.info("Like data retrieved successfully.")

    except Exception as error:
        logger.error("Error loading Like data: %s", error)
        return

    #use the default base_dir
    create_node2vec_annoy(likes_df, embed_dimensions=128, num_trees=10)


@shared_task
def run_matching_algo():

    #check for Annoy directory and required files
    base_dir = os.path.join(settings.BASE_DIR, "matching", "Annoy")
    ann_file = os.path.join(base_dir, "cluster_global.ann")
    json_file = os.path.join(base_dir, "global_map.json")

    #if ann file not found, skip the run_matcing_algo early
    if not (os.path.exists(base_dir) and os.path.exists(ann_file) and os.path.exists(json_file)):
        logger.warning(
            "run_matching_algo skipped: Annoy directory or required files missing."
        )
        return

    #connect to Redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    #when multiple celery workers are used: added a lock (via SETNX) to prevent two Celery workers from running run_matching_algo() at the same time. Otherwise, risk double-matching or room assignment conflicts under concurrency.

    lock_key = "run_matching_algo_lock"
    lock_ttl = 60  # seconds; adjust to max expected runtime

    #NX = "Only set lock if Not eXists"
    #EX = set an expiration time for the lock
    # If the key did not exist, Redis executes the SET key value NX EX ttl command and returns the string reply "OK".
    # If the key already exists, the NX flag prevents the set, and Redis returns a nil reply (i.e. “no value”)
    got_lock = redis_client.set(lock_key, "1", nx=True, ex=lock_ttl)
    if not got_lock:
        logger.info("Another worker is already running run_matching_algo; skipping this round.")
        return
    
    try:
        logger.info("run_matching_algo started")

        #get all user id's in queue in redis
        # redis_client.smembers("queue") returns strings because Redis stores everything as strings by default, even if insert numbers.
        try:
            membersIdSet = redis_client.smembers("queue")
        except Exception as error:
            logger.error("Error fetching queue members: %s", error)
            membersIdSet = set()

        if not membersIdSet:
            logger.debug("Queue is empty—nothing to match.")
            return

        #ensuring user_ids are int
        try:
            user_ids = [int(member_id) for member_id in membersIdSet]
        except ValueError as error:
            logger.error("Non-integer ID in queue: %s", error)
            user_ids = []

        #to double check if these ids actually do exist.
        #users is in QuerySet, not yet hit the database
        users_queryset = AppUser.objects.filter(id__in=user_ids)

        #convert to list, this is when Queryset hits the database due to both list and values_list
        #flat true makes the tuples into plain list
        retrieved_user_ids = list(users_queryset.values_list('id', flat=True))
        logger.info("Found %d valid users in queue", len(retrieved_user_ids))

        #commented out to enable easier testing (using fewer users) in development mode. 
        #comment out in production mode!
        if len(retrieved_user_ids) < 2:
            logger.debug("Not enough users to match.")
            return


        #this automatically initialises "global" and "leftover" queues
        queue_manager = ClusterQueueManager()

        for user_id in retrieved_user_ids:
            queue_manager.add("global", int(user_id))
        
        #run the batch matching algo
        grouped_users = run_batch_matching(queue_manager)
        logger.debug("Grouped users: %s", grouped_users)
        
        #distribute grouped users to rooms
        #format of matched_groups
        # matched_groups = [{"room_id": 123, "user_ids": [1,2,3,4]}, {"room_id": 555, "user_ids": [5,6,7,8]}]
        matched_groups, users_in_matched_groups = distribute_rooms(grouped_users, redis_client)


        #remember when this is returned, it is a tuple as two values are returned!
        logger.info("Matched groups: %s", matched_groups)

        # ##this needs amending for robustness
        # removed_ids = redis_client.smembers("rooms")
        # print(f"removed_ids: {removed_ids}")
        # if removed_ids:
        #     redis_client.srem("rooms", *removed_ids)


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
                    logger.error("Error sending to user %d: %s", user_id, error)
        #srem command removes one or more members from a set.
        #*unpacks the elements of the collection, so instead of passing the collection as one argument, it passes each element of the collection as a separate argument
        #here is to remove the successfully matched users from the Redis queue.
        #only remove if its not empty:
        if success_matched_userIds:
            redis_client.srem("queue",*success_matched_userIds)
            logger.info("Removed matched users from queue: %s", success_matched_userIds)
            
    finally:
        #use finally as we NEED to delete the lock even if an error occurs. Finally executes no matter what.
        #release the lock so others can pick up next time
        redis_client.delete(lock_key)
        logger.info("run_matching_algo completed, lock released.")


            







