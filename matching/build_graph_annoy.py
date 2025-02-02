import pandas as pd
import json
from annoy import AnnoyIndex
from scipy.sparse import csr_matrix
from sklearn.cluster import KMeans
import os
from node2vec import Node2Vec
import networkx as nx

#this function builds a directede graph from likes_df 
#if there is a directed edge from user A to user B but no edge from user B to user A, the script creates that missing reverse edge and assigns it 0.5 of the original weight. This means if there’s no reciprocity (if user B didn’t like user A back), the algorithm weakens the link by adding only a fraction of the original weight in the reverse direction.

def create_graph_from_likes(likes_df, reciprocal_weight=0.5):

    graph = nx.DiGraph()

    #graph structure is as follows:
    # {
    #     1: {2: {'weight': 5}},   #node 1 to node 2 (weight 5)
    #     2: {3: {'weight': 10}},  
    #     3: {}  
    # }

    all_edges = set()
    #iterrows() is from dataframe outputs (index, row) pairs.
    #keep track of all forward edges
    for i, row in likes_df.iterrows():
        all_edges.add((row.user_from, row.user_to))

    for i, row in likes_df.iterrows():
        #from node
        u = row.user_from
        #to node
        v = row.user_to
        #weight
        w = float(row.like_count)

        #add edge, or increase weight if already exists
        if graph.has_edge(u, v):
            graph[u][v]['weight'] += w
        else:
            #this will also automatically create nodes
            graph.add_edge(u, v, weight=w)

        if (v,u) not in all_edges:
            if graph.has_edge(v, u):
                graph[v][u]['weight'] += w*reciprocal_weight
            else:
                graph.add_edge(v, u, weight=w*reciprocal_weight)

    return graph

#embed_dimensions is the number of dimensions in the embedding space
#num_trees is the number of trees in the Annoy index
#this will build graph from likes_df, then run node2vec to get the embeddings and then builds a single annoy index (no clusters for now) and then save the annoy index and user_index_map for retrieval to base_dir Anooy folder.
def create_node2vec_annoy(likes_df, base_dir=None, embed_dimensions=128, num_trees=10):

    if likes_df.empty:
        print("likes_df is empty")
        return

    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Annoy")

    #check if base dir folder exists, if not, create it.
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    graph = create_graph_from_likes(likes_df, reciprocal_weight=0.5)
    print("graph created, now running node2vec")

    node2vec = Node2Vec(
        graph,
        dimensions=embed_dimensions,
        walk_length=10,
        num_walks=20,
        p=1.0,
        q=1.0, #1.0 and 1.0 is effectively deepwalk, use this for now
        weight_key="weight",
        workers=1 #this can be increase for parallele processing
    )

    print("carrying out fitting skip-gram model")
    model = node2vec.fit(window=5, min_count=1, batch_words=4)

    user_list = sorted(graph.nodes())
    num_users = len(user_list)

    print(f"total users/nodes in the graph: {num_users}")

    annoy_index = AnnoyIndex(embed_dimensions, metric="angular")

    user_index_map = {}
    index_user_map = {}

    #add each user's embedding to Annoy 
    for i, user_id in enumerate(user_list):

        #.wv stands for word vecotrs. it stores all the learned embeddings (vectors) for each node. embeddings/vectors are much like coordinates in the vector space. .wv is an object that stores all the learned embeddings and n2v_model.wv[str(user_id)] is how to retrieve a specific embedding from it. #Note: .wv is automatically created when run node2vec.fit(), therefore already exists.

        user_vector = model.wv[str(user_id)] #model keys are strings
        annoy_index.add_item(i, user_vector)

        #note that annoy requires incremental index values to retrieve users.

        #record the user_id that maps to the index
        user_index_map[str(user_id)] = int(i)
        #record the reverse, the index that maps to user_id
        index_user_map[str(i)] = int(user_id)

    print("building annoy index...")
    annoy_index.build(num_trees)

    #save files
    annoy_file_path = os.path.join(base_dir, "cluster_global.ann")
    #save the annoy file to Annoy folder
    annoy_index.save(annoy_file_path)

    map_info = {
        "user_index_map": user_index_map,
        "index_user_map": index_user_map,
        "embed_dimensions": int(embed_dimensions)
    }

    # with open(os.path.join(base_dir, "global_map_info.json"), "w") as f:
    #     json.dump(map_info, f)

    with open(f"{base_dir}/global_map.json", "w") as f:
            json.dump(map_info, f)

    print(f"global annoy and map info created in {base_dir}.")





    

    




        
        
        

 








        




