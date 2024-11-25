import os
import fnmatch
import mimetypes
import json
from typing import Dict, List
from llama_index.core import SimpleDirectoryReader
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.schema import BaseNode

from src.models import (
    ChunkMetadata,
    FunctionContext,
    ScopeType,
    ChunkContext,
    CodeChunk,
    ChunkType
)
from src.settings import DEFAULT_INDEX_SETTINGS
from moatless.index.epic_split import EpicSplitter
from moatless.codeblocks import CodeBlock, CodeBlockType
from rtfs_rewrite.ts import cap_ts_queries, TSLangs

from .base import Chunker

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

        self.splitter = EpicSplitter(
            min_chunk_size=DEFAULT_INDEX_SETTINGS.min_chunk_size,
            chunk_size=DEFAULT_INDEX_SETTINGS.chunk_size,
            hard_token_limit=DEFAULT_INDEX_SETTINGS.hard_token_limit,
            max_chunks=DEFAULT_INDEX_SETTINGS.max_chunks,
            comment_strategy=DEFAULT_INDEX_SETTINGS.comment_strategy,
            index_callback=index_callback,
            repo_path=str(repo_path),
        )

    def chunk(self, persist_path: str = "") -> List[CodeChunk]:
        if os.path.exists(persist_path):
            print("Loading persisted chunks from ", persist_path)
            with open(persist_path, "r") as f:
                chunk_nodes = json.loads(f.read())
                return [CodeChunk.from_json(chunk) for chunk in chunk_nodes]
        else:
            chunk_nodes = self.splitter.get_nodes_from_documents(self.docs, show_progress=True)

        chunks = []
        chunk_fp, chunk_i = chunk_nodes[0].metadata["file_path"], 0
        for chunk_ctxt in chunk_nodes:
            # chunk_node, _ = chunk_ctxt
            chunk_node = chunk_ctxt
            if chunk_fp == chunk_node.metadata["file_path"]:
                chunk_i += 1
            else:
                chunk_fp = chunk_node.metadata["file_path"]
                chunk_i = 1

            short_name = f"/".join(chunk_fp.split(os.path.sep)[-2:])
            node_id = f"{short_name}::{chunk_i}"
            chunks.append(
                CodeChunk(
                    id=node_id,
                    metadata=ChunkMetadata(**chunk_node.metadata),
                    input_type=ChunkType.CHUNK,
                    content=chunk_node.get_content().replace("\r\n", "\n"),
                    # add summary here
                )
            )

        print(f"Persisting chunks to {persist_path}")
        with open(persist_path, "w") as f:
            f.write(json.dumps([chunk.to_json() for chunk in chunks], indent=2))    

        return chunks
