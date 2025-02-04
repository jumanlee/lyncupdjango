import pytest
from unittest.mock import Mock
from matching.distribute_rooms import distribute_rooms
from matching.queue_manager import UserEntry
from matching.build_graph_annoy import create_graph_from_likes, create_node2vec_annoy
import pandas as pd

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




    
