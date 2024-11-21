from src.models import CodeChunk
from typing import   List, Protocol, Any
from abc import ABC
from abc import abstractmethod

from .stores import VectorStore

class CodeIndex(ABC):
    def __init__(self, vec_store: VectorStore):
        self._vec_store = vec_store

    @abstractmethod
    def index(self, *args: Any, **kwargs: Any) -> None:
        pass
    
class CodeIndex(CodeIndex):
    def index(self, chunks: List[CodeChunk]) -> None:
        self._vec_store.add_all(chunks)