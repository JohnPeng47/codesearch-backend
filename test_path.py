from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.summarize.summarize import Summarizer
from src.config import GRAPH_ROOT
from src.chunk.chunk import chunk_repo, ChunkStrat

import json
from src.chunk.lmp.summarize import summarize_lmp, CodeSummary
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from pathlib import Path

repo_path = Path(r"C:\Users\jpeng\Documents\projects\codesearch-backend\src\cluster\repos\moatless-tools")
graph_path = GRAPH_ROOT / "aorwall_moatless-tools"

graph_json = json.loads(open(graph_path, "r").read())
