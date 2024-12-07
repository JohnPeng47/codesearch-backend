import json
from pathlib import Path

from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer, IndexStrat
from src.index.core import ClusterIndex
from src.index.stores import FaissVectorStore, VectorStoreType

repo = "codesearch-backend"
repo_dir = "C:\\Users\\jpeng\\Documents\\projects\\codesearch-data\\repo\\{dir}"
repo_path = Path(repo_dir.format(dir=repo)).resolve()


store = ClusterIndex(FaissVectorStore(repo_path, IndexStrat.CLUSTER))
results = store.query("What is the process for breaking down oversized clusters into smaller subclusters?")
for res in results:
    print(res)