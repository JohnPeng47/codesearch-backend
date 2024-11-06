from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.summarize.summarize import Summarizer
from src.config import GRAPH_ROOT
from src.chunk.chunk import chunk_repo, ChunkStrat

import json
from pathlib import Path

repo_path = Path(r"C:\Users\jpeng\Documents\projects\codesearch-backend\src\cluster\repos\moatless-tools")
graph_path = GRAPH_ROOT / "aorwall_moatless-tools"

chunks = chunk_repo(repo_path, ChunkStrat.VANILLA)
graph_json = json.loads(open(graph_path, "r").read())
cg = ChunkGraph.from_json(repo_path, graph_json)
paths = cg.get_longest_path()

print(paths[0].to_str())