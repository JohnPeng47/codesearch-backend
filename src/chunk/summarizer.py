from llm import LLMModel
from typing import List

from .lmp.summarize import summarize_lmp
from .models import CodeChunk

def is_import_block(content: str) -> bool:
    import_count = content.lower().count("import")
    return import_count > 3

def summarize(model: LLMModel, chunks: List[CodeChunk]):
    for chunk in chunks:
        if is_import_block(chunk.content):
            print("Skipping import block: ", chunk.content)
            continue

        chunk.summary = summarize_lmp(model, chunk.content)

    return chunks