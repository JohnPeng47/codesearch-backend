import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, cast, Set
import faiss
import fsspec
import numpy as np
from pathlib import Path
from dataclasses_json import DataClassJsonMixin
from fsspec.implementations.local import LocalFileSystem
# IMPORTANT: not using native pydantic PrivateAttr
from llama_index.core.bridge.pydantic import PrivateAttr

from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores.simple import _build_metadata_filter_fn
from llama_index.core.vector_stores.types import (
    VectorStoreQuery,
    VectorStoreQueryMode,
    VectorStoreQueryResult,
    VectorStore as LLamaVectorStore,
    BasePydanticVectorStore
)
from llama_index.core.vector_stores.utils import node_to_metadata_dict
from llama_index.core.ingestion import IngestionPipeline, DocstoreStrategy
from llama_index.core.storage.docstore import SimpleDocumentStore

from src.settings import DEFAULT_INDEX_SETTINGS

from src.config import INDEX_ROOT
from src.models import CodeChunk

from .base import VectorStore, VStoreQueryResult, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

LEARNER_MODES = {
    VectorStoreQueryMode.SVM,
    VectorStoreQueryMode.LINEAR_REGRESSION,
    VectorStoreQueryMode.LOGISTIC_REGRESSION,
}

MMR_MODE = VectorStoreQueryMode.MMR

NAMESPACE_SEP = "__"
DEFAULT_VECTOR_STORE = "default"


@dataclass
class SimpleVectorStoreData(DataClassJsonMixin):
    text_id_to_ref_doc_id: Dict[str, str] = field(default_factory=dict)
    vector_id_to_text_id: Dict[int, str] = field(default_factory=dict)
    metadata_dict: Dict[str, Any] = field(default_factory=dict)


