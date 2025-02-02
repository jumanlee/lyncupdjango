import pytest
from matching.queue_manager import ClusterQueueManager, UserEntry

'''
Test Queue Manager
'''
#this set of unit tests is to test the functionalities of the queue manager
def test_add_and_get_cluster_size():
    queue_manager = ClusterQueueManager()
    queue_manager.add("test_cluster", 1)
    queue_manager.add("test_cluster", 2)
    size = queue_manager.get_cluster_size("test_cluster")
    assert size == 2

def test_get_remove():
    queue_manager = ClusterQueueManager()
    queue_manager.add("test_cluster", 1)

    user_entry = queue_manager.get_remove("test_cluster", 1)

    #remove user 1 should return the UserEntry with user_id 1
    assert user_entry is not False
    assert user_entry.user_id == 1

    #remove again, should return false
    assert queue_manager.get_remove("test_cluster", 1) is False

def test_pop_random():
    queue_manager = ClusterQueueManager()
    queue_manager.add("test_cluster", 1)
    popped_entry = queue_manager.pop_random("test_cluster")
    assert popped_entry is not None

    #after this the cluster should be empty
    assert queue_manager.get_cluster_size("test_cluster") == 0


    

