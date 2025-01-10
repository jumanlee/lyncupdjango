import heapq
import time

class UserEntry:
    def __init__(self, user_id, priority=1.0):
        self.user_id = user_id

        self.priority = priority
        self.joined_at = time.time()
    
    #need to define how heapq compares, by default it will compare based on minheap, and because we need maxheap, we will reverse the lt (less than) comparison. This is standard practice in python heapq.
    def __ lt__(self, other):
        if self.priority == other.priority:
        #compare by joined_at if priorities are the same
            return self.joined_at < other.joined_at
        return self.priority > other.priority

#this one will create a separate priority queue for each cluster. 
#we will push UserEntry objects into it and pop them based on priority.
class ClusterQueueManager:
    def __init__(self):
        #the cluster id maps to the respective priority queue, implemented in list form.
        self.cluster_queues = {}

    def enqueue(self, cluster_id, user_id, priority=1.0):
        if cluster_id not in self.cluster_queues:
            self.cluster_queues[cluster_id] = []
        user_entry = UserEntry(user_id, priority)
        heapq.heappush(self.cluster_queues[cluster_id], user_entry)

    def pop(self, cluster_id):
        if cluster_id not in self.cluster_queues or not self.cluster_queues:
            return None
        #this pops the user at the tip of the heap
        return heapq.heappop(self.cluster_queues[cluster_id])

    def requeue(self, cluster_id, user_entry, boost=0.5):
        user_entry.priority += boost
        heapq.heappush(self.queues[cluster_id], user_entry)

    def get_cluster_size(self, cluster_id):
        return len(self.cluster_queues[cluster_id], [])

    def get_all_clusters(self):
        return list(self.cluster_queues.keys())





    



