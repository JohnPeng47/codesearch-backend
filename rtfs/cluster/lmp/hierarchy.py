from typing import List, Dict, Type
from llm import LLMModel
from rtfs.cluster.graph import Cluster
from rtfs.graph import CodeGraph
from rtfs.graph import Node
from src.utils import DELIMETER, extract_json_code
from pydantic import BaseModel

import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)
from abc import ABC, abstractmethod
from .graph_ops import MoveOp, CreateOp, GraphOp


# class GraphOp(ABC):
#     @abstractmethod
#     def apply(self, graph: CodeGraph):
#         raise NotImplementedError

#     @abstractmethod
#     def prompt(self) -> str:
#         raise NotImplementedError


# class CreateOp:
#     def __init__(self, title: str, node_constr: List[Type[Node]], **kwargs):
#         self.title = title
#         self.node_args = kwargs
#         self.node_constr = {nc.__name__: nc for nc in node_constr}
    
#     def op_prompt(self) -> str:
#         node_kinds = "[" + list(self.node_constr.keys()) + "]"
#         return f""

#     def apply(self, node_kind: str, graph: CodeGraph):
#         constructor = self.node_constr[node_kind]
#         node = constructor(**self.node_args)
#         graph.add_node(node)

#     def response_format(self) -> BaseModel:
#         class GraphOp:
#             title: str
#         return 


class ParentCluster:
    name: str
    child_names: List[str]

class ParentClusterList:
    parent_clusters: List[ParentCluster]


# NEWTODO: currently only allowing
@retry(
    wait=wait_random_exponential(min=1, max=15),
    reraise=True,
    stop=stop_after_attempt(3),
    retry=retry_if_not_exception_type((RuntimeError)),
)
def create_2tier_hierarchy(model: LLMModel, clusters: List[Cluster]) -> List[GraphOp]:
    CREATE_HIERARCHY = """
TASK
Here are some code clusters:
{cluster_str}
    
Form parent clusters to group these current clusters into some higher level categories

ACTIONS
You can perform two actions:
CreateOp
AdoptCluster

Note that the order of operations matter and take care to create a node before adopting a cluster into it.
Note when creating a cluster id make it alot larger than the ids in the clusters to avoid collisions.

Here is an example:
{{
    "operations": [
        {{
            "op_type": "CreateOp",
            "id": "integer",
            "title": "string",
            "kind": "ClusterNode"
        }},
        {{
            "op_type": "AdoptCluster", 
            "child_cluster": "integer",
            "parent_cluster": "integer"
        }},
        {{
            "op_type": "AdoptCluster", 
            "child_cluster": "integer",
            "parent_cluster": "integer"
        }}
        ...
    ]
}}

Return the list of operations in JSON format.
"""
    res = model.invoke(
        CREATE_HIERARCHY.format(cluster_str=f"\n\n{DELIMETER}".join(
            [cluster.to_str(return_summaries=True, return_imports=False) for cluster in clusters])
        ), 
        model_name="gpt-4o"
    )
    res = json.loads(extract_json_code(res))
    return [GraphOp(**op).to_op() for op in res["operations"]]

@retry(
    wait=wait_random_exponential(min=1, max=15),
    reraise=True,
    stop=stop_after_attempt(3),
    retry=retry_if_not_exception_type((RuntimeError)),
)
def create_2tier_hierarchy_with_existing(model: LLMModel, 
                                         leftover: List[Cluster],
                                         parents: Dict) -> List[GraphOp]:
    CREATE_HIERARCHY = """
TASK
Here are some ungrouped clusters from leftover from a clustering algorithm:
{cluster_str}
    
Here are some parent groups that have been formed:
{parents}

Now for each of the ungrouped clusters, either:
1. Create a new parent group that fits the cluster
2. Assign them to an existing parent group

ACTIONS
You can perform two actions:
CreateOp
AdoptCluster

Note that the order of operations matter and take care to create a node before adopting a cluster into it.
Note when creating a cluster id make it alot larger than the ids in the clusters to avoid collisions.

Here is an example:
{{
    "operations": [
        {{
            "op_type": "CreateOp",
            "id": "integer",
            "title": "string",
            "kind": "ClusterNode"
        }},
        {{
            "op_type": "AdoptCluster", 
            "child_cluster": "integer",
            "parent_cluster": "integer"
        }},
        {{
            "op_type": "AdoptCluster", 
            "child_cluster": "integer",
            "parent_cluster": "integer"
        }}
        ...
    ]
}}
"""
    prompt = CREATE_HIERARCHY.format(
            cluster_str=f"\n\n{DELIMETER}".join(
                [
                    cluster.to_str(return_summaries=True, return_imports=False) for cluster in leftover
                ]
            ),
            parents="\n".join(
                [
                    f"Parent: {parent}\nChildren: {children}" for parent, children in parents.items()
                ]
            )
        )
    print(prompt)
    
    res = model.invoke(
        CREATE_HIERARCHY.format(
            cluster_str=f"\n\n{DELIMETER}".join(
                [
                    cluster.to_str(return_summaries=True, return_imports=False) for cluster in leftover
                ]
            ),
            parents="\n".join(
                [
                    f"Parent: {parent}\nChildren: {children}" for parent, children in parents.items()
                ]
            )
        ),
        model_name="gpt-4o"
    )
    print(res)
    res = json.loads(extract_json_code(res))
    return [GraphOp(**op).to_op() for op in res["operations"]]
