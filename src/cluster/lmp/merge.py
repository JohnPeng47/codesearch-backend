from typing import List
from enum import Enum
import ell

from src.chunk.models import ClusterInput
from ..models import (
    ClusteredTopic,
    LMClusteredTopicList,
    LMClusteredTopic
)

DELIMETER = f"\n\n{'-' * 80}\n" # only 1 tokens good deal!

class ChunkType(str, Enum):
    LOGIC = "\{code\}"
    DATA_STRUCTURE = "\{data_structure\}"


# TODO: try again with code at the top of the prompt to trigger caching
@ell.complex(model="gpt-4o-2024-05-13")
def merge(clusters: List[ClusteredTopic]) -> LMClusteredTopicList:
    clusters = "\n".join([str(cluster) for cluster in clusters])

    # TODO: should actually make a template out of this prompt so the first line
    # can be obvious for caching purposes
    MERGE_CLUSTERS = """
The following are clusters created thet 

"""
