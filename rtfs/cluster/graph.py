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

@dataclass
class ClusterRefEdge(Edge):
    ref: str
    kind: str = "ClusterRef"

# Note: only ClusterChunk and Cluster can be pydantic BaseModel
# because it provides too much latency during graph construction
class ClusterChunk(BaseModel):
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

class Cluster(BaseModel):
    id: int
    title: str
    # key_variables: List[str]
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
            # "key_variables": self.key_variables,
            "summary": self.summary,
            "chunks": [chunk.__dict__ for chunk in self.chunks],
            "children": [child.to_dict() for child in self.children],
        }
    
    @classmethod
    def from_json(cls, data: Dict):
        # Control flags
        has_valid_fields = all(field in data for field in 
                               ["id", "title", "summary", "chunks", "children"])
        should_process = has_valid_fields
        
        # Process chunks
        processed_chunks = []
        if should_process:
            processed_chunks = [
                ClusterChunk(
                    id=chunk["id"],
                    og_id=chunk["og_id"], 
                    file_path=chunk["file_path"],
                    start_line=chunk["start_line"],
                    end_line=chunk["end_line"]
                )
                for chunk in data["chunks"]
            ]
        
        # Process children recursively 
        processed_children = []
        if should_process:
            processed_children = [
                Cluster.from_json(child) 
                for child in data["children"]
            ]

        # Create instance
        result = None
        if should_process:
            result = cls(
                id=data["id"],
                title=data["title"],
                # key_variables=data["key_variables"],
                summary=data["summary"],
                chunks=processed_chunks,
                children=processed_children
            )

        return result


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