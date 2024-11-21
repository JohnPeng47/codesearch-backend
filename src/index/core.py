from pathlib import Path
from enum import Enum

from src.chunk.chunkers import Chunker

from .stores import VECTOR_STORES, VectorStoreType 
from .index_strats import CodeIndex

class IndexStrat(str, Enum):
    VANILLA = "vanilla"

class Indexer:
    def __init__(self, 
                 repo_path: Path, 
                 chunker: Chunker,
                 vec_store_type: VectorStoreType = VectorStoreType.FAISS,
                 run_code: bool = True):
        self._vec_store_cls = VECTOR_STORES[vec_store_type]
        self._repo_path = repo_path
        self._chunker = chunker

        self._run_code = run_code

    def run(self):
        chunks = self._chunker.chunk()

        if self._run_code:
            vec_store = self._vec_store_cls(self._repo_path, IndexStrat.VANILLA)
            code_index = CodeIndex(vec_store)
            code_index.index(chunks)
            