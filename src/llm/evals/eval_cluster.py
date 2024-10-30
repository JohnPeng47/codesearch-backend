from typing import List
from pydantic import BaseModel, field_validator
from pathlib import Path
import ell
from openai import OpenAI

from src.cluster.models import ClusteredTopic
from src.cluster.cluster_v1 import (
    generate_full_code_clusters, 
    generate_summarized_clusters,
    generate_graph_clusters,
    generate_random_clusters
)
from src.config import EVAL_ROOT
from src.llm.invoke_mt import invoke_multithread

from .lmps import eval_coherence_single, eval_remove_chunks
from .utils import EvalReport

# TODO: rerun this eval set to determine new number ranking
CLUSTER_METHODS = {
    "FULL_CODE": generate_full_code_clusters,
    "SUMMARIZE": generate_summarized_clusters,
    "GRAPH": generate_graph_clusters,
    "RANDOM": generate_random_clusters
} 
EVAL_ITERATIONS = 5

client = OpenAI()

def eval_cross_file_single(cluster: ClusteredTopic) -> float:
    # Calculate the number of unique files in the cluster
    unique_files = set(chunk.filepath for chunk in cluster.chunks 
                       if chunk.filepath is not None)
    num_files = len(unique_files)
    num_chunks = len(cluster.chunks)

    # print("Cluster: ", cluster.name)
    # print(f"Num Files: {len(unique_files)}, Num Chunks: {num_chunks}")
    # for f in unique_files:
    #     print(f)

    # Avoid division by zero
    if num_chunks == 0:
        return 0.0

    # Calculate the ratio of files to chunks
    score = num_files ** 1.3 / num_chunks

    return num_files, num_chunks, score
    

def eval_cross_file_cluster(clusters: List[ClusteredTopic], min_chunks: int = 3) -> float:
    cross_file_scores = [eval_cross_file_single(cluster)[2] for cluster in clusters 
                         if len(cluster.chunks) >= min_chunks]

    # Calculate the average cross-file score
    if len(cross_file_scores) > 0:
        avg_cross_file_score = sum(cross_file_scores) / len(cross_file_scores)
    else:
        avg_cross_file_score = 0.0

    return avg_cross_file_score


# TODO: make a log_report object with add_section() method
def eval_coherence_clusters(clusters: List[ClusteredTopic], 
                            eval_name: str,
                            repo_name: str,
                            iters: int = 1,
                            min_chunks: int = 4) -> List[int]:
    eval_report = EvalReport(subdir=Path("coherence") / repo_name / eval_name)
    to_eval = [cluster for cluster in clusters if len(cluster.chunks) >= min_chunks]
    if not to_eval:
        NO_CLUSTERS_MSG = f"No clusters found matching min_chunks requirement for {eval_name}, exiting..."
        eval_report.add_line(NO_CLUSTERS_MSG)
        return
    
    # if multiple iterations, evaluate each single cluster in parallel batches
    # to take advantage of prompt caching
    scores = []
    for cluster in to_eval:
        eval_clusters = [cluster] * iters
        # TODO: pass the session ID and test if we are passing it properly
        cluster_scores = [score.parsed.rating for score in 
                        invoke_multithread(eval_clusters, eval_coherence_single, max_workers=6)["results"]]
        scores.append(cluster_scores)

    scores = [score for score in zip(*scores)]


    # LEARN: zip(*scores) is a way to transpose a list of lists
    # calculate estimated variance of a single cluster across iterations 
    cluster_scores = [c_scores for c_scores in zip(*scores)]

    # kinda broken does not account for cf scores
    # if iters > 1:        
    #     for j, c_scores in enumerate(cluster_scores):
    #         mean = sum(c_scores) / len(c_scores)
    #         variance = sum((x - mean) ** 2 for x in c_scores) / len(c_scores)
    #         eval_report.add_section(f"Cluster Variance")
    #         eval_report.add_line(f"Cluster {j} variance: {variance}")

    mean_cluster_scores = [(c_index, agg_score) for c_index, agg_score in 
                    enumerate([sum(score)/len(score) for score in cluster_scores])]
    mean_cluster_scores = sorted(mean_cluster_scores, key=lambda x: x[1], reverse=True)

    clusters_n_scores = [(to_eval[index], score) for index, score in mean_cluster_scores]
    for cluster, score in clusters_n_scores:
        eval_report.add_section(f"Cluster Eval")
        eval_report.add_line(f"Score: {score}")
        eval_report.add_line(f"Cluster name: {cluster.name}")
        eval_report.add_line(f"{cluster.full_code()}")

    # TODO: code not run before, not sure working
    # Take the higest and lowest coherence scores and the index into
    # clusters from to_eval
    # total_scores = [(c_index, agg_score) for c_index, agg_score in 
    #                 enumerate([sum(score)/iters for score in scores])]
    # total_scores = sorted(total_scores, key=lambda x: x[1], reverse=True)
    # top_scores = total_scores[:4]
    # bottom_scores = total_scores[-4:]
    
    # chunks_n_scores = [(to_eval[index], score) for index, score in top_scores + bottom_scores]
    # for chunk, score in chunks_n_scores:
    #     f.write(f"Coherence score: ")

    avg_score = sum(sum(iter_score) / len(to_eval) for iter_score in scores) / iters        
    variance = sum((sum(iter_score) / len(to_eval) - avg_score) ** 2 for iter_score in scores) / iters
    std = variance ** 0.5

    eval_report.add_line(f"Total coherence score: {avg_score}")
    eval_report.write()

    return avg_score, std

