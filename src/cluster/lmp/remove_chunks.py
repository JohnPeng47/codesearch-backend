from pydantic import BaseModel
from typing import List
import ell

from src.cluster.models import ClusteredTopic
from src.utils import DELIMETER

class ToRemove(BaseModel):
    remove: List[str]

@ell.complex(model="gpt-4o-mini", response_format=ToRemove)
def remove_chunks(cluster: ClusteredTopic):
    cluster_code = "\n".join([str(chunk) + DELIMETER for chunk in cluster.chunks])

    TO_REMOVE = """
You are given a cluster that is the output of a clustering algorithm designed to group together code from related features. 
The algorithm that generated the cluster has identified these chunks as working together to form a cohesive functional unit. It is prone to making
mistakes so its your job to identify what code should be remove from the cluster to make it more coherent.
Here is the code cluster:

{code}

Now give your output with the name of the chunks to be removed 
"""
    return TO_REMOVE.format(code=cluster_code)
