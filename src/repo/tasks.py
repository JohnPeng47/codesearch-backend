from src.queue.models import Task, TaskType
from src.index.service import get_or_create_index
import json

from .graph import get_or_create_chunk_graph, GraphType


class InitIndexGraphTask(Task):
    type: TaskType = TaskType.INIT_GRAPH

    def task(
        self,
        *,
        repo_dst,
        index_persist_dir,
        save_graph_path,
        graph_type=GraphType.STANDARD
    ):
        code_index = get_or_create_index(
            str(repo_dst),
            str(index_persist_dir),
        )
        return get_or_create_chunk_graph(
            code_index, repo_dst, save_graph_path, graph_type
        )
