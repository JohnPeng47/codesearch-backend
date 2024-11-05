from cowboy_lib.repo import GitRepo

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.queue.core import get_queue, TaskQueue
from src.queue.models import TaskResponse
from src.index.service import get_or_create_index
from src.queue.service import enqueue_task, enqueue_task_and_wait
from src.exceptions import ClientActionException
from src.models import HTTPSuccess
from src.config import (
    REPOS_ROOT, 
    INDEX_ROOT, 
    GRAPH_ROOT, 
    SUMMARIES_ROOT,
    ENV, 
    GITHUB_API_TOKEN,
    REPO_MAX_SIZE_MB
)
from rtfs.summarize.summarize import Summarizer, SummarizedCluster
from rtfs.transforms.cluster import cluster
from rtfs.cluster.graph import ClusterGraph

from .service import list_repos, delete, get_repo
from .repository import GitRepo, PrivateRepoError, RepoSizeExceededError
from .models import (
    Repo,
    RepoCreate,
    RepoListResponse,
    RepoResponse,
    RepoGetRequest,
    RepoSummaryRequest,
    SummarizedClusterResponse,
    repo_ident,
)
from .tasks import InitIndexGraphTask, IndexGraphResponse
from .graph import get_or_create_chunk_graph
from .utils import get_repo_size, http_to_ssh, get_repo_main_language

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

from logging import getLogger

logger = getLogger(__name__)

repo_router = APIRouter()

SUPPORTED_LANGS = [
    "python"
]

