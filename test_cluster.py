from src.repo.graph import get_or_create_chunk_graph
from src.index.service import get_or_create_index
from rtfs.aider_graph.aider_graph import AiderGraph
from rtfs.transforms.cluster import cluster

from pathlib import Path

REPO_NAME = "JohnPeng47_codesearch-test.git"

REPO_PATH = Path("../codesearch-data/repo") / REPO_NAME
INDEX_PATH = Path("../codesearch-data/index") / REPO_NAME
GRAPH_PATH = Path("../codesearch-data/graph") / REPO_NAME

code_index = get_or_create_index(REPO_PATH, INDEX_PATH)
nodes = code_index._docstore.docs.values()

cg = AiderGraph.from_chunks(REPO_PATH, nodes)
