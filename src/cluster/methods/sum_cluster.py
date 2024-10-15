import ell
from pydantic import BaseModel
from typing import List
from pathlib import Path

from ..types import CodeChunk
from ..chunk_repo import chunk_repo


# TODO(Prompt Optimizations):
# order of summary wrt to defs/refs? Adding it after could benefit
# from the refs/defs being used as the scratchpad

class Reference(BaseModel):
    name: str
    use_explanation: str

class ChunkSummary(BaseModel):
    title: str
    summary: str
    definitions: List[str]
    references: List[str]
    
    def __str__(self):
        return (
            f"{self.title}\n"
            f"{self.summary}\n\n"
            f"Definitions: {self.definitions}\n"
            f"References: {self.references}"
        )


@ell.complex(model="gpt-4o-mini", response_format=ChunkSummary)
def summarize_chunk(cluster: CodeChunk, num_lines: int = 2) -> ChunkSummary:
    SUMMARY_PROMPT = """
You are given a chunk of code that represents a cluster in a larger codebase. Your task is to provide a structured summary of this cluster.
Write a summary of {num_lines} lines that captures the main intent of the code
Also note the definitions and references used in the code, according to the following guidelines:
- for both, DO NOT anythin that is a part of the standard library/system module
- for definitions only include the name, and nothing else
- for references, the list does not have to exhaustive, but should include the most important references (ie. not defined in current chunk)
- for references, include the name and brief explanation of the usage

Here is the code cluster:
{code}

Provide your response in a structured format.
"""
    return SUMMARY_PROMPT.format(code=cluster.content, num_lines=num_lines)


def summarize_chunks(repo_path: Path) -> List[ChunkSummary]:
    chunks = chunk_repo(repo_path, mode="full")
    for chunk in chunks[:5]:
        print("Chunk: ", chunk.id)
        print("Content: ", chunk.content)
        print("Summary: ", summarize_chunk(chunk))