import re
from pydantic import BaseModel
from typing import List, Dict, Tuple
from llm import LLMModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)

from rtfs.cluster.graph import Cluster
from .utils import get_src_metadata
from ..models import WalkthroughChat

# TODO: should move all of this into src
class Transition(BaseModel):
    src_cluster: int
    dst_cluster: int
    description: str

class TransitionList(BaseModel):
    transitions: List[Transition]

# TODO: add optional to start with a cluster
def identify_transitions(model: LLMModel, 
                         clusters: List[Cluster], 
                         walkthrough: str,
                         start_cluster: int = None) -> TransitionList:
    cluster_str = "\n".join([cluster.to_str(return_content=True) for cluster in clusters])

    IDENTIFY_TRANSITIONS = """
Here is a walkthrough of a codebase:
{walkthrough}
    
Here are a list of the clusters:
{clusters}

Identify a list of cluster transitions that take place, where the src and dst clusters are the cluster ids. 
Add a description of the transition taking place, with references to code entities
Only add a single transition between clusters 
"""

    START_CLUSTER = """
Start with the following cluster: {start_cluster}
"""
    IDENTIFY_TRANSITIONS = IDENTIFY_TRANSITIONS + (START_CLUSTER.format(start_cluster=start_cluster) if start_cluster is not None else "")

    return model.invoke(
        IDENTIFY_TRANSITIONS.format(walkthrough=walkthrough, clusters=cluster_str), 
        model_name="gpt-4o",
        response_format=TransitionList
    )

@retry(
    wait=wait_random_exponential(min=1, max=15),
    reraise=True,
    stop=stop_after_attempt(3),
    after=lambda retry_state: print(f"Retry attempt failed with exception: {retry_state.outcome.exception()}"),
)
def generate_chat_transition(model: LLMModel,
                             transition: Transition,
                             clusters: List[Cluster],
                             walkthrough: str) -> Tuple[str, Dict]:
    src_cluster = next(cluster for cluster in clusters if cluster.id == transition.src_cluster)
    dst_cluster = next(cluster for cluster in clusters if cluster.id == transition.dst_cluster)

    CHAT_TRANSITION = """
The following walkthrough describes a feature that spans several code clusters in a codebase:
{walkthrough}

Here is an overview of the clusters in the codebase:
{clusters}

You are tasked with writing a short summary of the transition between cluster {src_cluster} and cluster {dst_cluster}.
Here are their respective source code:
Source cluster:
{src_code}

Destination cluster:
{dst_code}

Here is a brief description of the transition:
{description}

Some additional guidance to follow:
- a list of code related features. this section should include the id of the chunk that is being referenced enclosed in [_KEYPHRASE_][[]], which will be specially parsed by the client, where _KEYPHRASE_ is a word/phrase that is referenced in the chunk
- do not refer to clusters explicitly in your explanation
- limit your discussion only to the relevant part described by the walkthrough

Here is an example:
....
- The [search() function][[src/vector.py::1]] uses an exclusion filter to exclude certain search terms from the result

Now write a more short summary of the transition, including references to code entities and how they interact
"""
    llm_res = model.invoke(
        CHAT_TRANSITION.format(walkthrough=walkthrough,
                               clusters="\n".join([c.to_str(return_content=True) for c in clusters]),
                               src_cluster=src_cluster.id,
                               dst_cluster=dst_cluster.id,
                               src_code=src_cluster.to_str(return_content=True),
                               dst_code=dst_cluster.to_str(return_content=True),
                               description=transition.description),
        model_name="gpt-4o"
    )
    src_metadata = get_src_metadata(llm_res, clusters)
    return llm_res, src_metadata

def cluster_wiki(model: LLMModel, cluster: Cluster) -> str:
    cluster_str = cluster.to_str(return_content=True)
    CLUSTER_WIKI = """
Generate a summary of this cluster in the form of a wiki page. The general structure of the wiki page should be:
- the title of the cluster
- an overview of the code in the cluster. this should be in the form of a well structured paragraph that flows along well with smooth narration
- a list of code related features. this section should include the id of the chunk that is being referenced enclosed in [_KEYPHRASE_][[]], which will be specially parsed by the client, where _KEYPHRASE_ is a word/phrase that is referenced in the chunk

Here is an exampe of a wiki page:
....
- The [search() function][[src/vector.py:1]] uses an exclusion filter to exclude certain search terms from the result

{cluster}
"""
    output = model.invoke(    
        CLUSTER_WIKI.format(cluster=cluster_str),
        model_name="gpt-4o"
    )