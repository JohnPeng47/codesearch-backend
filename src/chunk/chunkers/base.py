from abc import ABC, abstractmethod
from src.models import CodeChunk
from typing import List

class Chunker(ABC):
    @abstractmethod
    def chunk(self) -> List[CodeChunk]:
        raise NotImplementedError()
