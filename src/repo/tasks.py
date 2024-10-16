from pydantic import BaseModel

from src.queue.models import Task, TaskType
from src.index.service import get_or_create_index
from rtfs.cluster.graph import ClusterGraph

from .repository import GitRepo
from .graph import get_or_create_chunk_graph, GraphType


class TaskResponse(BaseModel):
    pass

class IndexGraphResponse(TaskResponse):
    cg: ClusterGraph
    lang: str
    size: int

    class Config:
        arbitrary_types_allowed = True
    

class InitIndexGraphTask(Task):
    type: TaskType = TaskType.INIT_GRAPH

    def task(
        self,
        *,
        url,
        repo_dst,
        index_persist_dir,
        save_graph_path,
        graph_type=GraphType.STANDARD
    ) -> IndexGraphResponse:
        print(f"Cloning repo {url} ...")
        git_repo = GitRepo.clone_repo(repo_dst, url)
        
        print(f"Finished cloning starting indexing {url} ...")
        code_index = get_or_create_index(
            str(repo_dst),
            str(index_persist_dir),
        )

        print("Creating graph ...")
        cg = get_or_create_chunk_graph(
            code_index, repo_dst, save_graph_path, graph_type
        )
        lang, sz = git_repo.get_lang_and_size()

        return IndexGraphResponse(cg=cg, lang=lang, size=sz)