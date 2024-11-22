from pathlib import Path
from enum import Enum

from src.chunk.chunkers import Chunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph

from .stores import VECTOR_STORES, VectorStoreType 
from .index_strats import CodeIndex

class IndexStrat(str, Enum):
    VANILLA = "vanilla"
    CLUSTER = "cluster"

class Indexer:
    def __init__(self, 
                 repo_path: Path, 
                 chunker: Chunker,
                 vec_store_type: VectorStoreType = VectorStoreType.FAISS,
                 run_code: bool = True, 
                 run_cluster: bool = False):
        self._vec_store_cls = VECTOR_STORES[vec_store_type]
        self._repo_path = repo_path
        self._chunker = chunker

        self._run_code = run_code
        self._run_cluster = run_cluster

    def run(self):
        chunks = self._chunker.chunk()

        if self._run_code:
            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.VANILLA)
            code_index = CodeIndex(vec_store)

            nodes = chunks
            code_index.index(chunks)
            
        if self._run_cluster:
            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.CLUSTER)
            cg = ChunkGraph.from_chunks(self._repo_path, chunks)
            cg.cluster()

            chunk_nodes = [c.to_text_node() for c in chunks]
            cluster_nodes = [c.to_text_node() for c in cg.get_clusters()]
            vec_store.add_all(chunk_nodes + cluster_nodes)
            