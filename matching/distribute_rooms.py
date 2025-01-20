import random

#function to distribute rooms to users
def distribute_rooms(grouped_users: Dict[int, List['UserEntry']], redis_client
) -> Tuple[List[Dict[str, object]], List[int]]):
    # grouped_users in format of:
    # {2: [<__main__.UserEntry object at 0x1781f3ce0>, <__main__.UserEntry object at 0x1781f3aa0>, <__main__.UserEntry object at 0x1781f3200>, <__main__.UserEntry object at 0x1781f3c20>], 'global': []}


    matched_groups = []
    users_in_matched_groups = []
    #get the existing rooms being used now from Redis
    try:
        roomsSet = redis_client.smembers("rooms")
    except Exception as error:
        print(error)
        roomsSet = set()
    
    #first let's handle non-global users
    #keep getting a room id not being used now
    for cluster_id, group in grouped_users.items():
        if cluster_id == "global":
            continue
        #temporary solution, may change to more efficient sequential method for id allocation
        random_roomId = random.randint(1,10000)
        while str(random_roomId) in roomsSet:
            random_roomId = random.randint(1,10000)

        matched_group = {"room_id": random_roomId, "user_ids": []}
        
        for user_entry in group:
            matched_group["user_ids"].append(user_entry.user_id)
            users_in_matched_groups.append(user_entry.user_id)

        
        redis_client.sadd("rooms", str(random_roomId))
        roomsSet.add(str(random_roomId))

        matched_groups.append(matched_group)

    return matched_groups, users_in_matched_groups


    
    



