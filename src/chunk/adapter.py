from pathlib import Path
from typing import List

from rtfs.cluster.graph import SummarizedCluster
from src.cluster.models import ClusteredTopic
from src.chunk.models import CodeChunk

def convert_rtfs_cluster(cluster: SummarizedCluster) -> ClusteredTopic:    
    chunks: List[CodeChunk] = []
    
    for chunk in cluster.chunks:
        code_chunk = CodeChunk(
            input_type="chunk",
            id=chunk.id,
            content=chunk.content,
            filepath=chunk.file_path
        )
        chunks.append(code_chunk)
    
    return ClusteredTopic(
        name=cluster.title,
        chunks=[c.dict() for c in chunks]
    )

def convert_rtfs_clusters(clusters: List[SummarizedCluster]) -> List[ClusteredTopic]:
    return [convert_rtfs_cluster(cluster) for cluster in clusters if cluster.chunks]