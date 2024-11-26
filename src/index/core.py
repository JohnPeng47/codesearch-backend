from pathlib import Path
from enum import Enum
from typing import List
from dataclasses import dataclass

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.models import CodeChunk, MetadataType


from .stores import VectorStore, VECTOR_STORES, VectorStoreType 

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
                 overwrite: bool = False,
                 run_code: bool = True, 
                 run_cluster: bool = False):
        self._overwrite = overwrite
        self._vec_store_cls = VECTOR_STORES[vec_store_type]
        self._repo_path = repo_path
        self._chunks = chunks
        self._cg = cg

        self._run_code = run_code
        self._run_cluster = run_cluster

    def run(self):
        if self._run_code:
            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.VANILLA, overwrite=self._overwrite)
            chunk_nodes = [c.to_text_node() for c in self._chunks]
            
            vec_store.add_all(chunk_nodes)
            
        if self._run_cluster:
            if not self._cg and len(self._cg.get_clusters()) == 0:
                raise ValueError(f"No clusters found in graph {self._cg}")

            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.CLUSTER, overwrite=self._overwrite)
            chunk_nodes = [c.to_text_node() for c in self._chunks]
            cluster_nodes = [c.to_text_node() for c in self._cg.get_clusters()]

            vec_store.add_all(chunk_nodes + cluster_nodes)

# @dataclass
# class QueryResult:
#     files: List[str]
#     type: MetadataType

class ClusterIndex:
    def __init__(self, vec_store: VectorStore):
        if vec_store.name() != IndexStrat.CLUSTER:
            raise ValueError(f"Invalid vector store type {vec_store.name()}")
        
        self._vec_store = vec_store

    def query(self, query: str):
        """
        Currently only returning all the files that present in the query
        """
        ret = []
        results = self._vec_store.query(query)
        for r in results:
            ret.append({
                "files": r.files,
                "type": r.type,
                "distance": r.distance
            })

        return ret
