from typing import List
from ...cluster.types import ClusteredTopic

def match_clusters(cluster_a: List[ClusteredTopic], 
                 cluster_b: List[ClusteredTopic], 
                 min_match=3):
    """
    Loops through all clusters to find the best match for each cluster in the other set.
    """
    min_match = 0
    matched_clusters = []
    for a in cluster_a:
        best_match = None
        best_score = -1
        for b in cluster_b:
            score = len(set(a.chunks) & set(b.chunks))
            if score > best_score:
                best_score = score
                best_match = b
        if best_score >= min_match:
            matched_clusters.append((a, best_match))

    return matched_clusters