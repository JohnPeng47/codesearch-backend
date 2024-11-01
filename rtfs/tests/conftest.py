from pathlib import Path
import pytest

from src.chunk.chunk import chunk_repo, ChunkStrat
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.repo_resolution.repo_graph import RepoGraph
from rtfs.utils import TextRange

from rtfs.tests.data import CHUNK_GRAPH 

def range(start, end):
    return TextRange(
        start_byte=0, end_byte=0, start_point=(start, 0), end_point=(end, 0)
    )


@pytest.fixture
def chunk_nodes(request):
    repo_path = request.param
    # Use the new chunker implementation
    chunks = chunk_repo(
        Path(repo_path), 
        chunk_strat=ChunkStrat.VANILLA,
        exclusions=[
            "__pycache__/*",
            "*.pyc",
            ".git/*",
            ".venv/*",
            "tests/*",  # Exclude test files from indexing
        ]
    )
            
    return chunks


@pytest.fixture
def chunk_graph(request, chunk_nodes):
    repo_path = request.param
    return ChunkGraph.from_chunks(Path(repo_path).resolve(), chunk_nodes)


@pytest.fixture(scope="function")
def repo_graph(request):
    repo_path = request.param
    return RepoGraph(Path(repo_path).resolve())
