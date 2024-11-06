from src.cluster.cluster_v1 import generate_full_code_clustersv2
from src.cluster.cluster_v1 import (
    generate_full_code_clusters, 
    generate_graph_clusters, 
    generate_summarized_clusters,
    generate_random_clusters,
)
from src.llm.evals.eval_cluster import eval_clusters_metrics, eval_coherence_clusters
from src.llm.evals.utils import EvalReport
from src.cluster.chunk_repo import ChunkStrat

from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

# for i in range(10):
#     report = EvalReport("hello")
#     report.add_line("hello")
#     report.write("hello", subfolder="coherence/ello")

# random_clusters = generate_random_clusters(repo_path, size=4, num_clusters=1)
# eval_coherence_clusters(random_clusters, 1, "Random", repo_name, log_local=True)

# eval_clusters_metrics(repo_path, iters=1)
# generate_summarized_clusters(repo_path)

clusters = generate_full_code_clustersv2(repo_path.resolve(), ChunkStrat.VANILLA, summarize=True)
# eval_coherence_clusters(clusters, 1, "FullCodeHybrid", log_local=True)