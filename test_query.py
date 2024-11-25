import json
from pathlib import Path

from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer, IndexStrat
from src.index.stores import FaissVectorStore, VectorStoreType

repo = "codesearch-backend"
repo_dir = "C:\\Users\\jpeng\\Documents\\projects\\codesearch-data\\repo\\{dir}"
repo_path = Path(repo_dir.format(dir=repo)).resolve()


vec_store = FaissVectorStore(repo_path, IndexStrat.CLUSTER)
vec_store.query("")
