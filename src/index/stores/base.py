from llama_index.embeddings.openai import OpenAIEmbedding

from typing import Any
from pathlib import Path
from abc import ABC, abstractmethod

EMBEDDING_MODEL = OpenAIEmbedding()

# TODO: add logging methods here
class VectorStore(ABC):
    @abstractmethod
    def __init__(self, repo_path: Path, index_name: str):
        raise NotImplementedError()
    
    @abstractmethod
    def add_all(self, items: Any):
        raise NotImplementedError()

    @abstractmethod
    def query(self, query: str):
        raise NotImplementedError()