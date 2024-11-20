from pathlib import Path
from typing import List, NamedTuple
from llama_index.core.schema import BaseNode

from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs.cluster.cluster_graph import ClusterGraph
from rtfs.chunk_resolution.graph import (
    ChunkNode,
    FunctionContext,
    ScopeType,
    ChunkContext,
    ImportEdge as RefToEdge,
)

from src.cluster.models import CodeChunk
import networkx as nx


class AiderGraph(ClusterGraph):
    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[CodeChunk]):
        graph = cls(repo_path=repo_path, graph=nx.MultiDiGraph(), cluster_roots=[])

        all_chunks = []
        for i, chunk in enumerate(chunks):
            definitions = []
            references = []
            module_ctxt = ChunkContext(
                scope_name="module", scope_type=ScopeType.MODULE, functions=[]
            )
            class_ctxts: List[ChunkContext] = []
            curr_scope = module_ctxt
            curr_func = None
            end_class = False

            for node, capture_name in cap_ts_queries(
                bytearray(chunk.get_content(), encoding="utf-8"), TSLangs.PYTHON
            ):
                match capture_name:
                    case "name.definition.class":
                        class_name = node.text.decode()
                        definitions.append(class_name)
                        ctxt = ChunkContext(
                            scope_name=class_name,
                            scope_type=ScopeType.CLASS,
                            functions=[],
                        )
                        class_ctxts.append(ctxt)
                        curr_scope = ctxt
                    case "name.definition.function":
                        curr_func = FunctionContext(
                            name=node.text.decode(), args_list=[]
                        )
                        curr_scope.functions.append(curr_func)
                        if end_class:
                            curr_scope = module_ctxt
                            end_class = False
                    case "parameter.definition.function":
                        curr_func.args_list.append(node.text.decode())
                    # TS query for class parses the last block before the last function
                    # which is why we need to set this here and handle the ctx change in
                    # function definitions
                    case "class.definition.end":
                        end_class = True
                    case "name.reference.call":
                        references.append(node.text.decode())

            node = ChunkNode(
                id=chunk.node_id,
                metadata=chunk.metadata,
                content=chunk.get_content(),
                ctxt_list=[module_ctxt] + class_ctxts,
                # TODO: maybe we should add these fields to CHunkNode
                definitions=definitions,
                references=references,
            )
            all_chunks.append(node)
            graph.add_node(node)

        # build relation ships
        for c1 in all_chunks:
            for c2 in all_chunks:
                for ref in c1.references:
                    if (
                        ref in c2.definitions
                        and c1.id != c2.id
                        and not graph.has_edge(c1.id, c2.id)
                    ):
                        edge = RefToEdge(src=c1.id, dst=c2.id, ref=ref)
                        graph.add_edge(edge)

        return graph
