from typing import List, Dict, Literal, TYPE_CHECKING
from dataclasses import dataclass, field
from pydantic import BaseModel

from src.models import CodeChunk, MetadataType, ChunkImport
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
    kind: Literal[EdgeKind.ClusterToCluster, EdgeKind.ChunkToCluster]

@dataclass
class ClusterRefEdge(Edge):
    ref: str
    src_node: str
    dst_node: str
    kind: EdgeKind = EdgeKind.ClusterRef

### Cluster Node ####
class ClusterMetadata(BaseModel):
    imports: List[ChunkImport]

# TODO: not ideal since we to have all deserialize logic inside the class
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
               return_summaries: bool = False) -> str:
        name = self.id if not self.summary else self.summary.title
        s = f"Cluster {name}\n"
        s += f"Summary: {self.summary.get_content()}\n" if self.summary and return_summaries else ""
        
        for chunk in self.chunks:
            chunk_str = chunk.to_str(return_content)
            s += "  " + chunk_str.replace("\n", "\n  ") + "\n"

        if self.children:
            s += f"Children ({len(self.children)}):\n"
            for child in self.children:
                child_str = child.to_str(return_content)
                s += "  " + child_str.replace("\n", "\n  ") + "\n"

        return s

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary.dict(),
            "chunks": [chunk.__dict__ for chunk in self.chunks],
            "children": [child.to_dict() for child in self.children],
        }
        
    @classmethod
    def from_json(cls, data: Dict):
        # Process chunks
        processed_chunks = [
            CodeChunk.from_json(chunk) for chunk in data["chunks"]
        ]
    
        # Process children recursively 
        processed_children = [
            Cluster.from_json(child) for child in data["children"]
        ]

        # Create instance
        result = cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            chunks=processed_chunks,
            children=processed_children
        )

        return result   
    
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
        for child in cluster_graph.children(cluster_id, edge_types=[EdgeKind.ChunkToCluster, 
                                                           EdgeKind.ClusterToCluster]):
            if child == cluster_id:
                raise ValueError(f"Cluster {cluster_id} has a self-reference")

            child_node: ChunkNode = cluster_graph.get_node(child)
            if child_node.kind == NodeKind.Chunk:
                chunk_info = cluster_graph.node_to_chunk(child, return_content=return_content)
                chunks.append(chunk_info)
            elif child_node.kind == NodeKind.Cluster:
                children.append(cluster_graph.node_to_cluster(child, return_content=return_content))

        return Cluster(
            id=cluster_node.id,
            title=cluster_node.title,
            summary=cluster_node.summary,
            metadata=cluster_node.metadata,
            chunks=chunks,
            children=children,
        )


    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        if len(self.chunks) != len(other.chunks):
            return False
        
        chunks_equal = all([chunk == other_chunk for chunk, other_chunk in zip(self.chunks, other.chunks)])
        return self.id == other.id and chunks_equal
    
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


@dataclass(kw_only=True)
class ClusterNode(Node):
    kind: NodeKind = NodeKind.Cluster
    title: str = ""
    summary: ClusterSummary = None
    metadata: ClusterMetadata = None

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
            "metadata": self.metadata.dict() if self.metadata else None
        }        