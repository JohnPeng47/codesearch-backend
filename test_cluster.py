from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.chunk.chunkers import PythonChunker
from src.repo.models import SummarizedClusterResponse

from pathlib import Path
import json
import dotenv

dotenv.load_dotenv()

repo_path = "/home/ubuntu/codesearch-data/repo/MadcowD_ell"
# graph_path = "../codesearch-data/graphs/MadcowD_ell"

chunks = PythonChunker(repo_path).chunk()
cg = ChunkGraph.from_chunks(Path(repo_path), chunks)
# for cluster in cg.filter_nodes(node_filter={"kind": "ClusterNode"}):
#     cg.remove_node(cluster.id)

cg.cluster()
print(SummarizedClusterResponse(summarized_clusters=cg.get_clusters()))