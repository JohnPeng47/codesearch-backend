from typing import List, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel, field_validator
from enum import Enum

from src.cluster.types import ClusteredTopic
from src.cluster.cluster import (
    generate_full_code_clusters, 
    generate_summarized_clusters,
    generate_graph_clusters,
    generate_random_clusters
)

from openai import OpenAI
from pydantic import BaseModel, Field

CLUSTER_METHODS = {
    "FULL_CODE": generate_full_code_clusters,
    "SUMMARIZE": generate_summarized_clusters,
    "GRAPH": generate_graph_clusters,
    "RANDOM": generate_random_clusters
} 

client = OpenAI()

# ell.init(store="logdir", autocommit=True)

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
    ratio = num_files ** 2.0 / num_chunks

    return ratio
    

def eval_cross_file_cluster(clusters: List[ClusteredTopic], min_chunks: int = 3) -> float:
    cross_file_scores = [eval_cross_file_single(cluster) for cluster in clusters 
                         if len(cluster.chunks) >= min_chunks]

    # Calculate the average cross-file score
    if len(cross_file_scores) > 0:
        avg_cross_file_score = sum(cross_file_scores) / len(cross_file_scores)
    else:
        avg_cross_file_score = 0.0

    return avg_cross_file_score


class OneToFiveScale(BaseModel):
    rating: int

    @field_validator("rating")
    def validate_rating(cls, v):
        if isinstance(v, float):
            raise ValueError("Rating must be an integer")
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v
    
def eval_coherence_single(cluster: ClusteredTopic):
    DELIMITER = "\n\n================="
    cluster_code = "\n".join([chunk.get_content() + DELIMITER for chunk in cluster.chunks])

    EVAL_COHERENCE = """
You are given a cluster that is the output of a clustering algorithm designed to group together
code from related features. Your task is to evaluate how well the code in this cluster works together
as a cohesive functional unit in the wider codebase. Output your score on a scale of 1 to 5, where:

1 indicates the cluster contains largely unrelated code snippets with no clear functional relationship
2 indicates the cluster has some loosely related code, but lacks a coherent purpose or functionality
3 indicates the cluster contains moderately related code with a somewhat discernible shared purpose, but with significant irrelevant or misplaced elements
4 indicates the cluster has closely related code forming a mostly cohesive functional unit, with only minor inconsistencies or outliers
5 indicates the cluster represents a highly cohesive functional unit with strongly related code snippets that clearly work together towards a common purpose

Here is the code in the cluster:
{code}

Evaluate the coherence and output your rating.
"""
    messages = [
        # {"role": "system", "content": "You are an AI assistant that evaluates code clusters."},
        {"role": "user", "content": EVAL_COHERENCE.format(code=cluster_code)}
    ]

    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=messages,
        response_format=OneToFiveScale
    )

    return response.choices[0].message.parsed.rating


def eval_coherence_clusters(clusters: List[ClusteredTopic], 
                            iters: int,
                            min_chunks: int = 4,
                            output_file: str = "") -> List[int]:
    
    # need this for notebook rel path :(
    COHERENCE_LOG = Path(r"C:\Users\jpeng\Documents\projects\codesearch-backend\src\llm\evals") / "log" / "coherence"
    to_eval = [cluster for cluster in clusters if len(cluster.chunks) >= min_chunks]
    scores = []

    for _ in range(iters):
        eval_i_scores = []
        for i, eval_cluster in enumerate(to_eval):
            eval_i_scores.append(eval_coherence_single(eval_cluster))
        scores.append(eval_i_scores)

    # calculate estimated variance of a single cluster across iterations        
    if iters > 1:
        cluster_scores = [[] for _ in range(len(to_eval))]
        for i in range(iters):
            for j in range(len(to_eval)):
                cluster_scores[j].append(scores[i][j])
        
        cluster_variances = []
        for j, s in enumerate(cluster_scores):
            mean = sum(s) / len(s)
            variance = sum((x - mean) ** 2 for x in s) / len(s)
            cluster_variances.append(variance)
            print(f"Cluster {j} variance: {variance}")
        
    if output_file:
        with open(COHERENCE_LOG / output_file, "w") as f:
            # LEARN: zip(*scores) is a way to transpose a list of lists
            total_scores = [(c_index, agg_score) for c_index, agg_score in 
                            enumerate([sum(score)/len(score) for score in zip(*scores)])]
            total_scores = sorted(total_scores, key=lambda x: x[1], reverse=True)
            clusters_n_scores = [(to_eval[index], score) for index, score in total_scores]

            for cluster, score in clusters_n_scores:
                f.write(f"Score: {score}\n")
                f.write(f"Cluster name: {cluster.name}\n")
                f.write(f"{cluster}\n")
                f.write("\n")

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
    
    total_score = sum(sum(iter_score) / len(to_eval) for iter_score in scores) / iters
    return total_score


def eval_clusters_metrics(repo_path, iters: int = 1):
    # Generate clusters
    full_code_clusters = generate_full_code_clusters(repo_path)
    graph_clusters = generate_graph_clusters(repo_path)
    random_clusters = generate_random_clusters(repo_path)
    summary_clusters = generate_summarized_clusters(repo_path)

    # Evaluate coherence for each cluster type
    full_code_coherence = eval_coherence_clusters(full_code_clusters, iters=iters)
    graph_coherence = eval_coherence_clusters(graph_clusters, iters=iters)
    random_coherence = eval_coherence_clusters(random_clusters, iters=iters)
    summary_coherence = eval_coherence_clusters(summary_clusters, iters=iters)

    # Create a list of tuples with cluster type and coherence score
    coherence_scores = [
        ("Full Code", full_code_coherence),
        ("Graph", graph_coherence),
        ("Random", random_coherence),
        ("Summary", summary_coherence)
    ]

    # Sort the list based on coherence scores in descending order
    sorted_scores = sorted(coherence_scores, key=lambda x: x[1], reverse=True)

    print("\nCoherence scores ordered from highest to lowest:")
    for cluster_type, score in sorted_scores:
        print(f"{cluster_type}: {score:.4f}")

    # Print pair-wise comparisons
    print("Pair-wise coherence comparisons:")
    print(f"Full Code vs Graph: {full_code_coherence - graph_coherence:.4f}")
    print(f"Full Code vs Random: {full_code_coherence - random_coherence:.4f}")
    print(f"Full Code vs Summary: {full_code_coherence - summary_coherence:.4f}")
    print(f"Graph vs Random: {graph_coherence - random_coherence:.4f}")
    print(f"Graph vs Summary: {graph_coherence - summary_coherence:.4f}")
    print(f"Random vs Summary: {random_coherence - summary_coherence:.4f}")

