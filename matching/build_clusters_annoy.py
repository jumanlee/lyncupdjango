import pandas as pd
import json
from annoy import AnnoyIndex
from scipy.sparse import csr_matrix
from sklearn.cluster import KMeans
import os

#this set of algos are for pre-computing annoy index for each K-means cluster so that we don't have to calculate top-k neighbours in real time

#this will generate a similarity matrix based on the likes_df
def create_similarity_matrix(likes_df, reciprocal_weight=0.5):

    if likes_df.empty:
        return {}, csr_matrix((0,0))

    #get unique users and create a mapping to indices
    # user_list = likes_df['user_from'].unique()
    user_list = pd.concat([likes_df['user_from'], likes_df['user_to']]).unique()
    #sort based on numerical order. remember, this is user IDs
    user_list = sorted(user_list)
    #creating user_index_map for easy and quick retrieval of index number of users. even when the user id is integer, we would still need a mapping. This is cuz they can be  large or sparse as a matrix requires 0-based row/column indices. Mapping the userI to smaller indices here is more practical.
    user_index_map = {}
    for i in range(len(user_list)):
        user_index_map[int(user_list[i])] = int(i)

 

    #initialise sparse matrix lists
    row_indices = []
    col_indices = []
    data = []

    #pre-compute reciprocal pairs in the first loop check (second loop check is below)
    reciprocal_pairs = set()
    #using iterrows() is inefficient for large DataFrames, consider changing.
    for i, row in likes_df.iterrows():
        reciprocal_pairs.add((row['user_from'], row['user_to']))

    #fill in the matrix with reciprocity check using set lookup
    for i, row in likes_df.iterrows():
        from_index = user_index_map[row['user_from']]
        to_index = user_index_map[row['user_to']]
        
        #original "Like"
        #a value at position (i, j) means there is a relationship from i (row) to j (column). I'm using row to represent from_index and col to represent to_index, then the coordinate that holds the value is the like count for the said relationship.
        row_indices.append(from_index)
        col_indices.append(to_index)
        data.append(row['like_count'])
        
        #second recip loop check: add reduced weighted reciprocal if not in reciprocal pairs
        if (row['user_to'], row['user_from']) not in reciprocal_pairs:
            row_indices.append(to_index)
            col_indices.append(from_index)
            data.append(row['like_count']* reciprocal_weight)
    
    #create sparse like matrix
    #social graphs can be extremely sparse, most users don’t “like” most others, it’s more memory efficient to build a sparse matrix. Returning a sparse matrix is better idea to avoid big exponential memory spikes. Better to build sparse, then convert to dense only when needed for Annoy. More importantly, this allows me to only build dense matrix, which is huge in memory, only for the cluster that I am working on. This keeps eadch cluster's memory usage low.
    like_matrix_sparse = csr_matrix((data, (row_indices, col_indices)), shape=(len(user_list), len(user_list)))
    return user_index_map, like_matrix_sparse

    print("create_similarity_matrix done")

#this will use the create_similarity_matrix above to convert likes_df and then build a user to user matrix from likes_df. Then it will cluster users to segment them into smaller groups. Then, for each cluster, it will build an annoy index. Then it will save the annoy index along with the user_id mappings to a file.
def create_clusters_and_annoy(likes_df, n_clusters=5, base_dir=None):
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Annoy")

    #like_matrix_sparse will be converted to dense
    user_index_map, like_matrix_sparse = create_similarity_matrix(likes_df)

    #convert to dense matrix
    dense_matrix = like_matrix_sparse.toarray()
    #get number of rows from dense_matrix
    num_users = dense_matrix.shape[0]

    if num_users == 0:
        return
        
    #clusters number specified from argument should not exceed num_users as can't create more clusters than there are data points
    if n_clusters > num_users:
        n_clusters = num_users

    #clustering users using K-means
    #Kmeans is straightforward and computationally less demanding, but it might not capture complex patterns in the data effectively for high-dimensional or sparse data. However, for the purpose of this project, Kmeans is used for simplicity.
    kmeans = KMeans(n_clusters=n_clusters, random_state=45)
    kmeans.fit(dense_matrix)
    cluster_labels = kmeans.labels_

