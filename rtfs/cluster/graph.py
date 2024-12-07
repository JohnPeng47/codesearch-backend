from typing import List, Dict, Literal, TYPE_CHECKING, Optional, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from collections import defaultdict

from src.models import CodeChunk, MetadataType
from rtfs.graph import Edge, Node, EdgeKind, NodeKind
from rtfs.chunk_resolution.graph import ChunkNode

from llama_index.core.schema import TextNode
 
if TYPE_CHECKING:
    from .cluster_graph import ClusterGraph

class ClusterSummary(BaseModel):
    title: str
    summary: str

    def get_content(self):
        return self.summary

@dataclass(kw_only=True)
class ClusterEdge(Edge):
    kind: Literal[EdgeKind.ClusterToCluster,EdgeKind.ChunkToCluster]

@dataclass
class ClusterRefEdge(Edge):
    ref: str
    src_node: str
    dst_node: str
    kind: EdgeKind = EdgeKind.ClusterRef

### Cluster Node ####
class ClusterMetadata(BaseModel):
    imports: Optional[Dict[str, List[str]]] = Field(
        default_factory=lambda: defaultdict(list)
    )

    @classmethod
    def from_json(cls, data):
        print("DATA: ", data)
        return cls(
            imports=defaultdict(set, {k: set(v) for k,v in data.get("imports", {}).items()}),
        )

    def to_json(self) -> Dict:
        return {
            "imports": {k: list(v) for k,v in self.imports.items()}
        }

    def __str__(self):
        output_str = ""
        for file_id in self.imports:
            output_str += f"From: {file_id}\n"
            for ref in self.imports[file_id]:
                output_str += f" - {ref}\n"

        return output_str

# todo RIGHT NOW: move the conversion to ClusterNode since that is how we are
# handling the conversion
# TODO: think we want to establish inheritance from ClusterNode to Cluster
# ClusterNode is convereted to Cluster via ClusterGraph::node_to_cluster 
@dataclass
class Cluster:
    id: int
    title: str
    chunks: List[CodeChunk]
    children: List["Cluster"]
    summary: ClusterSummary
    metadata: ClusterMetadata

    # TODO: 
    def to_str(self,
               return_content: bool = False, 
               return_summaries: bool = False,
               return_imports: bool = True) -> str:
        
        name = self.id if not self.summary else self.summary.title
        summary = self.summary.get_content() if self.summary else ""
        imports = str(self.metadata) if self.metadata else {}

        s = f"Cluster: {name}\n"
        s += f"Summary:\n {summary}\n" if summary and return_summaries else ""
        s += f"Imports:\n {imports}\n" if imports and return_imports else ""
        s += f"Chunks ({len(self.chunks)}):\n"
        for chunk in self.chunks:
            chunk_str = chunk.to_str(return_content)
            s += "- " + chunk_str.replace("\n", "\n  ") + "\n"

        if self.children:
            s += f"Children ({len(self.children)}):\n"
            for child in self.children:
                child_str = child.to_str(return_content)
                s += "  " + child_str.replace("\n", "\n  ") + "\n"

        return s

    # Design decision:
    # consolidate all deserialization methods into one class
    @classmethod
    def from_cluster_node(cls, 
                          cluster_id: str, 
                          cluster_graph: "ClusterGraph",    
                          return_content = False):
        cluster_node: ClusterNode = cluster_graph.get_node(cluster_id)
        if not cluster_node or cluster_node.kind != NodeKind.Cluster:
            raise ValueError(f"Node {cluster_node} is the wrong input type")

        chunks = []
        children = []
        imports: Dict[str, Set] = defaultdict(set)
        for child in cluster_graph.children(cluster_id, edge_types=[EdgeKind.ChunkToCluster, 
                                                           EdgeKind.ClusterToCluster]):
            if child == cluster_id:
                raise ValueError(f"Cluster {cluster_id} has a self-reference")

            child_node: ChunkNode = cluster_graph.get_node(child)
            if child_node.kind == NodeKind.Chunk:
                chunk_info = cluster_graph.node_to_chunk(child, return_content=return_content)
                chunks.append(chunk_info)

                # merge the dicts together
                for new_key in chunk_info.metadata.imports:
                    imports[new_key] = imports[new_key].union(chunk_info.metadata.imports[new_key])

            elif child_node.kind == NodeKind.Cluster:
                children.append(cluster_graph.node_to_cluster(child, return_content=return_content))

        # create imports
        cluster_node.metadata.imports = imports
        print("Imports: ", imports)

        return Cluster(
            id=cluster_node.id,
            title=cluster_node.title,
            summary=cluster_node.summary,
            metadata=cluster_node.metadata,
            chunks=chunks,
            children=children,
        )

    def to_text_node(self) -> TextNode:
        return TextNode(
            text=self.summary.get_content(),
            metadata={
                "chunk_ids": [chunk.id for chunk in self.chunks],
                "title": self.title,
                "type": MetadataType.CLUSTER
            },
            id_=self.id,
            embedding=None,
        )

    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        if len(self.chunks) != len(other.chunks):
            return False
        
        chunks_equal = all([chunk == other_chunk for chunk, other_chunk in zip(self.chunks, other.chunks)])
        return self.id == other.id and chunks_equal
    
@dataclass(kw_only=True)
class ClusterNode(Node):
    kind: NodeKind = NodeKind.Cluster
    title: str = ""
    summary: ClusterSummary = None
    metadata: ClusterMetadata = ClusterMetadata()

    # Need this here because ClusterSummary is used as a response_format
    # for LLMs and cant accept default values
    def __post_init__(self):
        if self.summary is None:
            self.summary = ClusterSummary(
                title="",
                summary=""
            )

    def get_content(self):
        return self.summary

    def __hash__(self): 
        return hash(self.id)

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary.dict(),
            "kind": self.kind,
            "metadata": self.metadata.to_json()
        }