from .graph import Cluster, ClusterChunk

from typing import List, Tuple
from dataclasses import dataclass


class ChunkPathSegment:
    """
    A single ref connection between two chunks
    """
    def __init__(self, 
                 src_chunk: ClusterChunk, 
                 ref: str, 
                 dst_chunk: ClusterChunk):
        self.src_chunk = src_chunk
        self.dst_chunk = dst_chunk
        self.ref = ref

    def __str__(self):
        return f"[{self.src_chunk.id} ] --{self.ref}--> [{self.dst_chunk.id}]"

class ClusterPathSegment:
    """
    Represents multiple paths from src_cluster to dst_cluster via the ref list
    """
    def __init__(self, 
                 src_cluster: Cluster,
                 dst_cluster: Cluster,
                 paths: List[ChunkPathSegment]):
        self.src_cluster = src_cluster
        self.dst_cluster = dst_cluster
        self.paths = paths

    def __len__(self):
        return len(self.paths)
    
class ClusterPath:
    def __init__(self, segments: List[ClusterPathSegment] = None):
        self.segments: List[ClusterPathSegment] = segments if segments else []

    def add_segment(self, segment: Tuple):
        self.segments.append(ClusterPathSegment(*segment))

    def find_cluster(self, name):
        for segment in self.segments:
            if segment.src_cluster.title == name:
                return self
            if segment.dst_cluster.title == name:
                return self
        return None

    def __len__(self):
        return sum([len(seg) for seg in self.segments])

    def to_str(self):
        path_str = ""
        if not self.segments:
            return path_str
            
        # Add first source cluster and its chunk paths
        path_str += self.segments[0].src_cluster.title
        chunk_paths = "\n".join([str(path) for path in self.segments[0].paths])
        path_str += "\n" + chunk_paths

        # Add each subsequent segment
        for segment in self.segments:
            path_str += f"\n-> {segment.dst_cluster.title}"
            chunk_paths = "\n".join([str(path) for path in segment.paths])
            path_str += "\n" + chunk_paths
            
        return path_str
