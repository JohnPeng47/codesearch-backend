from src.llm.evals.eval_cluster import eval_coherence_clusters
from src.cluster.cluster_v1 import (
    generate_full_code_clusters, 
    generate_full_code_clustersv2,
    generate_summarized_clusters,
    generate_graph_clusters,
    generate_random_clusters
)
from pathlib import Path
import time


repo_name = "ell"
repo_path = Path("src/cluster/repos") / repo_name
graph_clusters = generate_graph_clusters(repo_path)

all_scores = []
for i in range(10):
    score, variance = eval_coherence_clusters(graph_clusters, 3, "Graph", repo_name)
    all_scores.append((score, variance))

    print(f"Iteration {i + 1} - Score: {score:.2f}, Variance: {variance:.2f}")

    time.sleep(30)

# Calculate average score and variance
avg_score = sum(score for score, _ in all_scores) / len(all_scores)
avg_variance = sum(variance for _, variance in all_scores) / len(all_scores)

# Calculate sample variance of scores
score_variance = sum((score - avg_score) ** 2 for score, _ in all_scores) / (len(all_scores) - 1)
variance_variance = sum((variance - avg_variance) ** 2 for _, variance in all_scores) / (len(all_scores) - 1)

print(f"Average score: {avg_score:.2f}")
print(f"Average variance: {avg_variance:.2f}")
print(f"Sample variance of scores: {score_variance:.2f}")
print(f"Sample variance of variances: {variance_variance:.2f}")

print(all_scores)

