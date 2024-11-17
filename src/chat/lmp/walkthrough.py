import re
from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Optional
from llm import LLMModel
import uuid
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from src.chat.models import WalkthroughChat, WalkthroughData
from src.chat.models import SrcMetadata
from rtfs.cluster.graph import Cluster
from src.exceptions import LLMException
from src.utils import DELIMETER

from .utils import get_src_metadata, clean_markdown

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
Add a single sentence description of the transition taking place, with references to code entities
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
    return output

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
    mkdown = clean_markdown(llm_res)
    src_metadata = get_src_metadata(mkdown, clusters)

    return llm_res, src_metadata

@retry(
    wait=wait_random_exponential(min=1, max=15),
    reraise=True,
    stop=stop_after_attempt(3),
    after=lambda retry_state: print(f"Retry attempt failed with exception: {retry_state.outcome.exception()}"),
)
def generate_chat_transition_rolled(model: LLMModel,
                                    prev_chat: str,
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
"""
    PREV_CHAT_PROMPT = """
Now write a more short summary of the transition, including references to code entities and how they interact
Connect your output to this previously generated step, and make the flow smooth
{prev_chat}
""".format(prev_chat=prev_chat) if prev_chat else "Now write a more short summary of the transition, including references to code entities and how they interact"
    
    CHAT_TRANSITION += PREV_CHAT_PROMPT

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

    mkdown = clean_markdown(llm_res)
    src_metadata = get_src_metadata(mkdown, clusters)
    if not src_metadata:
        raise LLMException("No SrcMetadata generated")
    
    return llm_res, src_metadata


class LMChat(BaseModel):
    content: str
    name: Optional[str]

class ChatList(BaseModel):
    chats: List[LMChat]

def post_process_smooth(model: LLMModel,
                        walkthrough: str,
                        prev_chats: List[Dict]) -> ChatList:
    chat_str = "Name: {name}\n{content}"
    prev_chat_str = f"\n{DELIMETER}".join([chat_str.format(name=c["name"], content=c["content"]) for c in prev_chats])

    SMOOTH_TRANSITION_CHATS = """
You are given a list of the chats aimed at walking a user through a code feature. The code feature is described below:
{walkthrough}

Each of these chats are generated individually wrt to a specific part of the feature, without taking into consideration the previous chat
Your task is to rectify this, and introduce a smooth transition between the chats.
You should also add a proper introduction to the first chat to introduce the reader to the code feature

Here are the previous chats:
{prev_chats}
"""
    return model.invoke(
        SMOOTH_TRANSITION_CHATS.format(
            walkthrough=walkthrough,
            prev_chats=prev_chat_str
        ),
        model_name="gpt-4o",
        response_format=ChatList
    )

class ChatName(BaseModel):
    name: str
 
def post_process_name(model: LLMModel,
                      chat: str) -> ChatName:
    GEN_CHAT_NAME = """
Given the following chat message that describes a code feature, come up with a name for it:
{chat}
"""
    return model.invoke(
        GEN_CHAT_NAME.format(chat=chat),
        model_name="gpt-4o",
        response_format=ChatName
    )


# TODO: make this return Walkthrough
# we should really design the following primitive:
def generate_walkthroughs(model: LLMModel,
                            summary: str,
                            transitions: List[Transition],
                            matched_clusters: List[Cluster]) -> List[WalkthroughChat]:
    # generate initial transition chats
    all_chats = []
    prev_chat = ""
    for i, t in enumerate(transitions):
        content, metadata = generate_chat_transition_rolled(model, prev_chat, t, matched_clusters, summary)
        chat_name = post_process_name(model, content).name
        prev_chat = content
        all_chats.append(
            {
                "id": str(uuid.uuid4()),
                "content": content,
                "metadata": metadata,
                "name": chat_name
            }
        )   

    # NOTE: parse to LMChat, which is an internal LM representation used for this function
    chat_list = post_process_smooth(model, summary, all_chats).chats
    for i, chat in enumerate(all_chats):
        for smooth_chat in chat_list:
            if smooth_chat.name == chat["name"]:
                all_chats[i]["content"] = smooth_chat.content
                break

    walkthroughs = []
    for i, chat in enumerate(all_chats):
        content = chat["content"]
        metadata = chat["metadata"]
        id = chat["id"]
        next_chat = all_chats[i+1]["id"] if i < len(all_chats) - 1 else None
        data = WalkthroughData(next_chat=next_chat, metadata=metadata)
        walkthrough = WalkthroughChat(content=content,
                                    metadata=data,
                                    id=id)
        walkthroughs.append(walkthrough)
    
    # TODO: generate a name for the chat tab
    return walkthroughs
    
# def construct_walkthroughs(all_chats: Dict):
#     walkthroughs = []
#     for i, chat in enumerate(all_chats):
#         content = chat["content"]
#         metadata = chat["metadata"]
#         id = chat["id"]
#         next_chat = all_chats[i+1]["id"] if i < len(all_chats) - 1 else None
#         data = WalkthroughData(next_chat=next_chat, metadata=metadata)
#         walkthrough = WalkthroughChat(content=content,
#                                     metadata=data,
#                                     id=id)
#         walkthroughs.append(walkthrough)
    
#     # TODO: generate a name for the chat tab
#     return walkthroughs, all_chats