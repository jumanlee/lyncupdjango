from matching.matching import run_batch_matching
import os
import json
from matching.matching import match_in_cluster
from matching.queue_manager import ClusterQueueManager, UserEntry
from matching.distribute_rooms import distribute_rooms
from annoy import AnnoyIndex
from test_create_graph_annoy import test_create_node2vec_annoy
from matching.build_graph_annoy import create_graph_from_likes, create_node2vec_annoy
import pandas as pd
from typing import Dict, Tuple, List
import pytest
from unittest.mock import Mock


@pytest.fixture
# how to code mock redis: https://docs.python.org/3/library/unittest.mock.html
# https://stackoverflow.com/questions/65519905/mock-redis-for-writing-unittest-for-application
def test_redis():
    test_redis = Mock()

    #when smembers("rooms") is called, 
    #reminder: in distribute_rooms.py, "rooms" is called and added to this test redis: 
    #     try:
    #       roomsSet = redis_client.smembers("rooms")
        # except Exception as error:
        #     print(error)
        #     roomsSet = set()
    
    test_redis.smembers.return_value = {"123"}
    #no matter what argument is passed to smembers, return {"123"}, just a mock.
    #note: mocks don’t work like real dictionaries or databases. They don't validate keys! Instead, they simulate behaviour without checking what keys exist. Took me a while to realise.
    #{"123"} is only used inside distribute_rooms to check which room ids are already taken
    return test_redis


def test_match_in_cluster():
    #make sure all the necessary Annoy and map files are in place
    test_create_node2vec_annoy()

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Annoy")
    #check that the function has successfully created the annoy file and global map file.
    annoy_file = os.path.join(base_dir, "cluster_global.ann")
    global_map = os.path.join(base_dir, "global_map.json")
    assert os.path.exists(annoy_file)
    assert os.path.exists(global_map)

    queue_manager = ClusterQueueManager()

    #we currenlty only have 1 cluster called "global", which makes sense as the number of users aren't yet huge.
    queue_manager.add("global", 1)
    queue_manager.add("global", 2)
    queue_manager.add("global", 3)
    queue_manager.add("global", 4)

    groups = match_in_cluster("global", queue_manager, base_dir=base_dir, batch_size=50, top_k=20)

    #as per the function, groups is a list, each group must have at least 3 members up to 4 members
    assert isinstance(groups, list)
    for group in groups:
        assert len(group) >= 3
        assert len(group) <= 4

#batch matching tries to match those in each cluster, in our case here, only the global cluster, then match the leftover members.
#now that test_match_in_cluster() has passed and works with small dummy data, we now want to test the run_batch_matching function AND test it with a HUGE dataset, with 1 million "like" interactions between 10,000 users. We'll also stress test it with a high user number load.
def test_run_batch_matching_with_big_data():

    #get the csv
    current_folder = os.path.dirname(os.path.abspath(__file__))
    likes_data_path = os.path.join(current_folder, "likes_df.csv")
    assert os.path.exists(likes_data_path)
    likes_df = pd.read_csv(likes_data_path)

    # #uncomment for fast testing alternative, can just use 10% of the data, if not wanting to wait
    # likes_df = likes_df.iloc[:int(0.10*len(likes_df))]

    print(f"the size of likes_df is {len(likes_df)}")

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Annoy")

    #create the Annoy and json map file with the big data csv
    create_node2vec_annoy(likes_df, base_dir=base_dir, embed_dimensions=128, num_trees=10)

    #check that the function has successfully created the annoy file and global map file.
    annoy_file = os.path.join(base_dir, "cluster_global.ann")
    global_map = os.path.join(base_dir, "global_map.json")
    assert os.path.exists(annoy_file)
    assert os.path.exists(global_map)

    queue_manager = ClusterQueueManager()

    #add 500 user ids into global cluster. In likes_df csv, I've deliverately used user_ids in incremental integer values. I created this csv with python script.
    for user_id in range(1, 3000):
        queue_manager.add("global", user_id)

    res = run_batch_matching(queue_manager, base_dir=base_dir, batch_size=3000)

    #check there is correct number of entries
    assert "global" in res
    global_groups = res["global"]
    for group in global_groups:
        assert len(group) >= 3
        assert len(group) <= 4

    assert "leftover" in res
    leftover_groups = res["leftover"]
    for group in global_groups:
        assert len(group) >= 3
        assert len(group) <= 4

    #check that the output is in the form of -> Dict[str, List[List[UserEntry]]] e.g. {global: [[userEntry, userEntry]], "leftover": [[userentry, userEntry]]}

    assert isinstance(res, dict), "res should be a dictionary"

    #check if global and leftover keys exist
    assert "global" in res, "global key is missing in res"
    assert "leftover" in res, "leftover key is missing in res"

    #checke values are lists of lists
    assert all(isinstance(group, list) for group in res["global"]), "'global' should contain a list of lists"
    assert all(isinstance(group, list) for group in res["leftover"]), "'leftover' should contain a list of lists"

    #check elements inside lists are instances of UserEntry
    for group in res["global"]:
        assert all(isinstance(user, UserEntry) for user in group), "Not all elements in 'global' are UserEntry objects"

    for group in res["leftover"]:
        assert all(isinstance(user, UserEntry) for user in group), "Not all elements in 'leftover' are UserEntry objects"


    #would only show if run with pytest -s
    print(f"output of test_run_batch_matching_with_big_data: {res}")

