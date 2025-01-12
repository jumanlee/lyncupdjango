import json
from annoy import AnnoyIndex
import numpy as np

#this function will load the cluster_{id}.ann and cluster_{id}_map.json files and pop up to batch_size users from the queue to form groups of 4 with greedy algo. Users who are leftovers (can't form a group) will be placed in a cluster queue, if still unmatched, will be placed in the global leftover queue. The batch_num represents the number to pop from this cluster’s queue.
def match_in_cluster(cluster_id, queue_manager, base_dir=None, batch_size=50, top_k=10):
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), "Annoy")

    try:
        with open(f"{base_dir}/cluster_{cluster_id}_map.json", "r") as f:
            map_data = json.load(f)
        feature_size = map_data["feature_size"]
        user_index_map = map_data["user_index_map"]
        index_user_map = map_data["index_user_map"]

        cluster_file = f"{base_dir}/cluster_{cluster_id}.ann"
        annoy_index = AnnoyIndex(feature_size, 'angular')
        annoy_index.load(cluster_file)

    except FileNotFoundError:
        print(f"cluster {cluster_id} not found.")
        return []
    
    groups_formed = []

    #tracker for the number of users processed
    processed = 0

    while queue_manager(cluster_id) >= 4 and processed < batch_size:
        user_entry = queue_manager.pop(cluster_id)
        if not user_entry:
            break
        processed += 1
        user_id = user_entry.user_id

        #try to get top-k from Annoy. if not in user_index map, then skip this user
        if int(user_id) not in user_index_map:
            continue

        user_index = user_index_map[int(user_id)]

        #when annoy is queried, the returned indices also include the queried item. So to mitigate that, have to to k+1 and exclude the first item. This returns a list.
        neigh_indices = annoy_index.get_nns_by_item(user_index, top_k+1)

        matched_entries = []
        while len(matched_entries) < 3 and neigh_indices:
            neigh_index = neigh_indices.pop(0)
            if index == user_index:
                continue
            #get the neighbour id
            neigh_id = int(index_user_map[int(neigh_index)])

            #get and pop this specific neighbour from the queue
            neigh_entry = pop_specific_user(queue_manager, cluster_id, neigh_id)
            if neigh_entry:
                matched_entries.append(neigh_entry)

        #if we can't find 3 neighbours from Annoy queue, then try to pick from other possible users from the same cluster, if any available.
        if len(matched_entries) < 3:
            num_leftover_users = 3 - len(matched_entries)
            found_cluster_users = random_cluster_pick(queue_manager, cluster_id)
            matched_entries.extend(found_cluster_users)

            #if still fail to find from cluster and no matches at all are found, then push all leftover users to global queue for cross cluster matching with other leftovers
            if len(matched_entries) < 3:
                #push all leftover users to global queue
                queue_manager.enqueue("global", user_id, user_entry.priority)
                for entry in matched_entries:

                

            





        
            








    


