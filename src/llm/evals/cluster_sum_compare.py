from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, v_measure_score
from typing import List
from pathlib import Path

from src.cluster.types import ClusteredTopic
from src.cluster.cluster import (
    generate_full_code_clusters, 
    generate_graph_clusters, 
    generate_summarized_clusters
)

def eval_clusters_similarity(golden_cluster: List[ClusteredTopic], eval_cluster: List[ClusteredTopic]):
    """
    Evaluate two sets of clusters for similarity
    
    :param golden_cluster: Golden standard clusters
    :param eval_cluster: Clusters to evaluate
    """
    # Extract cluster labels
    golden_labels = [i for i, cluster in enumerate(golden_cluster) for _ in cluster.chunks]
    eval_labels = [i for i, cluster in enumerate(eval_cluster) for _ in cluster.chunks]

    print("Golden Labels: ", len(golden_labels))
    print("Eval Labels: ", len(eval_labels))

    # Calculate comparison metrics
    ari = adjusted_rand_score(golden_labels, eval_labels)
    nmi = normalized_mutual_info_score(golden_labels, eval_labels)
    v_measure = v_measure_score(golden_labels, eval_labels)

    return {
        "Adjusted Rand Index": ari,
        "Normalized Mutual Information": nmi,
        "V-Measure": v_measure
    }


# def eval_summary_cluster_similiarity(repo_path: Path):
#     """
#     Evaluate the similarity between the golden standard clusters and the summary clusters
    
#     :param repo_path: Path to the repository
#     """
#     golden_clusters = generate_full_code_clusters(repo_path)
#     summary_clusters = generate_summarized_clusters(repo_path)

#     cluster_sim_score = eval_clusters_similiarity(golden_clusters, summary_clusters)
#     return cluster_sim_score