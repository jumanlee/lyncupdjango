import random
from typing import Dict, Tuple, List

#function to distribute rooms to users
def distribute_rooms(grouped_users: Dict[str, List['UserEntry']], redis_client
) -> Tuple[List[Dict[str, object]], List[int]]:
    # grouped_users in format of:
    # {2: [[<__main__.UserEntry object at 0x1781f3ce0>, <__main__.UserEntry object at 0x1781f3aa0>, <__main__.UserEntry object at 0x1781f3200>, <__main__.UserEntry object at 0x1781f3c20>]], 'global': []}

    matched_groups = []
    users_in_matched_groups = []

    #no need try catch block with .incr() as it will create the key if it does not exist, won't throw error. incr() already returns an int, so int(...) is redundant.
    #note "last_room_id" is stored in a Redis string, not a set, list, hash, or anything else, unlike what we have done with the queue. 
    #if last_room_id doesn't already exist, it will be 0 automatically
    last_room_id = redis_client.incr("last_room_id")

    #keep getting a room id not being used now
    for cluster_id, groups_in_cluster in grouped_users.items():
        # if cluster_id == "leftover":
        #     continue

        for group in groups_in_cluster:
            # atomic counter to prevent race conditions. If "last_room_id" doesn’t exist in Redis, Redis will create it with value 0, then increment result to 1, if "last_room_id" already exists, Redis increments the existing integer by 1.
            new_room_id = redis_client.incr("last_room_id")  

            matched_group = {"room_id": new_room_id, "user_ids": []}
            
            for user_entry in group:
                matched_group["user_ids"].append(user_entry.user_id)
                users_in_matched_groups.append(user_entry.user_id)

            matched_groups.append(matched_group)

    #need to handle leftover users still
    # ...

    return matched_groups, users_in_matched_groups


    
    



