from src.models import CodeChunk
from typing import List, Protocol, Any
from abc import ABC, abstractmethod

from rtfs.cluster.graph import Cluster

from .stores import VectorStore

class BaseIndex(ABC):
    def __init__(self, vec_store: VectorStore):
        self._vec_store = vec_store

    @abstractmethod
    def index(self, *args: Any, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def query(self, *args: Any, **kwargs: Any) -> None:
        pass

class CodeIndex(BaseIndex):
    def index(self, chunks: List[CodeChunk]) -> None:
        self._vec_store.add_all(chunks)

    def query(self, query: str) -> List[CodeChunk]:
        return self._vec_store.query(query)

# class ClusterIndex(BaseIndex):
#     def index(self, 
#               chunks: List[CodeChunk], 
#               clusters: List[Cluster]) -> None:
