from pathlib import Path
from typing import List, NamedTuple
from llama_index.core.schema import BaseNode

from rtfs.chunk_resolution.graph import ChunkMetadata
from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs.cluster.graph import ClusterGraph

import networkx as nx

from .graph import (
    AltChunkNode,
    AltChunkEdge,
    FunctionContext,
    ScopeType,
    ChunkContext,
)


class AiderGraph(ClusterGraph):
    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[BaseNode]):
        graph = cls(repo_path=repo_path, graph=nx.MultiDiGraph(), cluster_roots=[])

        all_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"Chunk{i}")

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

            node = AltChunkNode(
                id=chunk.node_id,
                og_id=chunk.node_id,
                metadata=ChunkMetadata(**chunk.metadata),
                content=chunk.get_content(),
                ctxt=[module_ctxt] + class_ctxts,
                # TODO: maybe we should add these fields to CHunkNode
                # definitions=definitions,
                # references=references,
            )

            print(node)
            chunk_node = [
                node,
                {"definitions": definitions, "references": references},
            ]
            all_chunks.append(chunk_node)
            graph.add_node(chunk_node[0])

        # build relation ships
        # for c1, refsndefs1 in all_chunks:
        #     for c2, refsndefs2 in all_chunks:
        #         for ref in refsndefs1["references"]:
        #             if (
        #                 ref in refsndefs2["definitions"]
        #                 and c1.id != c2.id
        #                 and not graph.has_edge(c1.id, c2.id)
        #             ):
        #                 edge = AltChunkEdge(src=c1.id, dst=c2.id, ref=ref)
        #                 graph.add_edge(edge)

        return graph
