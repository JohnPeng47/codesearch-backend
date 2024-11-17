from typing import List, Dict
import re
from functools import reduce

from rtfs.cluster.cluster_graph import Cluster
from ..models import SrcMetadata

def get_src_metadata(content: str, clusters: List[Cluster]) -> Dict[str, SrcMetadata]:
    chunk_metadata = {}
    chunk_files = re.findall("\[\[(.*?)\]\]", content)
    cluster_chunks = [chunk for cluster in clusters for chunk in cluster.chunks]

    for f in chunk_files:
        chunk = next(filter(lambda c: c.id == f, cluster_chunks), None)
        if not chunk:
            raise Exception(f"{f} is hallucinated")
        
        chunk_metadata[f] = SrcMetadata(
            filepath=chunk.file_path,
            start_line=chunk.start_line, 
            end_line=chunk.end_line
        )
    
    return chunk_metadata

def clean_markdown(mkdown: str):
    def clean_backticks_in_brackets(content: str):
        pattern = r'`\[(.*?)\]\[\[(.*?)\]\]`'
        content = re.sub(pattern, r'[`\1`][[\2]]', content)
        return content
    
    clean_funcs = [
        clean_backticks_in_brackets
    ]
    
    return reduce(lambda x, f: f(x), clean_funcs, mkdown)