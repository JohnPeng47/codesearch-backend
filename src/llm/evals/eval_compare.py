from typing import List
from src.cluster.models import ClusteredTopic

from .lmps import eval_coherence_single, eval_compare_clusters as compare_clusters
from .utils import EvalReport, match_clusters


# TODO: this evaluation is kinda useless unless we have high confidence in our evaluation metrics 
# themselves
def eval_compare_clusters(cluster_a: List[ClusteredTopic], 
                          cluster_b: List[ClusteredTopic],
                          perp_a: float,
                          perp_b: float,
                          a_name: str,
                          b_name: str,
                          repo_name: str) -> float:
    eval_report = EvalReport(subdir=f"compare/{repo_name}")

    clusters_report = eval_report.create_subfolder("clusters")
    eval_report.add_section("Cluster Comparison")
    eval_report.add_line(f"Comparing {a_name}[0] and {b_name}[1]")
    eval_report.add_line(f"Coherence:        Compare:        Perplexity:")
    eval_report.add_line("----------------------------------------------")
    
    matched = match_clusters(cluster_a, cluster_b)
    a_total_score = 0
    b_total_score = 0

    for match_a, match_b, perc_a, perc_b in matched:
        a_score = eval_coherence_single(match_a)
        b_score = eval_coherence_single(match_b)

        cohere_score = 0 if a_score > b_score else 1
        ranking_score = compare_clusters(match_a, match_b).parsed.index    
        perp_score = 0 if perc_a < perc_b else 1

        eval_report.add_line(f"{cohere_score}       {ranking_score}     {perp_score}")

        a_total_score += sum(len([score for score in [cohere_score, ranking_score, perp_score] if score == 0]))
        b_total_score += sum(len([score for score in [cohere_score, ranking_score, perp_score] if score == 1]))
        
    