#test distribute rooms functionality with a mock redis and some small dummy data
def test_distribute_rooms_with_mock_and_small_data(test_redis):
    user1 = UserEntry(1)
    user2 = UserEntry(2)

    grouped_users = {"global": [[user1, user2]]}
    matched_groups, users_in_matched_groups = distribute_rooms(grouped_users, test_redis)

    #check the results
    assert len(matched_groups) == 1
    group = matched_groups[0]
    assert "room_id" in group
    assert "user_ids" in group
    assert set(group["user_ids"]) == {1, 2} #use set cuz order should not matter!

    #check that the list of users are in matched groups
    assert 1 in users_in_matched_groups
    assert 2 in users_in_matched_groups

    #check that necessary functions have been called
    test_redis.smembers.assert_called_once_with("rooms")
    test_redis.sadd.assert_called_once()

    #get the first positional arguments tuple from the last called of test_redis.sadd()
    #e.g. redis_client.sadd("rooms", str(random_roomId))

    assert test_redis.sadd.call_args[0][0] == "rooms"
    print(f"room id is: {test_redis.sadd.call_args[0][1]}")

#we are going to test with likes_df.csv, which contains 1 million like interactions among 10,000 users, we will stress test with a high user load in the queue.
def test_distribute_rooms_with_mock_and_big_data(test_redis):
    #get the annoy related files
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Annoy")
    #check that the function has successfully created the annoy file and global map file.
    annoy_file = os.path.join(base_dir, "cluster_global.ann")
    global_map = os.path.join(base_dir, "global_map.json")
    assert os.path.exists(annoy_file), f"missing Annoy file at {annoy_file}"
    assert os.path.exists(global_map), f"missing global map file at {global_map}"

    queue_manager = ClusterQueueManager()

    #add 500 user ids into global cluster. In likes_df csv, I've deliverately used user_ids in incremental integer values. I created this csv with python script.
    for user_id in range(1, 3000):
        queue_manager.add("global", user_id)

    res = run_batch_matching(queue_manager, base_dir=base_dir, batch_size=3000)

    matched_groups, users_in_matched_groups = distribute_rooms(res, test_redis)

    assert isinstance(matched_groups, list), "matched_groups should be a list"

    for group in matched_groups:
        assert "room_id" in group, "each room must have a room_id"
        assert "user_ids" in group, "each room must have a user_ids list"
        #check group sizes match matching constraints of 3 or 4 users per room
        assert len(group["user_ids"]) <= 4, "room group size must be between 3 and 4"
        assert len(group["user_ids"]) >= 3, "room group size must be between 3 and 4"

    #check if all user ids collected match the ones output by distribute_rooms
    all_user_ids_from_res = set()
    for cluster in res.values():
        for group in cluster:
            for user_entry in group:
                all_user_ids_from_res.add(user_entry.user_id)

    assert set(users_in_matched_groups) == all_user_ids_from_res, "collected all_user_ids_from_res does not match users_in_matched_groups from distribute_rooms"

    #check redis.sadd was called at least once per group created
    output_calls = len(matched_groups)
    redis_calls = test_redis.sadd.call_count
    assert output_calls >= redis_calls, "output_calls >= redis_calls NOT TRUE"

    #check if the outputs are in the form of: Tuple[List[Dict[str, object]], List[int]]
    #first element: check matched_groups is a list of dicts 
    assert isinstance(matched_groups, list)
    for group in matched_groups:
        assert isinstance(group, dict)
        assert "room_id" in group
        assert "user_ids" in group

    #second element: check users_in_matched_groups is a list of integers (all users)
    assert isinstance(users_in_matched_groups, list)
    for user_id in users_in_matched_groups:
        assert isinstance(user_id, int)








    




    












