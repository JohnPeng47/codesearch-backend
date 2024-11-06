from pydantic import BaseModel
import ell

from src.utils import DELIMETER
from src.cluster.models import ClusteredTopic

class IndexChoice(BaseModel):
    index: int

@ell.complex(model="gpt-4o-2024-08-06", response_format=IndexChoice)
def eval_compare_clusters(*clusters: ClusteredTopic):
    unique_chunks = set([
        chunk for cluster in clusters for chunk in cluster.chunks
    ])
    all_chunk_code = "\n".join([chunk.get_content() + DELIMETER for chunk in unique_chunks])
    clusters_str = DELIMETER.join([str(f"Cluster {i}:\n" + str(cluster)) for i, cluster in enumerate(clusters)])

    EVAL_COMPARE = """
You are given the following set of source code chunks:
{code}

Your task is to compare the following clusters and choose which cluster forms a more cohesive grouping of source code chunks. You should
penalize a cluster for including too much unrelated code or for missing important code that should have been included.
Here are the clusters:
{clusters}


Now output your decision by selecting the number of the cluster that you would score higher on overall cohesion
"""
    return EVAL_COMPARE.format(code=all_chunk_code, clusters=clusters_str)
