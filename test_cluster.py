from networkx import random_reference
from src.cluster.cluster_v1 import (
    generate_full_code_clusters, 
    generate_full_code_clustersv2,
    generate_graph_clusters, 
    generate_summarized_clusters,
    generate_random_clusters,
    ClusteredTopic,
    CodeChunk
)
from src.llm.evals.eval_cluster import eval_clusters_metrics, eval_coherence_clusters
from src.llm.evals.utils import EvalReport
from src.cluster.chunk_repo import ChunkStrat

from pathlib import Path
from typing import List
import json
from src.config import GRAPH_ROOT, REPOS_ROOT
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.transforms.cluster import cluster
import ell

ell.init(
    store="./ell_storage/chunk_alt",
    autocommit=True,
)

def generate_cgraph_clusters() -> List[ClusteredTopic]:
    ell_json = json.loads(open(GRAPH_ROOT / "MadcowD_ell_standard.json", "r").read())
    cg = ChunkGraph.from_json(REPOS_ROOT / "MadcowD_ell", ell_json)

    cluster(cg)

    return [
        ClusteredTopic(
            name="Graph Cluster",
            chunks=[
                CodeChunk(
                    id=chunk.og_id,
                    content=chunk.content,
                    filepath=chunk.file_path,
                    input_type="chunk",
                ).dict() for chunk in cluster.chunks
            ],
        ) 
        for cluster in cg.get_clusters()
    ]


repo_name = "ell"
repo_path = Path("src/cluster/repos") / repo_name

# for i in range(10):
#     report = EvalReport("hello")
#     report.add_line("hello")
#     report.write("hello", subfolder="coherence/ello")

# random_clusters = generate_random_clusters(repo_path, size=4, num_clusters=1)
# eval_coherence_clusters(random_clusters, 1, "Random", repo_name, log_local=True)

# eval_clusters_metrics(repo_path, iters=1)
# generate_summarized_clusters(repo_path)

# clusters = generate_full_code_clustersv2(repo_path.resolve(), ChunkStrat.VANILLA, summarize=True)
# eval_coherence_clusters(clusters, 1, "FullCodeHybrid", log_local=True)

cgraph_clusters = generate_cgraph_clusters()
# random_clusters = generate_random_clusters(repo_path, num_clusters = 10)

cgraph_coherence = eval_coherence_clusters(cgraph_clusters, 1, "cgraph", repo_name)
# random_coherence = eval_coherence_clusters(random_clusters, 3, "random", subdir="random")
print(cgraph_coherence)
# print(random_coherence)