from src.cluster.cluster import (
    generate_full_code_clusters, 
    generate_graph_clusters, 
    generate_summarized_clusters
)
from src.llm.evals.eval_cluster import eval_clusters_metrics

from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name


eval_clusters_metrics(repo_path, iters=5)
