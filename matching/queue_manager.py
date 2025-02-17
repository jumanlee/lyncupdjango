import time

class UserEntry:
    def __init__(self, user_id):
        self.user_id = user_id

        self.joined_at = time.time()

    #define __eq__ and __hash__ to compare UserEntry objects by user_id, rather than requiring the same object reference (memory address).

    #__eq__ used to define how two objects of the UserEntry class are considered equal. It ensures logical equality based on the user_id attribute
    def __eq__(self, other):
        return isinstance(other, UserEntry) and self.user_id == other.user_id
    #making sure the unique identifier hash
    def __hash__(self):
        return hash(self.user_id)
    
#we will push UserEntry objects into it and pop them based on priority.
class ClusterQueueManager:
    def __init__(self):
        #the cluster id maps to the respective priority queue, implemented in list form.
        self.cluster_queues = {"global": set(), "leftover": set()}

    def add(self, cluster_id, user_id):
        if cluster_id not in self.cluster_queues:
            self.cluster_queues[cluster_id] = set()
        user_entry = UserEntry(user_id)
        self.cluster_queues[cluster_id].add(user_entry)
    
    def get_remove(self, cluster_id, user_id):
        if cluster_id not in self.cluster_queues:
            print(f"cluster {cluster_id} not found.")
            return False
        #even if don’t know the joined_at date, can still create a new UserEntry object with the same user_id to remove it from the set. This is cuz of overriden hash.
        user_entry = UserEntry(user_id)
        if user_entry in self.cluster_queues[cluster_id]:
            self.cluster_queues[cluster_id].remove(user_entry)
            return user_entry
        else:   
            print(f"user {user_id} not found in cluster {cluster_id}")
            return False

    def pop_random(self, cluster_id):
        if cluster_id not in self.cluster_queues or not self.cluster_queues[cluster_id]:
            print(f"Cluster {cluster_id} is empty or does not exist.")
            return None
        return self.cluster_queues[cluster_id].pop()

    def get_cluster_size(self, cluster_id):
        if cluster_id not in self.cluster_queues:
            return None
        return len(self.cluster_queues[cluster_id])

    def get_all_clusters(self):
        return list(self.cluster_queues.keys())





    



