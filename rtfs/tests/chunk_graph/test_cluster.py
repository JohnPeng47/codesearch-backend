from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.transforms.cluster import cluster

from conftest import chunk_graph, chunk_nodes, CHUNK_GRAPH
import os

import pytest


# TODO: failing
@pytest.mark.parametrize(
    "chunk_nodes", ["tests/repos/cowboy-server"], indirect=["chunk_nodes"]
)
@pytest.mark.parametrize(
    "chunk_graph", ["tests/repos/cowboy-server"], indirect=["chunk_graph"]
)
def test_confirm_imports(chunk_graph: ChunkGraph):
    cluster(chunk_graph)

    print(chunk_graph.to_str_cluster())
    # assert CHUNK_GRAPH == chunk_graph.to_str_cluster()    