class SimpleFaissVectorStore(BasePydanticVectorStore):
    """Simple Vector Store using Faiss as .

    In this vector store, embeddings are stored within a simple, in-memory dictionary.

    Args:
        simple_vector_store_data_dict (Optional[dict]): data dict
            containing the embeddings and doc_ids. See SimpleVectorStoreData
            for more details.
    """

    _data: SimpleVectorStoreData = PrivateAttr()
    _fs: fsspec.AbstractFileSystem = PrivateAttr()
    _faiss_index: Any = PrivateAttr()
    _d: int = PrivateAttr()

    _vector_ids_to_delete: List[int] = PrivateAttr(default_factory=list)
    _text_ids_to_delete: Set[str] = PrivateAttr(default_factory=set)

    stores_text: bool = False

    def __init__(
        self,
        faiss_index: Any,
        d: int = 1536,
        data: Optional[SimpleVectorStoreData] = None,
        fs: Optional[fsspec.AbstractFileSystem] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""

        import_err_msg = """
            `faiss` package not found. For instructions on
            how to install `faiss` please visit
            https://github.com/facebookresearch/faiss/wiki/Installing-Faiss
        """
        try:
            import faiss
        except ImportError:
            raise ImportError(import_err_msg)

        self._d = d
        self._faiss_index = cast(faiss.Index, faiss_index)
        self._data = data or SimpleVectorStoreData()
        self._fs = fs or fsspec.filesystem("file")
        super().__init__(**kwargs)

    @classmethod
    def from_defaults(cls, d: int = 1536):
        faiss_index = faiss.IndexIDMap(faiss.IndexFlatL2(1536))
        return cls(faiss_index, d)

    @property
    def client(self) -> Any:
        """Return the faiss index."""
        return self._faiss_index

    def add(
        self,
        nodes: List[BaseNode],
        **add_kwargs: Any,
    ) -> List[str]:
        """Add nodes to index."""

        if not nodes:
            return []

        vector_id = (
            max([int(k) for k in self._data.vector_id_to_text_id.keys()])
            if self._data.vector_id_to_text_id
            else 0
        )

        logger.info(f"Adding {len(nodes)} nodes to index, start at id {vector_id}.")

        embeddings = []
        ids = []
        for node in nodes:
            embeddings.append(node.get_embedding())
            ids.append(int(vector_id))
            self._data.vector_id_to_text_id[vector_id] = node.id_
            self._data.text_id_to_ref_doc_id[node.id_] = node.ref_doc_id or node.id_
            vector_id += 1

            metadata = node_to_metadata_dict(
                node, remove_text=True, flat_metadata=False
            )
            metadata.pop("_node_content", None)
            self._data.metadata_dict[node.node_id] = metadata

        vectors_ndarray = np.array(embeddings)
        ids_ndarray = np.array(ids)

        self._faiss_index.add_with_ids(vectors_ndarray, ids_ndarray)

        return [node.node_id for node in nodes]

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """
        Delete nodes using with ref_doc_id.

        Args:
            ref_doc_id (str): The doc_id of the document to delete.

        """

        self._text_ids_to_delete = set()
        for text_id, ref_doc_id_ in self._data.text_id_to_ref_doc_id.items():
            if ref_doc_id == ref_doc_id_:
                self._text_ids_to_delete.add(text_id)

        for vector_id, text_id in self._data.vector_id_to_text_id.items():
            if text_id in self._text_ids_to_delete:
                self._vector_ids_to_delete.append(vector_id)

    def query(
        self,
        query: VectorStoreQuery,
        **kwargs: Any,
    ) -> VectorStoreQueryResult:
        """Query index for top k most similar nodes.

        Args:
            query_embedding (List[float]): query embedding
            similarity_top_k (int): top k most similar nodes

        """
        # TODO: turning off the filter, idk where this is set
        query.filters = None
        query_filter_fn = _build_metadata_filter_fn(
            lambda node_id: self._data.metadata_dict[node_id], query.filters
        )

        query_embedding = cast(List[float], query.query_embedding)
        query_embedding_np = np.array(query_embedding, dtype="float32")[np.newaxis, :]
        dists, indices = self._faiss_index.search(
            query_embedding_np, query.similarity_top_k
        )
        dists = list(dists[0])

        if len(indices) == 0:
            return VectorStoreQueryResult(similarities=[], ids=[])

        node_idxs = indices[0]

        duplicates = 0
        not_found = 0
        filtered_out = 0

        filtered_dists = []
        filtered_node_ids = []

        for dist, idx in zip(dists, node_idxs):
            if idx < 0:
                break

            node_id = self._data.vector_id_to_text_id.get(idx)
            if not query_filter_fn(node_id):
                filtered_out += 1
            elif node_id and node_id not in filtered_node_ids:
                filtered_node_ids.append(node_id)
                filtered_dists.append(dist.item())
            elif node_id in filtered_node_ids:
                duplicates += 1
            else:
                not_found += 1

        if not_found or duplicates:
            logger.debug(
                f"Return {len(filtered_node_ids)} nodes ({not_found} not found, {duplicates} duplicates and {filtered_out} nodes)."
            )

        return VectorStoreQueryResult(
            similarities=filtered_dists, ids=filtered_node_ids
        )

    def persist(
        self,
        persist_dir: str,
        fs: Optional[fsspec.AbstractFileSystem] = None,
    ) -> None:
        """Persist the SimpleVectorStore to a directory."""
        fs = fs or self._fs

        # I don't think FAISS supports fsspec, it requires a path in the SWIG interface
        # TODO: write to a temporary file and then copy to the final destination
        if fs and not isinstance(fs, LocalFileSystem):
            raise NotImplementedError("FAISS only supports local storage for now.")
        import faiss

        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)

        logger.info(f"Deleting {len(self._vector_ids_to_delete)} vectors from index.")

        if self._vector_ids_to_delete:
            ids_to_remove_array = np.array(self._vector_ids_to_delete, dtype=np.int64)
            removed = self._faiss_index.remove_ids(ids_to_remove_array)
            logger.info(f"Removed {removed} vectors from index.")

        if self._text_ids_to_delete:
            for text_id in self._text_ids_to_delete:
                if self._data.metadata_dict is not None:
                    self._data.metadata_dict.pop(text_id, None)

        faiss.write_index(
            self._faiss_index, f"{persist_dir}/vector_index.faiss"
        )

        for vector_id in self._vector_ids_to_delete:
            text_id = self._data.vector_id_to_text_id.pop(vector_id, None)
            if text_id:
                self._data.text_id_to_ref_doc_id.pop(text_id, None)

        self._vector_ids_to_delete = []

        with fs.open(f"{persist_dir}/vector_index.json", "w") as f:
            json.dump(self._data.to_dict(), f)

    @classmethod
    def from_persist_dir(
        cls,
        persist_dir: str,
        fs: Optional[fsspec.AbstractFileSystem] = None,
    ) -> "SimpleFaissVectorStore":
        """Create a SimpleKVStore from a persist directory."""

        fs = fs or fsspec.filesystem("file")
        if not fs.exists(persist_dir):
            raise ValueError(f"No existing index store found at {persist_dir}.")

        index_path = f"{persist_dir}/vector_index.faiss"
        data_path = f"{persist_dir}/vector_index.json"

        if not fs.exists(index_path) or not fs.exists(data_path):
            logger.warning(f"No existing index store found for index {persist_dir}")
            return None

        # I don't think FAISS supports fsspec, it requires a path in the SWIG interface
        # TODO: copy to a temp file and load into memory from there
        if fs and not isinstance(fs, LocalFileSystem):
            raise NotImplementedError("FAISS only supports local storage for now.")

        faiss_index = faiss.read_index(index_path)

        with fs.open(data_path, "rb") as f:
            data_dict = json.load(f)
            data = SimpleVectorStoreData.from_dict(data_dict)

        logger.info(f"Loading {__name__} from {persist_dir}.")

        return cls(faiss_index=faiss_index, data=data)

    @classmethod
    def from_index(cls, faiss_index: Any):
        return cls(faiss_index)

    def to_dict(self) -> dict:
        return self._data.to_dict()
    
