import argparse
from pathlib import Path
from typing import List, Dict, Type
from llama_index.core.schema import BaseNode
from dataclasses import field, dataclass
import tempfile
import os
import json
from enum import Enum
import random

from src.llm.invoke_mt import invoke_multithread
# from rtfs.chunk_resolution.chunk_graph import ChunkGraph
# from rtfs.transforms.cluster import cluster as cluster_cg

from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs.chunk_resolution.graph import (
    FunctionContext,
    ScopeType,
    ChunkContext,
    ImportEdge as RefToEdge,
)
from src.index.service import get_or_create_index
from src.utils import num_tokens_from_string

from .summarizer import summarize
from .models import CodeChunk, ClusterInputType, SummaryChunk, FILE_CLASSIFICATIONS
from .classify_files import classify_files

from llm import LLMModel

# Default exclusions
DEFAULT_EXCLUSIONS = [
    "versions/*",
    "alembic/*",
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
    "cache/*",
    "*.db",
    "examples/*", 
    "tests/*",
    ".pytest_cache/*",
    ".coverage",
    "htmlcov/*"
]


def temp_index_dir(repo_name: str):
    temp_dir = tempfile.gettempdir()
    index_dir = Path(temp_dir) / "index" / repo_name
    if not index_dir.exists():
        os.makedirs(index_dir, exist_ok=True)

    print("Saving chunks to file: ", index_dir.resolve())
    return index_dir


#### CHUNKING STRATEGIES ####
@dataclass
class ChunkCtxtNode:
    ctxt_list: List[ChunkContext]
    base_node: BaseNode = field(default=None)

    def ctxt_str(self):
        return "\n".join(str(ctxt) for ctxt in self.ctxt_list)



class ChunkStrategy:
    """Base class for chunking strategies"""
    def __init__(self, 
                 repo_dir: Path, 
                 exclusions: List[str] = DEFAULT_EXCLUSIONS,
                 summarize: bool = False):
        self.repo_dir = repo_dir
        self.exclusions = exclusions
        self.summarize = summarize
    
    def chunk(self) -> List[CodeChunk]:
        """Execute the chunking strategy"""
        raise NotImplementedError
    
    def _get_vanilla_chunks(self, index_dir=None) -> List[CodeChunk]:
        """Common method to get vanilla chunks used by multiple strategies"""
        cluster_input = []
        index_dir = index_dir if index_dir else temp_index_dir(self.repo_dir.name)
        chunk_index = get_or_create_index(str(self.repo_dir), str(index_dir), exclusions=self.exclusions)
        chunk_nodes = chunk_index._docstore.docs.values()
        chunk_fp, chunk_i = list(chunk_nodes)[0].metadata["file_path"], 1

        print(f"[Chunker]: {len(chunk_nodes)} chunks used")

        for chunk_ctxt in get_chunk_ctxt_nodes(chunk_nodes):
            chunk_node, ctxt_list = chunk_ctxt
            if chunk_fp == chunk_node.metadata["file_path"]:
                chunk_i += 1
            else:
                chunk_fp = chunk_node.metadata["file_path"]
                chunk_i = 1

            short_name = f"/".join(chunk_fp.split(os.path.sep)[-2:])
            node_id = f"{short_name}::{chunk_i}"
            cluster_input.append(
                CodeChunk(
                    id=node_id,
                    metadata=chunk_node.metadata,
                    node_id=node_id,
                    input_type=ClusterInputType.FILE,
                    content=chunk_node.get_content().replace("\r\n", "\n"),
                    filepath=chunk_node.metadata["file_path"],
                )
            )

        # generate summaries of clusters
        if self.summarize:
            cluster_input = summarize(cluster_input)

        return cluster_input

class VanillaStrategy(ChunkStrategy):
    def chunk(self) -> List[CodeChunk]:
        return self._get_vanilla_chunks()

class BatchStrategy(ChunkStrategy):
    def __init__(self, repo_dir: Path, exclusions: List[str] = DEFAULT_EXCLUSIONS, batch_size: int = 6000):
        super().__init__(repo_dir, exclusions)
        self.batch_size = batch_size

    def chunk(self) -> List[CodeChunk]:
        chunks = self._get_vanilla_chunks()
        remaining_chunks = chunks.copy()
        current_batch = []
        current_size = 0
        batches = []

        while remaining_chunks:
            chunk = remaining_chunks.pop(0)
            chunk_size = len(chunk.get_content())
            
            should_add = current_size + chunk_size <= self.batch_size
            should_start_new = not should_add and current_batch
            
            if should_add:
                current_batch.append(chunk)
                current_size += chunk_size
            
            if should_start_new:
                batches.append(current_batch)
                current_batch = [chunk]
                current_size = chunk_size
                
        if current_batch:
            batches.append(current_batch)
            
        random.shuffle(batches)
        batched_chunks = [chunk for batch in batches for chunk in batch]
        batch_size = len(batched_chunks) / len(batches)
        print("Avg batch size: ", batch_size)
        
        return batched_chunks

