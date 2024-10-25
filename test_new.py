from src.cluster.chunk_repo import ChunkStrat
from pathlib import Path

from src.cluster.cluster_v2 import ClusterStrategy
from src.cluster.lmp.cluster_v4 import generate_clusters
from src.chunk.chunk import chunk_repo, ChunkStrat

repo_name = "ell"
repo_path = Path("src/cluster/repos") / repo_name

chunks = chunk_repo(repo_path, ChunkStrat.VANILLA)
chunk_strat = ClusterStrategy(chunks, 
                              cluster_op=generate_clusters,
                              max_iters=1)
chunk_strat.run()
