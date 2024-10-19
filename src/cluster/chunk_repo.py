import argparse
from pathlib import Path
from typing import List
from llama_index.core.schema import BaseNode
from dataclasses import field, dataclass
import tempfile
import os
import json
from enum import Enum
import random

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.transforms.cluster import cluster as cluster_cg

from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs.chunk_resolution.graph import (
    FunctionContext,
    ScopeType,
    ChunkContext,
    ImportEdge as RefToEdge,
)
from src.index.service import get_or_create_index
from src.cluster.types import CodeChunk, ClusterInputType
from src.config import GRAPH_ROOT
@dataclass
class ChunkCtxtNode:
    ctxt_list: List[ChunkContext]
    base_node: BaseNode = field(default=None)

    def ctxt_str(self):
        return "\n".join(str(ctxt) for ctxt in self.ctxt_list)


def get_chunk_ctxt_nodes(chunks: List[BaseNode]):
    for chunk in chunks:
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
                    curr_func = FunctionContext(name=node.text.decode(), args_list=[])
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

        yield chunk, [module_ctxt] + class_ctxts


def process_directory(directory, exclusions):
    tree = []
    content = []
    directory = Path(directory)

    def should_exclude(path: Path):
        for pattern in exclusions:
            if path.match(pattern):
                return True
        return False

    def process_item(item, prefix="", is_last=False):
        if should_exclude(item):
            return

        current_prefix = "└── " if is_last else "├── "
        tree.append(f"{prefix}{current_prefix}{item.name}")

        if item.is_dir():
            contents = sorted(
                item.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            )
            for i, subitem in enumerate(contents):
                is_last_subitem = i == len(contents) - 1
                extension = "    " if is_last else "│   "
                process_item(subitem, prefix + extension, is_last_subitem)
        elif item.suffix == ".py":
            with open(item, "r", encoding="utf-8") as f:
                try:
                    file_content = f.read()
                    content.append(f"# File: {item}\n\n{file_content}\n\n")
                except UnicodeDecodeError as e:
                    print(f"Error reading {item}: {e}")
                    return

    contents = sorted(
        directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
    )
    for i, item in enumerate(contents):
        process_item(item, is_last=(i == len(contents) - 1))

    return tree, content

def temp_index_dir(repo_name: str):
    temp_dir = tempfile.gettempdir()
    index_dir = Path(temp_dir) / "index" / repo_name
    if not index_dir.exists():
        os.makedirs(index_dir, exist_ok=True)

    print("Saving chunks to file: ", index_dir.resolve())
    return index_dir


#### CHUNKING STRATEGIES ####

class ChunkStrat(str, Enum):
    VANILLA = "vanilla"
    HYBRID = "hybrid"
    RANDOM = "random"

def chunk_vanilla(repo_dir: Path, mode: str = "full", exclusions=[]) -> List[CodeChunk]:
    cluster_input = []
    index_dir = temp_index_dir(repo_dir.name)
    chunk_index = get_or_create_index(str(repo_dir), str(index_dir), exclusions=exclusions)
    chunk_nodes = chunk_index._docstore.docs.values()

    print(f"[Chunker]: {len(chunk_nodes)} chunks used")

    chunk_fp, chunk_i = list(chunk_nodes)[0].metadata["file_path"], 1
    for chunk_ctxt in get_chunk_ctxt_nodes(chunk_nodes):
        chunk_node, ctxt_list = chunk_ctxt

        if chunk_fp == chunk_node.metadata["file_path"]:
            chunk_i += 1
        else:
            chunk_fp = chunk_node.metadata["file_path"]
            chunk_i = 1

        short_name = f"{os.path.sep}".join(chunk_fp.split(os.path.sep)[-2:])
        node_id = f"{short_name}::{chunk_i}"
        
        if mode == "full":
            cluster_input.append(
                CodeChunk(
                    id= node_id,
                    metadata=chunk_node.metadata,
                    node_id=node_id,
                    input_type=ClusterInputType.FILE, 
                    content=chunk_node.get_content().replace("\r\n", "\n"),
                    filepath=chunk_node.metadata["file_name"],
                ),
            )
        elif mode == "partial":
            cluster_input.append(
                CodeChunk(
                    id= node_id,
                    metadata=chunk_node.metadata,
                    node_id=node_id,                    input_type=ClusterInputType.CHUNK,
                    content="\n".join([str(ctxt) for ctxt in ctxt_list]) + "\n"),
                    metadata=chunk_node.metadata,
            )
            
    return cluster_input

