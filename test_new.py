from pathlib import Path

from src.cluster.cluster import ClusterStrategy
from src.cluster.lmp.cluster_v4 import generate_clusters
from src.chunk.chunk import chunk_repo, ChunkStrat

import ell

ell.init("ell_storage/chunk_alt")

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

chunks = chunk_repo(repo_path, ChunkStrat.VANILLA)
chunk_strat = ClusterStrategy(chunks, 
                              cluster_op=generate_clusters)
clusters = chunk_strat.run(iters=2)

for cluster in clusters:
    print(cluster)
