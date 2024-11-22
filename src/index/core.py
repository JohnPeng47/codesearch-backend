from pathlib import Path
from enum import Enum
from typing import List

from rtfs.chunk_resolution.chunk_graph import ChunkGraph

from src.chunk.chunkers import Chunker
from src.models import CodeChunk

from .stores import VECTOR_STORES, VectorStoreType 

class IndexStrat(str, Enum):
    VANILLA = "vanilla"
    CLUSTER = "cluster"

class Indexer:
    def __init__(self, 
                 repo_path: Path, 
                 # TODO: consider grouping these into a single object
                 # that matches the indexing strategy 
                 chunks: List[CodeChunk],
                 cg: ChunkGraph = None,
                 ############################
                 vec_store_type: VectorStoreType = VectorStoreType.FAISS,
                 run_code: bool = True, 
                 run_cluster: bool = False):
        self._vec_store_cls = VECTOR_STORES[vec_store_type]
        self._repo_path = repo_path
        self._chunks = chunks
        self._cg = cg

        self._run_code = run_code
        self._run_cluster = run_cluster

    def run(self):
        if self._run_code:
            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.VANILLA)
            chunk_nodes = [c.to_text_node() for c in self._chunks]
            vec_store.add_all(chunk_nodes)
            
        if self._run_cluster:
            if not self._cg and len(self._cg.get_clusters()) == 0:
                raise ValueError(f"No clusters found in graph {self._cg}")

            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.CLUSTER)
            chunk_nodes = [c.to_text_node() for c in self._chunks]
            cluster_nodes = [c.to_text_node() for c in self._cg.get_clusters()]

            vec_store.add_all(chunk_nodes + cluster_nodes)
            