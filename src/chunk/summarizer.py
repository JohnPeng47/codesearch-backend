from llm import LLMModel
from typing import List

from .lmp.summarize import summarize_lmp
from .models import CodeChunk
from src.llm.invoke_mt import invoke_multithread
from src.config import MODEL_CONFIG

def is_import_block(content: str) -> bool:
    import_count = content.lower().count("import")
    return import_count > 3

def summarize(chunks: List[CodeChunk]):
    model = LLMModel(provider=MODEL_CONFIG["ChunkSummarizer"]["provider"])

    results = invoke_multithread(chunks, lambda chunk: summarize_lmp(model, chunk.content))
    for chunk, results in zip(chunks, results):
        chunk_summary = results
        print("Chunk summary: ", chunk_summary)

        chunk.summary = results

    return chunks