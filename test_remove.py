from networkx import random_reference
from src.cluster.cluster_v1 import (
    generate_full_code_clusters, 
    generate_full_code_clustersv2,
    generate_graph_clusters, 
    generate_summarized_clusters,
    generate_random_clusters,
    ClusteredTopic,
    CodeChunk,
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
from ell.ctxt import get_session_id

ell.init(
    store="./ell_storage/chunk_alt",
    autocommit=True,
)

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

clusters = generate_full_code_clustersv2(repo_path.resolve(), ChunkStrat.VANILLA, summarize=False)
