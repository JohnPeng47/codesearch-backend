import json
from pathlib import Path

from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer

repo = "JohnPeng47_CrashOffsetFinder.git"
graph_dir = "C:\\Users\\jpeng\\Documents\\projects\\codesearch-data\\graphs\\{dir}"
repo_dir = "C:\\Users\\jpeng\\Documents\\projects\\codesearch-data\\repo\\{dir}"

repo_path = Path(repo_dir.format(dir=repo)).resolve()
graph_path = Path(graph_dir.format(dir=repo)).resolve()
chunker = PythonChunker(repo_path)
chunks = chunker.chunk()

if graph_path.exists() and graph_path.read_text():
    print("Loading graph from json: ", graph_path)
    graph_json = json.loads(graph_path.read_text()) 
    cg = ChunkGraph.from_json(repo_path, graph_json)
else:
    print("Creating new graph from chunks: ", graph_path)
    cg = ChunkGraph.from_chunks(repo_path, chunks)
    cg.cluster()

    with open(graph_path, "w") as f:
        f.write(json.dumps(cg.to_json(), indent=2))
    
indexer = Indexer(repo_path, chunks, cg, run_code=False, run_cluster=True)
indexer.run()