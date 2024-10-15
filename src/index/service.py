import os
from typing import Dict

from moatless.index import CodeIndex
from moatless.index.settings import IndexSettings
from moatless import FileRepository
from moatless.index.epic_split import EpicSplitter

import os
import fnmatch
import mimetypes
from typing import Dict, List
from pathlib import Path

from llama_index.core import SimpleDirectoryReader


def get_or_create_index(repo_path: str, persist_dir: str):
    """
    Gets or creates the code embeddings/docstore for the repo
    """
    file_repo = FileRepository(repo_path)
    index_settings = IndexSettings(embed_model="text-embedding-3-small")

    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        code_index = CodeIndex.from_persist_dir(persist_dir, file_repo=file_repo)
    else:
        code_index = CodeIndex(
            file_repo=file_repo,
            settings=index_settings,
            # cluster_list=cluster_json if cluster_json else {},
            use_summaries=False,
            summary_anthropic_model=True,
            summary_ref_vars=False,
        )
        code_index.run_ingestion()
        code_index.persist(persist_dir)

    return code_index


def get_or_create_chunks(repo_path: str, persist_dir: str):
    code_index = get_or_create_index(repo_path, persist_dir)
    return code_index._docstore.docs.values()
