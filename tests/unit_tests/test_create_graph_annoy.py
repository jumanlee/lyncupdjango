import os
import json
import pandas as pd
from matching.build_graph_annoy import create_graph_from_likes, create_node2vec_annoy

def test_create_graph_from_likes():
    #create dummy dataframe
    likes_data = {
        #columns: 
        "user_from": [1, 2, 3],
        "user_to":   [2, 3, 1],
        "like_count": [5, 10, 2]
    }

    likes_df = pd.DataFrame(likes_data)
    graph = create_graph_from_likes(likes_df, reciprocal_weight=0.5)

    #check the graph has forward edge (liking to other person)
    #user_from to user_to
    assert graph.has_edge(1,2)
    assert graph[1][2]["weight"] == 5

    #if user 1 likes user 2, but user 2 doesn't like user 1 back, we apply 0.5 to reduce weight
    #reminder: if 1 likes 2 but 2 doesn't like back, we would still add an edge from 2 to 1 but apply a 0.5 weight to weaken that edge, signalling that there's no reciprocity.
    assert graph.has_edge(2,1)
    assert graph[2][1]["weight"] == 5 * 0.5

def test_create_node2vec_annoy():

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Annoy")

    #check if base dir folder exists, if not, create it.
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    likes_data = {
        #columns: 
        "user_from": [1, 2, 3, 4],
        "user_to":   [2, 3, 1, 3],
        "like_count": [5, 10, 2, 5]
    }

    likes_df = pd.DataFrame(likes_data)

    #run the function
    create_node2vec_annoy(likes_df, base_dir=base_dir, embed_dimensions=128, num_trees=10)

    #check that the function has successfully created the annoy file and global map file.
    annoy_file = os.path.join(base_dir, "cluster_global.ann")
    global_map = os.path.join(base_dir, "global_map.json")


    assert os.path.exists(annoy_file)
    assert os.path.exists(global_map)

    #check if all the keys are present
    with open(global_map, "r") as f:
        map_data = json.load(f)
    assert "user_index_map" in map_data
    assert "index_user_map" in map_data
    assert "embed_dimensions" in map_data







    