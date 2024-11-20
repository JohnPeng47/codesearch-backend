import os
import fnmatch
import mimetypes
from typing import Dict, List
from llama_index.core import SimpleDirectoryReader

from src.chunk.settings import IndexSettings
from moatless.index.epic_split import EpicSplitter
from moatless.codeblocks import CodeBlock, CodeBlockType

from .base import Chunker

# TODO: can add another layer of indirection here and make this the context
# class that dispatches different strategies
class PythonChunker(Chunker):
    def __init__(self, 
                 repo_path: str, 
                 exclude_files: List[str] = None) -> None:
        repo_path = repo_path
        # Only extract file name and type to not trigger unnecessary embedding jobs
        def file_metadata_func(file_path: str) -> Dict:
            test_patterns = [
                "**/test/**",
                "**/tests/**",
                "**/test_*.py",
                "**/*_test.py",
            ]
            category = (
                "test"
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in test_patterns)
                else "implementation"
            )

            return {
                "file_path": os.path.relpath(file_path, repo_path),
                "file_name": os.path.basename(file_path),
                "file_type": mimetypes.guess_type(file_path)[0],
                "category": category,
            }
        
        reader = SimpleDirectoryReader(
            input_dir=repo_path,
            exclude=exclude_files,
            file_metadata=file_metadata_func,
            input_files=[],
            filename_as_id=True,
            required_exts=[".py"],  # TODO: Shouldn't be hardcoded and filtered
            recursive=True,
        )

        self.docs = reader.load_data()
        blocks_by_class_name = {}
        blocks_by_function_name = {}

        def index_callback(codeblock: CodeBlock):
            if codeblock.type == CodeBlockType.CLASS: 
                if codeblock.identifier not in blocks_by_class_name:
                    blocks_by_class_name[codeblock.identifier] = []
                blocks_by_class_name[codeblock.identifier].append(
                    (codeblock.module.file_path, codeblock.full_path())
                )

            if codeblock.type == CodeBlockType.FUNCTION:
                if codeblock.identifier not in blocks_by_function_name:
                    blocks_by_function_name[codeblock.identifier]= []
                blocks_by_function_name[codeblock.identifier].append(
                    (codeblock.module.file_path, codeblock.full_path())
                )

        settings = IndexSettings()
        self.splitter = EpicSplitter(
            min_chunk_size=settings.min_chunk_size,
            chunk_size=settings.chunk_size,
            hard_token_limit=settings.hard_token_limit,
            max_chunks=settings.max_chunks,
            comment_strategy=settings.comment_strategy,
            index_callback=index_callback,
            repo_path=repo_path,
        )

    def chunk(self):
        return self.splitter.get_nodes_from_documents(self.docs, show_progress=True)