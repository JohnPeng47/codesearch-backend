from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer, FaissVectorStore
from src.index.core import IndexStrat

from pathlib import Path

repo_path = r"..\codesearch-data\repo\JohnPeng47_CrashOffsetFinder.git"


# chunker = PythonChunker(repo_path)
# indexer = Indexer(Path(repo_path), chunker, run_code=False, run_cluster=True)

# indexer.run()

# FAISS vector store
vec_store = FaissVectorStore(Path(repo_path), IndexStrat.CLUSTER)
res = vec_store.query("What does this repo do?")
print(res)