# TODO: define query on this class because in case
class FaissVectorStore(VectorStore):
    def __init__(self, repo_path: Path, index_name: str):
        self._index_name = index_name
        self._persist_dir = INDEX_ROOT / repo_path.name / index_name
        self._docstore_path = self._persist_dir / f"docstore.json"
        self._docstore = SimpleDocumentStore()

        if os.path.exists(self._persist_dir):
            print(f"Loading from persisted: {self._persist_dir}")
            self._vector_store = SimpleFaissVectorStore.from_persist_dir(self._persist_dir)
        else:
            print("Creating new vector store")
            faiss_index = faiss.IndexIDMap(faiss.IndexFlatL2(DEFAULT_INDEX_SETTINGS.dimensions))
            self._vector_store = SimpleFaissVectorStore(faiss_index)

    def add_all(self, chunks: List[BaseNode]):        
        self._pipeline = IngestionPipeline(
        transformations=[EMBEDDING_MODEL],
            docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
            docstore=self._docstore,
            vector_store=self._vector_store,
        )

        self._pipeline.run( 
            nodes=chunks,
            show_progress=True,
            num_workers=None,
        )
        self._docstore.persist(persist_path=self._docstore_path)
        self._vector_store.persist(self._persist_dir)

    # NOTE: Need to include docstore as well
    def query(self, query_str: str):
        # save an instance of docstore
        if not self._docstore.docs:
            self._docstore = SimpleDocumentStore.from_persist_path(self._docstore_path)

        query_embedding = EMBEDDING_MODEL.get_query_embedding(query_str)
        # LEARN:
        # figure out what this is and how does hybrid search work in (parameter alpha in VectorStoreQuery)
        # filters = MetadataFilters(filters=[], condition=FilterCondition.AND)
        query_bundle = VectorStoreQuery(
            query_str=query_str,
            query_embedding=query_embedding,
            similarity_top_k=5,  # TODO: Fix paging?
        )
        query_res = self._vector_store.query(query_bundle)

        return [
            VStoreQueryResult(
                id=id,
                distance=dist,
                metadata=self._docstore.get_node(id).metadata
            ) for dist, id in zip(query_res.similarities, query_res.ids)
        ]

    