# class HybridStrategy(ChunkStrategy):
#     def chunk(self) -> List[CodeChunk]:
#         chunks = self._get_vanilla_chunks()
#         ell_json = json.loads(open(GRAPH_ROOT / "MadcowD_ell_standard.json", "r").read())
#         cg = ChunkGraph.from_json(self.repo_dir, ell_json)

#         cluster_cg(cg)

#         graph_chunks = [
#             CodeChunk(
#                 content=chunk.content,
#                 filepath=chunk.file_path,
#                 input_type=ClusterInputType.CHUNK
#             )
#             for cluster in cg.get_clusters() 
#             for chunk in cluster.chunks
#         ]
#         left_chunks = [chunk for chunk in chunks if chunk not in graph_chunks]

#         for i, c in enumerate(graph_chunks):
#             print(f"Chunk {i}:")
#             print(c.id)

#         return graph_chunks + left_chunks

class RandomStrategy(ChunkStrategy):
    def chunk(self) -> List[CodeChunk]:
        chunks = self._get_vanilla_chunks()
        random.shuffle(chunks)
        return chunks

class SummaryStrategy(ChunkStrategy):
    def chunk(self) -> List[CodeChunk]:
        chunks = self._get_vanilla_chunks()
        results = invoke_multithread(chunks, summarize_chunk)
        summary_chunks = [
            SummaryChunk.from_chunk(chunk, summed.parsed) 
            for chunk, summed in zip(chunks, results["results"]) 
            if summed
        ]

        summary_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in summary_chunks]))
        code_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in chunks]))

        print(f"Summary tokens: {summary_tokens}, "
              f"Code tokens: {code_tokens}, "
              f"Ratio: {summary_tokens / code_tokens}")

        return summary_chunks

class ChunkStrat(str, Enum):
    VANILLA = "vanilla"
    HYBRID = "hybrid"
    RANDOM = "random"
    SUMMARY = "summary"
    BATCH = "batch"

    @classmethod
    def get_strategy_class(cls, strat_type: 'ChunkStrat') -> Type[ChunkStrategy]:
        strategy_map: Dict[ChunkStrat, Type[ChunkStrategy]] = {
            cls.VANILLA: VanillaStrategy,
            # cls.HYBRID: HybridStrategy,
            cls.RANDOM: RandomStrategy,
            cls.SUMMARY: SummaryStrategy,
            cls.BATCH: BatchStrategy
        }
        return strategy_map[strat_type]

def chunk_repo(repo_dir: Path, 
               chunk_strat: ChunkStrat,
               exclusions=DEFAULT_EXCLUSIONS,
               summarize=False,
               split_files=False) -> List[CodeChunk]:
    if split_files:
        files, unclassified = classify_files(repo_dir, exclusions=exclusions)
        exclude_noncore = [f.fp for f in files if f.classification != FILE_CLASSIFICATIONS.CORE]
        exclusions += exclude_noncore
        print(f"Excluded {len(exclude_noncore)} non-core files")

    strategy_class = ChunkStrat.get_strategy_class(chunk_strat)
    strategy = strategy_class(repo_dir, exclusions, summarize=summarize)
    return strategy.chunk()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Concatenate Python files in a directory and generate a directory tree, with exclusions."
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument("--strattype", type=ChunkStrat, choices=list(ChunkStrat), default=ChunkStrat.VANILLA,
                        help="The chunking strategy to use")
    parser.add_argument("-e", "--exclude", action="append", default=[],
                        help="Exclusion patterns (can be used multiple times)")
    parser.add_argument("--output-format", choices=["text", "json"], default="text",
                        help="Output format for the chunks")
    parser.add_argument("--output-file", default="chunks.txt", help="Output file for the chunks")

    # Combine user-provided exclusions with default exclusions
    exclusions = DEFAULT_EXCLUSIONS + parser.parse_args().exclude
    print(f"Exclusion patterns: {exclusions}")

    chunks = chunk_repo(Path(parser.parse_args().directory), chunk_strat=parser.parse_args().strattype, exclusions=exclusions)
    print(f"Finished chunking with {len(chunks)} chunks")

    outfp_name = parser.parse_args().output_file
    if parser.parse_args().output_format == "json":
        # Serialize CodeChunk objects to JSON
        with open(f"{outfp_name}", "w", encoding="utf-8") as f:
            f.write(json.dumps([chunk.dict() for chunk in chunks], indent=4))
        print(f"Chunks have been written to chunks.json")
    else:
        # Write chunks to chunks.txt
        with open(f"{outfp_name}", "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(f"Chunk ID: {chunk.id}\n")
                f.write(f"Filepath: {chunk.filepath}\n")
                f.write(f"Content:\n{chunk.content}\n")
                f.write("-" * 80 + "\n")
        print(f"Chunks have been written to {outfp_name}")
