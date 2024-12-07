from pydantic import BaseModel
import json

from src.queue.models import Task, TaskType, TaskCompleteCallback, TaskResult
from src.repo.models import Repo
from src.index.service import get_or_create_index
from src.auth.service import get as get_user_by_id
from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer

from .repository import GitRepo
from .graph import get_or_create_chunk_graph, GraphType
from .utils import repo_path, index_path, graph_path

from rtfs.cluster.cluster_graph import ClusterGraph

from typing import Any

class IndexGraphResult(BaseModel):
    repo_url: str
    repo_owner: str
    repo_name: str
    user_id: int
    cg: ClusterGraph
    lang: str
    size: float

    class Config:
        arbitrary_types_allowed = True
        
class InitGraphCallback(TaskCompleteCallback):
    def __call__(self, db_session, task_result: IndexGraphResult, ex_time: float):
        print("Committing repo to DB")
        
        user = get_user_by_id(task_result.user_id)
        repo = Repo(
            url=task_result.repo_url,
            owner=task_result.repo_owner,
            repo_name=task_result.repo_name,
            language=task_result.lang,
            repo_size=task_result.size,
            users=[user],
            cluster_files=task_result.cg.get_chunk_files(),
            time=ex_time,
        )

        db_session.add(repo)
        db_session.commit()


# In local version indexing is done on same machine, db session is passed in args, 
# and db write happens when finished
# In remote version indexing is done on remote machine, and a separate request is made
# back to our server to complete the post_complete callback
class InitIndexGraphTaskRemote(Task):
    type: TaskType = TaskType.INIT_GRAPH
    post_complete: Any = InitGraphCallback()

    def task(
        self,
        *,
        url,
        owner,
        repo_name,
        language,
        repo_size,
        user_id,
        graph_type=GraphType.STANDARD
    ) -> IndexGraphResult:
        try:
            repo_dst = repo_path(owner, repo_name)
            index_persist_dir = index_path(owner, repo_name)
            save_graph_path = graph_path(owner, repo_name)

            print(f"Cloning repo {url} ...")
            GitRepo.clone_repo(repo_dst, url)
            
            print(f"Finished cloning starting indexing {url} ...")

            chunker = PythonChunker(repo_dst)
            chunks = chunker.chunk()
            cg = ChunkGraph.from_chunks(repo_dst, chunks) 
            cg.cluster()

            indexer = Indexer(repo_path, chunks, cg, run_code=False, run_cluster=True)
            indexer.run()

            # TODO: think
            return IndexGraphResult(repo_url=url, 
                                    repo_owner=owner, 
                                    repo_name=repo_name,
                                    user_id=user_id,
                                    cg=cg, 
                                    lang=language, 
                                    size=repo_size)
        except Exception as e:
            GitRepo.delete_repo(repo_dst)
            print(f"Failed to create repo configuration: {e}")
            
            import traceback
            print("Full exception traceback:")
            print("".join(traceback.format_tb(e.__traceback__)))
            print(f"{type(e).__name__}: {str(e)}")
            
            raise e

class InitIndexGraphTaskLocal(Task):
    type: TaskType = TaskType.INIT_GRAPH
    post_complete: Any = InitGraphCallback()

    def task(
        self,
        *,
        db_session,
        url,
        owner,
        repo_name,
        language,
        repo_size,
        user_id,
        graph_type=GraphType.STANDARD
    ) -> IndexGraphResult:
        try:
            repo_dst = repo_path(owner, repo_name)
            index_persist_dir = index_path(owner, repo_name)
            save_graph_path = graph_path(owner, repo_name)

            print(f"Cloning repo {url} ...")
            GitRepo.clone_repo(repo_dst, url)
            
            chunker = PythonChunker(repo_dst)
            chunks = chunker.chunk()
            cg = ChunkGraph.from_chunks(repo_dst, chunks) 
            cg.cluster()
            
            # save generated summaries
            print("Saving generated summaries")
            with open(save_graph_path, "w") as f:
                f.write(json.dumps(cg.to_json(save_graph_path)))

            # NEWTODO: turn this on when we are ready for chat
            # indexer = Indexer(repo_dst, chunks, cg, run_code=False, run_cluster=True)
            # indexer.run()

            user = get_user_by_id(db_session=db_session, user_id=user_id)
            repo = Repo(
                url=url,
                owner=owner,
                repo_name=repo_name,
                language=language,
                repo_size=repo_size,
                users=[user],
                cluster_files=cg.get_chunk_files(),
                time=0, # NEWTODO: how do we get here?
            )

            db_session.add(repo)
            db_session.commit()

        except Exception as e:
            GitRepo.delete_repo(repo_dst)
            print(f"Failed to create repo configuration: {e}")
            
            import traceback
            print("Full exception traceback:")
            print("".join(traceback.format_tb(e.__traceback__)))
            print(f"{type(e).__name__}: {str(e)}")
            
            raise e