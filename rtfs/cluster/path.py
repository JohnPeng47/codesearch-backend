from .graph import Cluster, ClusterChunk

from typing import List, Tuple, Set
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
    
    def __hash__(self):
        return hash((self.src_chunk.id, self.ref, self.dst_chunk.id))

    def __eq__(self, other):
        if not isinstance(other, ChunkPathSegment):
            return False
        return (self.src_chunk.id == other.src_chunk.id and
                self.ref == other.ref and
                self.dst_chunk.id == other.dst_chunk.id)

class ClusterPathSegment:
    """
    Represents multiple paths from src_cluster to dst_cluster via the ref list
    """
    def __init__(self, 
                 src_cluster: Cluster,
                 dst_cluster: Cluster,
                 paths: Set[ChunkPathSegment]):
        self.src_cluster = src_cluster
        self.dst_cluster = dst_cluster
        self.paths = paths

    def __len__(self):
        return len(self.paths)
    
    def __hash__(self):
        """
        Hash based on cluster IDs and frozen set of paths
        """
        return hash((self.src_cluster.id, 
                    self.dst_cluster.id, 
                    frozenset(self.paths)))
    
    def __eq__(self, other):
        if not isinstance(other, ClusterPathSegment):
            return False
        return (self.src_cluster.id == other.src_cluster.id and
                self.dst_cluster.id == other.dst_cluster.id and
                self.paths == other.paths)

class ClusterPath:
    def __init__(self, segments: List[ClusterPathSegment] = None):
        self.segments = segments if segments else []

    def add_segment(self, segment: Tuple):
        new_segment = ClusterPathSegment(*segment)
        if new_segment not in self.segments:
            self.segments.append(new_segment)

    def find_cluster(self, name):
        for segment in self.segments:
            if segment.src_cluster.title == name:
                return self
            if segment.dst_cluster.title == name:
                return self
        return None

    def __len__(self):
        return sum([len(seg) for seg in self.segments])

    def __hash__(self):
        return hash(frozenset(self.segments))
    
    def __eq__(self, other):
        if not isinstance(other, ClusterPath):
            return False
        return self.segments == other.segments

    def to_str(self, verbose: bool = False, show_refs: bool = False):
        path_str = ""
        if not self.segments:
            return path_str
            
        # Add first source cluster and its chunk paths
        path_str += list(self.segments)[0].src_cluster.title
        chunk_paths = "\n".join([str(path) for path in list(self.segments)[0].paths])
        path_str +=  ("\n" + chunk_paths) if verbose else ""

        # Add each subsequent segment
        for segment in self.segments:
            if show_refs:
                refs = [path.ref for path in segment.paths]
                path_str += f"\n-[{', '.join(refs)}]-> {segment.dst_cluster.title}"
            else:
                path_str += f"\n-> {segment.dst_cluster.title}"
            chunk_paths = "\n".join([str(path) for path in segment.paths])
            path_str += ("\n" +  chunk_paths) if verbose else ""
            
        return path_str

    # def to_str_simple(self):
    #     for i in range(1, len(self.segments) - 1):
    #         src_cluster = self.segments[i].src_cluster
    #         print(f"{segment.src_cluster.title} -> {segment.dst_cluster.title}")