# TODO: rewrite repo using class based approach and set the path
# as methods
# @repo_router.post("/repo/create", response_model=RepoResponse)
@repo_router.post("/repo/create")
async def create_repo(
    repo_in: RepoCreate,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    print('Repo: ', repo_in.owner, repo_in.repo_name)
    try:
        existing_repo = get_repo(
            db_session=db_session,
            curr_user=curr_user,
            owner=repo_in.owner,
            repo_name=repo_in.repo_name,
        )
        if existing_repo:
            if curr_user not in existing_repo.users:
                # add mapping between user and existing repo
                existing_repo.users.append(curr_user)
                db_session.add(existing_repo)
                db_session.commit()

            return RepoResponse(
                owner=existing_repo.owner, repo_name=existing_repo.repo_name
            )

        repo_dst = None
        index_persist_dir = INDEX_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        repo_dst = REPOS_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        save_graph_path = GRAPH_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        
        language = get_repo_main_language(repo_in.owner, repo_in.repo_name, GITHUB_API_TOKEN)
        if language.lower() not in SUPPORTED_LANGS:
            raise ClientActionException(
                message=f"Language {language} not supported. Supported languages: {SUPPORTED_LANGS}"
            )

        repo_size = get_repo_size(repo_in.owner, repo_in.repo_name, GITHUB_API_TOKEN) 
        if repo_size > REPO_MAX_SIZE_MB:
            raise RepoSizeExceededError(
                f"Repository size exceeded limit. Please try a smaller repository. Size: {repo_size:.2f} MB"
            )
                
        # TODO: add error logging
        task = InitIndexGraphTask(
            task_args={
                "url": repo_in.url,
                "repo_dst": repo_dst,
                "index_persist_dir": index_persist_dir,
                "save_graph_path": save_graph_path,
            }
        )

        # TODO: add error handling
        result = enqueue_task_and_wait(
            task_queue=task_queue, user_id=curr_user.id, task=task
        )
        time = result.time
        repo_result: IndexGraphResponse = result.result

        cg = repo_result.cg
        cluster(cg)

        # TODO: should maybe turn this into task as well
        # would need asyncSession to perform db_updates though
        repo = Repo(
            **repo_in.dict(),
            language=repo_result.lang,
            repo_size=repo_result.size,
            file_path=str(repo_dst),
            index_path=str(index_persist_dir),
            graph_path=str(save_graph_path),
            users=[curr_user],
            cluster_files=cg.get_chunk_files(),
            time=time,
        )

        db_session.add(repo)
        db_session.commit()

        # print("TASKID: ", task.task_id, "STATUS: ", task.status)
        # need as_dict to convert cloned_folders to list
        return RepoResponse(owner=repo.owner, repo_name=repo.repo_name)

    except RepoSizeExceededError as e:
        raise ClientActionException(
            message="Repository size exceeded limit. Please try a smaller repository.",
        )

    except PrivateRepoError as e:
        raise ClientActionException(message="Private repo not yet supported")

    # TODO: think
    except Exception as e:
        print("Error: ", e)
        db_session.rollback()

        GitRepo.delete_repo(repo_dst)
        logger.error(f"Failed to create repo configuration: {e}")

        raise e


@repo_router.get("/repo/list", response_model=RepoListResponse)
def get_user_and_recommended_repos(
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user, recommended = list_repos(db_session=db_session, curr_user=current_user)
    return RepoListResponse(
        user_repos=[
            RepoResponse(repo_name=repo.repo_name, owner=repo.owner) for repo in user
        ],
        recommended_repos=[
            RepoResponse(repo_name=recommended.repo_name, owner=recommended.owner)
            for recommended in recommended
        ],
    )


@repo_router.post("/repo/files")
async def get_repo_files(
    request: RepoGetRequest,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    repo = get_repo(
        db_session=db_session,
        curr_user=current_user,
        owner=request.owner,
        repo_name=request.repo_name,
    )
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    full_files = GitRepo(Path(repo.file_path)).to_json()
    filter_files = {
        path: content
        for path, content in full_files.items()
        if path in repo.cluster_files
    }
    return filter_files

@repo_router.post("/repo/summarize", response_model=SummarizedClusterResponse)
async def summarize_repo(
    request: RepoSummaryRequest,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    repo = get_repo(
        db_session=db_session,
        curr_user=current_user,
        owner=request.owner,
        repo_name=request.repo_name,
    )
    if not repo:
        print("Repo not found")
        raise HTTPException(status_code=404, detail="Repository not found")
    
    summary_path = SUMMARIES_ROOT / (repo_ident(repo.owner, repo.repo_name) + ".json")
    graph_path = GRAPH_ROOT / repo_ident(repo.owner, repo.repo_name)

    if summary_path and Path(summary_path).exists():
        print("Loading summary from cache ...")
        with open(summary_path, "r") as f:
            summarized_clusters = json.loads(f.read())
            return SummarizedClusterResponse(
                summarized_clusters=[SummarizedCluster.from_json(s) for s in summarized_clusters]
            )

    print("Summarizing ...")
    # summarization logic
    code_index = get_or_create_index(repo.file_path, repo.index_path)
    cg = get_or_create_chunk_graph(
        code_index, repo.file_path, repo.graph_path, request.graph_type
    )
    cluster(cg)

    summarizer = Summarizer(cg)

    summarizer.summarize()
    summarizer.gen_categories()
    # TODO: figure out how to handle
    # except ContextLengthExceeded as e:
    #     raise HTTPException(status_code=400, detail=str(e))
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

    logger.info(
        f"Summarizing stats: {request.graph_type} for {repo.file_path}: \n{cg.get_stats()}"
    )
    summary = summarizer.get_output()

    # write to both summary and graph
    with open(summary_path, "w") as f:
        print("Writing summary to: ", summary_path)
        f.write(json.dumps([s.to_dict() for s in summary]))

    with open(graph_path, "w") as f:
        print("Writing graph to: ", graph_path)
        f.write(json.dumps(cg.to_json()))
    
    return SummarizedClusterResponse(summarized_clusters=summary)


@repo_router.post("/repo/delete")
async def delete_repo(
    request: RepoGetRequest,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    deleted = delete(
        db_session=db_session,
        curr_user=current_user,
        owner=request.owner,
        repo_name=request.repo_name,
    )
    if not deleted:
        raise HTTPException(
            status_code=400, detail="A repo with this name does not exist."
        )

    return HTTPSuccess()


@repo_router.get("/repo/delete_all")
async def delete_all_repos(
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    if ENV != "dev":
        raise Exception("This endpoint is only available in dev environment.")

    def delete_all(db_session: Session, curr_user: User) -> int:
        repos = db_session.query(Repo).all()
        deleted_count = 0
        for repo in repos:
            try:
                delete(
                    db_session=db_session,
                    curr_user=current_user,
                    owner=repo.owner,
                    repo_name=repo.repo_name,
                )
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting repository {repo.repo_name}: {str(e)}")

        db_session.commit()
        return deleted_count

    deleted_count = delete_all(
        db_session=db_session,
        curr_user=current_user,
    )
    if deleted_count == 0:
        raise HTTPException(status_code=400, detail="No repositories found to delete.")

    return HTTPSuccess(detail=f"Successfully deleted {deleted_count} repositories.")


# @repo_router.get("/repo/get/{repo_name}", response_model=RepoGet)
# def get_repo(
#     repo_name: str,
#     db_session: Session = Depends(get_db),
#     current_user: CowboyUser = Depends(get_current_user),
# ):
#     repo = get(db_session=db_session, repo_name=repo_name, curr_user=current_user)
#     if not repo:
#         raise HTTPException(
#             status_code=400, detail="A repo with this name does not exists."
#         )
#     return repo.to_dict()

# # TODO: this should return HEAD of repo.source_folder rather than the remote repo
# # once we finish our task refactor
# @repo_router.get("/repo/get_head/{repo_name}", response_model=RepoRemoteCommit)
# def get_head(
#     repo_name: str,
#     db_session: Session = Depends(get_db),
#     current_user: CowboyUser = Depends(get_current_user),
# ):
#     repo = get(db_session=db_session, repo_name=repo_name, curr_user=current_user)
#     if not repo:
#         raise HTTPException(
#             status_code=400, detail="A repo with this name does not exists."
#         )

#     git_repo = GitRepo(Path(repo.source_folder))

#     # return RepoRemoteCommit(sha=git_repo.local_commit)
#     return RepoRemoteCommit(sha=git_repo.remote_commit)
