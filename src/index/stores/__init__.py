from .base import VectorStore
from .faiss import FaissVectorStore

from enum import Enum

class VectorStoreType(str, Enum):
    FAISS = "faiss"

VECTOR_STORES = {
    VectorStoreType.FAISS: FaissVectorStore
}


