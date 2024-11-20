from src.chunk.chunkers import PythonChunker
from src.chunk.settings import IndexSettings
from rtfs.chunk_resolution.chunk_graph import ChunkGraph

from pathlib import Path

repo_path = r"..\codesearch-data\repo\JohnPeng47_CrashOffsetFinder.git"

chunker = PythonChunker(repo_path)
chunks = chunker.chunk()

cg = ChunkGraph.from_chunks(Path(repo_path), chunks)
cg.cluster()

for cluster in cg.get_clusters():
    print(cluster)

