from llama_index.embeddings.openai import OpenAIEmbedding
from dataclasses import dataclass

from typing import Any, Dict, List
from pathlib import Path
from abc import ABC, abstractmethod

EMBEDDING_MODEL = OpenAIEmbedding()

@dataclass
class VStoreQueryResult:
    distance: float
    id: str
    metadata: Dict

# TODO: add logging methods here
class VectorStore(ABC):
    @abstractmethod
    def __init__(self, repo_path: Path, index_name: str):
        raise NotImplementedError()
    
    @abstractmethod
    def add_all(self, items: Any):
        raise NotImplementedError()

    @abstractmethod
    def query(self, query: str) -> List[VStoreQueryResult]:
        raise NotImplementedError()