def chunk_hybrid(repo_dir: Path, mode: str = "full", exclusions=[]) -> List[CodeChunk]:
    chunks = chunk_vanilla(repo_dir, mode="full", exclusions=exclusions)
    ell_json = json.loads(open(GRAPH_ROOT / "MadcowD_ell_standard.json", "r").read())
    cg = ChunkGraph.from_json(repo_dir, ell_json)

    cluster_cg(cg)

    graph_chunks = [
        CodeChunk(
            id=chunk.og_id,
            content=chunk.content,
            filepath=chunk.file_path,
            input_type=ClusterInputType.CHUNK
        )
        for cluster 
        in cg.get_clusters() for chunk in cluster.chunks
    ]
    left_chunks = [chunk for chunk in chunks if chunk not in graph_chunks]

    for i, c in enumerate(graph_chunks):
        print(f"Chunk {i}:")
        print(c.id)

    return graph_chunks + left_chunks

def chunk_random(repo_dir: Path, mode: str = "full", exclusions=[]) -> List[CodeChunk]:
    chunks = chunk_repo(repo_dir, ChunkStrat.RANDOM, mode="full", exclusions=exclusions)
    return random.shuffle(chunks)

def chunk_repo(repo_dir: Path, 
               chunk_strat: ChunkStrat,
               mode: str = "full", 
               exclusions=[]) -> List[CodeChunk]:
    
    if chunk_strat == ChunkStrat.VANILLA:
        return chunk_vanilla(repo_dir, mode=mode, exclusions=exclusions)
    elif chunk_strat == ChunkStrat.HYBRID:
        return chunk_hybrid(repo_dir, mode=mode, exclusions=exclusions)
    elif chunk_strat == ChunkStrat.RANDOM:
        return chunk_random(repo_dir, mode=mode, exclusions=exclusions)
    else:
        raise ValueError(f"Invalid chunking strategy: {chunk_strat}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Concatenate Python files in a directory and generate a directory tree, with exclusions."
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument("--strattype", type=ChunkStrat, choices=list(ChunkStrat), default=ChunkStrat.VANILLA,
                        help="The chunking strategy to use")
    parser.add_argument("-e", "--exclude", action="append", default=[],
                        help="Exclusion patterns (can be used multiple times)")
    # parser.add_argument(
    #     "-f",
    #     "--full",
    #     nargs="*",
    #     default=[],
    #     help="To include whole content or just partial context",
    # )
    args = parser.parse_args()

    # Default exclusions
    default_exclusions = [
        "cowboy_lib/*",
        "rtfs_rewrite/*",
        ".venv/*",
        "notebooks/*",
        "__pycache__/*",
        "*.pyc",
        ".git/*",
        ".idea/*",
        ".vscode/*",
        "node_modules/*",
        "build/*",
        "dist/*",
        "*.egg-info/*",
    ]

    # Combine user-provided exclusions with default exclusions
    exclusions = default_exclusions + args.exclude
    print(f"Exclusion patterns: {exclusions}")

    chunks = chunk_repo(Path(args.directory), chunk_strat=args.strattype, mode="full", exclusions=exclusions)
    
    # Write chunks to chunks.txt
    with open("chunks.txt", "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(f"Chunk ID: {chunk.id}\n")
            f.write(f"Filepath: {chunk.filepath}\n")
            f.write(f"Content:\n{chunk.content}\n")
            f.write("-" * 80 + "\n")
    
    print(f"Chunks have been written to chunks.txt")