# dense_matrix = [
#     [1.0, 0.8, 0.2],  user 0
#     [0.8, 1.0, 0.5],  user 1
#     [0.2, 0.5, 1.0],  user 2
   
#cluster_labels data structure:
#https://scikit-learn.org/1.5/modules/generated/sklearn.cluster.KMeans.html
#cluster_labels = [0, 0, 1, 0] index 2 (user) has cluster_label of 1


    #create reverse map
    #IMPORTANT: we needed the user_index_map to build the sparse matrix but we need index_user_map to build the clusters and annoy index. This is because the annoy index is built on the user index, not the user id. When building an annoy index, you provide numerical indices (like 0, 1, 2) for each vector. These indices correspond to positions in the annoy index, not the real world user IDs.
    index_user_map = {int(value): int(key) for key, value in user_index_map.items()}

    #create clusters for users
    clusters = {}
    for i in range(num_users):
        user_id = index_user_map[i]
        cluster_id = cluster_labels[i]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(user_id)

    #create annoy index for each cluster
    for cluster_id, user_ids in clusters.items():
        user_ids = clusters[cluster_id]

        #filter likes_df to keep only rows where both 'user_from' and 'user_to' are in the cluster
        #why use AND and not OR in if row['user_from'] in user_ids and row['user_to'] in user_ids:
        #first, keep in mind why we are breaking data into clusters in the first place:
        #k-means uses the full NxN user-user matrix of all likes to assign each user to a cluster. This clustering step already captures global relationships, like A and B both liking C, even if C is in a different cluster. However, once the clusters are finalised, I want to build a local Annoy index for each cluster that only includes users and interactions within that cluster. If I include edges where 'user_from' is inside the cluster but 'user_to' is outside (using "or"),the cluster-specific index would no longer represent a clean sub-graph of the cluster. Instead, it would include partial edges referencing users in other clusters, which defeats the purpose of having neat, self-contained sub-graphs. By restricting to 'user_from IN cluster AND user_to IN cluster', I ensure the resulting sub-matrix is a clean NxN block for the cluster. This makes the Annoy index memory-efficient and ensures that nearest-neighbor searches are focused solely on users within the cluster. In other words, the local step is to sieve out the interactions FURTHER, if there is any. K-means already does the similarity grouping step globally. By sieving out further locally, this allows a smaller Annoy index and dense matrix to be built.
        sub_likes = []
        for i, row in likes_df.iterrows():
            if row['user_from'] in user_ids and row['user_to'] in user_ids:
                sub_likes.append(row)

        #convert to dataframe
        sub_likes = pd.DataFrame(sub_likes)

        if sub_likes.empty:
            print(f"cluster {cluster_id} has no valid user interactions.. skipping.")
            continue

        sub_user_index_map, sub_like_matrix_sparse = create_similarity_matrix(sub_likes)
        sub_like_matrix_dense = sub_like_matrix_sparse.toarray()

        #.shape returns (number of rows, number of columns)
        sub_num_users, feature_size = sub_like_matrix_dense.shape

        if sub_num_users < 1 or feature_size < 1:
            continue
        
        annoy_index = AnnoyIndex(feature_size, 'angular')

        for row_i in range(sub_num_users):
            annoy_index.add_item(row_i, sub_like_matrix_dense[row_i])
        annoy_index.build(10)

        #save annoy index to file
        file_path = f"{base_dir}/cluster_{cluster_id}.ann"
        annoy_index.save(file_path)

        #also save the sub map and the reverse map
        rev_map = {value: key for key, value in sub_user_index_map.items()}

        map_info = {
            "user_index_map": sub_user_index_map,
            "index_user_map": rev_map,
            "feature_size": feature_size
        }

        with open(f"{base_dir}/cluster_{cluster_id}_map.json", "w") as f:
            json.dump(map_info, f)


    #also save the user to cluster assignment mapping
    #e.g. cluster_labels = [0, 1, 0]  #cluster ids for indices 0, 1, and 2

    user_clusters = {}
    for i in range(num_users):
        user_id = index_user_map[i]
        user_clusters[user_id] = int(cluster_labels[i])

    with open(f"{base_dir}/user_clusters.json", "w") as f:
        json.dump(user_clusters, f)
        
    print(f"built {len(clusters)} cluster indexes in {base_dir}.")

        
        
        

 








        




