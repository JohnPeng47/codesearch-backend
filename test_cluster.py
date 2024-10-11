from src.repo.graph import get_or_create_chunk_graph
from src.index.service import get_or_create_index
from rtfs.aider_graph.aider_graph import AiderGraph
from rtfs.transforms.cluster import cluster
from rtfs.summarize.summarize import Summarizer
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.cluster.graph import ClusterGraph

import networkx as nx
from pathlib import Path


def get_call_paths(g: nx.MultiDiGraph):
    # Assuming G is your multidigraph
    all_paths = []

    # Get all simple paths between all pairs of nodes
    for source in g.nodes():
        for target in g.nodes():
            if source != target:
                paths = list(nx.all_simple_paths(g, source, target))
                all_paths.extend(paths)

    # Sort paths by length in descending order
    sorted_paths = sorted(all_paths, key=len, reverse=True)
    return sorted_paths


DIR_PATH = Path("C:\\Users\\jpeng\\Documents\\projects\\codesearch-data")
REPO_NAME = "JohnPeng47_codesearch-test.git"

REPO_PATH = DIR_PATH / "repo" / REPO_NAME
INDEX_PATH = DIR_PATH / "index" / REPO_NAME
GRAPH_PATH = DIR_PATH / "graph" / REPO_NAME

code_index = get_or_create_index(REPO_PATH, INDEX_PATH)
nodes = code_index._docstore.docs.values()

cg = AiderGraph.from_chunks(REPO_PATH, nodes)
cg2 = ChunkGraph.from_chunks(REPO_PATH, nodes)

# cluster(cg)
print("AIderGraph: ")
paths = get_call_paths(cg._graph)
with open("aider_paths.txt", "w") as f:
    for p in paths:
        f.write(str(p) + "\n")

# print("ChunkGraph: ")
# paths = get_call_paths(cg2._graph)
# for p in paths[:30]:
#     print(p)
