from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer, FaissVectorStore

from pathlib import Path

repo_path = r"..\codesearch-data\repo\JohnPeng47_CrashOffsetFinder.git"


# chunker = PythonChunker(repo_path)
# indexer = Indexer(Path(repo_path), chunker)

# indexer.run()

# FAISS vector store
vec_store = FaissVectorStore(Path(repo_path), "vanilla")
res = vec_store.query("What does this rpeo do?")
print(res)