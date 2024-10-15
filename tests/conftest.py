import pytest
import json
from pathlib import Path
from rtfs.chunk_resolution import ChunkGraph

TEST_GRAPH = "tests/data/graphs/JohnPeng47_CrashOffsetFinder.git"
TEST_REPO = "tests/data/repo/JohnPeng47_CrashOffsetFinder.git"


@pytest.fixture
def chunk_graph():
    with open(TEST_GRAPH, "r") as f:
        graph_dict = json.load(f)

    cg = ChunkGraph.from_json(Path(TEST_REPO), graph_dict)
    return cg
