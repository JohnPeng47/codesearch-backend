from llama_index.embeddings.openai import OpenAIEmbedding
from dataclasses import dataclass

from typing import Any, Dict, List
from pathlib import Path
from abc import ABC, abstractmethod

from src.models import MetadataType

EMBEDDING_MODEL = OpenAIEmbedding()

@dataclass
class VStoreQueryResult:
    distance: float
    id: str
    metadata: Dict
    type: MetadataType
    files: List[str]
    content: str

    def __post_init__(self):
        self.files = [str(Path(f).as_posix()) for f in self.files]

    
# TODO: add logging methods here
class VectorStore(ABC):
    @abstractmethod
    def __init__(self, repo_path: Path, index_name: str, overwrite: bool = False):
        raise NotImplementedError()
    
    @abstractmethod
    def add_all(self, items: Any):
        raise NotImplementedError()

    @abstractmethod
    def query(self, query: str, k: int = 5) -> List[VStoreQueryResult]:
        raise NotImplementedError()
    
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()