from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel
from rtfs.graph import Edge, Node

@dataclass(kw_only=True)
class ClusterNode(Node):
    kind: str = "ClusterNode"
    title: str = ""
    summary: str = ""
    key_variables: List[str] = field(default_factory=list)
    
    def get_content(self):
        return self.summary

    def __hash__(self):
        return hash(self.id)

class ClusterEdgeKind(str, Enum):
    ChunkToCluster = "ChunkToCluster"
    ClusterToCluster = "ClusterToCluster"

@dataclass(kw_only=True)
class ClusterEdge(Edge):
    kind: Literal[ClusterEdgeKind.ClusterToCluster, ClusterEdgeKind.ChunkToCluster]

@dataclass(kw_only=True)
class ClusterChunk:
    id: str
    og_id: str
    file_path: str
    start_line: int
    end_line: int
    content: Optional[str] = ""

    def to_str(self, return_content: bool = False) -> str:
        s = f"Chunk: {self.id}"
        if return_content and self.content:
            s += f"\n{self.content}"
        return s

@dataclass(kw_only=True)
class Cluster:
    id: str
    title: str
    key_variables: List[str]
    summary: str
    chunks: List[ClusterChunk]
    children: List["Cluster"]

    def to_str(self, return_content: bool = False) -> str:
        s = f"Cluster {self.id}: {self.title}\n"
        s += f"Summary: {self.summary}\n"
        s += f"Chunks ({len(self.chunks)}):\n"
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
            "key_variables": self.key_variables,
            "summary": self.summary,
            "chunks": [chunk.__dict__ for chunk in self.chunks],
            "children": [child.to_dict() for child in self.children],
        }

class ClusterGStats(BaseModel):
    num_clusters: int
    num_chunks: int
    avg_cluster_sz: float

    def __str__(self):
        return f"""
Clusters: {self.num_clusters}, 
Chunks: {self.num_chunks}, 
Avg Cluster Size: {self.avg_cluster_sz:.2f}
        """

@dataclass
class ClusterRefEdge(Edge):
    ref: str
    kind: str = "ClusterRef"
