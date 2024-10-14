import ell
from typing import List
from pathlib import Path

from ..types import SourceChunk, LMSummaryChunk, SummaryChunk
from ..chunk_repo import chunk_repo



@ell.complex(model="gpt-4o-mini", response_format=LMSummaryChunk)
def summarize_chunk(cluster: SourceChunk, num_lines: int = 2) -> LMSummaryChunk:
    SUMMARY_PROMPT_V1 = """
You are given a chunk of code that represents a cluster in a larger codebase. Your task is to provide a structured summary of this cluster.
Write a summary of {num_lines} lines that captures the main intent of the code
Note whether the code is logic or data
Also note the definitions and references used in the code, according to the following guidelines:
- for both, DO NOT anythin that is a part of the standard library/system module
- references are any variables that are not declared in the current chunk
- only include the names and nothing else


Here is the code cluster:
{code}

Provide your response in a structured format.
"""
    return SUMMARY_PROMPT_V1.format(code=cluster.content, num_lines=num_lines)


def summarize_chunks(repo_path: Path) -> List[LMSummaryChunk]:
    chunks = chunk_repo(repo_path, mode="full")
    for chunk in chunks[:5]:
        print("Chunk: ", chunk.id)
        print("Content: ", chunk.content)
        print("Summary: ", summarize_chunk(chunk))



SUMMARY_PROMPT_V2 = """
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
