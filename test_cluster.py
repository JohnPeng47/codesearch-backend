from src.cluster.cluster import (
    generate_full_code_clusters, 
    generate_graph_clusters, 
    generate_summarized_clusters
)
from src.llm.evals.eval_cluster import eval_clusters_metrics, eval_coherence_clusters
from src.llm.evals.utils import EvalReport

from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

# for i in range(10):
#     report = EvalReport("hello")
#     report.add_line("hello")
#     report.write("hello", subfolder="coherence/ello")

code_cluster = generate_full_code_clusters(repo_path)
eval_coherence_clusters(code_cluster, 1, "FullCode")

# eval_clusters_metrics(repo_path, iters=5)