def eval_clusters(clusters: List[ClusteredTopic]):
    cf_score = eval_cross_file_cluster(clusters)
    cohere_score = eval_coherence_clusters(clusters, EVAL_ITERATIONS, "coherence")

    return 1.5 * cohere_score + cf_score
    
def eval_clusters_metrics(repo_path: Path, iters: int = 1):
    repo_name = repo_path.name
    eval_report = EvalReport("cluster_metrics", reportdir=EVAL_ROOT / repo_path.name / "cluster_metrics")

    full_code_clusters = generate_full_code_clusters(repo_path)
    graph_clusters = generate_graph_clusters(repo_path)
    random_clusters = generate_random_clusters(repo_path)
    summary_clusters = generate_summarized_clusters(repo_path)

    full_code_coherence = eval_coherence_clusters(full_code_clusters, iters, "FullCode", repo_name)
    graph_coherence = eval_coherence_clusters(graph_clusters, iters, "Graph", repo_name)
    random_coherence = eval_coherence_clusters(random_clusters, iters, "Random", repo_name)
    summary_coherence = eval_coherence_clusters(summary_clusters, iters, "Summary", repo_name)

    # Create a list of tuples with cluster type and coherence score
    coherence_scores = [
        ("Full Code", full_code_coherence),
        ("Graph", graph_coherence),
        ("Random", random_coherence),
        ("Summary", summary_coherence)
    ]

    # Sort the list based on coherence scores in descending order
    sorted_scores = sorted(coherence_scores, key=lambda x: x[1], reverse=True)

    eval_report.add_line("\nCoherence scores ordered from highest to lowest:")
    for cluster_type, score in sorted_scores:
        eval_report.add_line(f"{cluster_type}: {score:.4f}")

    # Print pair-wise comparisons
    eval_report.add_line("Pair-wise coherence comparisons:")
    eval_report.add_line(f"Full Code vs Graph: {full_code_coherence - graph_coherence:.4f}")
    eval_report.add_line(f"Full Code vs Random: {full_code_coherence - random_coherence:.4f}")
    eval_report.add_line(f"Full Code vs Summary: {full_code_coherence - summary_coherence:.4f}")
    eval_report.add_line(f"Graph vs Random: {graph_coherence - random_coherence:.4f}")
    eval_report.add_line(f"Graph vs Summary: {graph_coherence - summary_coherence:.4f}")
    eval_report.add_line(f"Random vs Summary: {random_coherence - summary_coherence:.4f}")

    eval_report.write("coherence_stats")

