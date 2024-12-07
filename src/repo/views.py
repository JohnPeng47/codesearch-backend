from cowboy_lib.repo import GitRepo

from rtfs.cluster.graph import Cluster
from rtfs.cluster.cluster_graph import ClusterGraph
from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.queue.core import get_queue, TaskQueue
from src.index.service import get_or_create_index
from src.queue.service import enqueue_task, enqueue_task_and_wait
from src.exceptions import ClientActionException
from src.models import HTTPSuccess
from src.config import (
    ENV, 
    GITHUB_API_TOKEN,
    REPO_MAX_SIZE_MB
)
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
)
from .tasks import InitIndexGraphTaskLocal
from .graph import get_or_create_chunk_graph
from .utils import (
    repo_path, 
    graph_path,
    index_path,
    get_repo_size, 
    http_to_ssh, 
    get_repo_main_language
)

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from logging import getLogger

logger = getLogger(__name__)

repo_router = APIRouter()

SUPPORTED_LANGS = [
    "python"
]

# async version where we return right away, doesn't work!!!
# @repo_router.post("/repo/create")
# async def create_repo(
#     repo_in: RepoCreate,
#     db_session: Session = Depends(get_db),
#     curr_user: User = Depends(get_current_user),
#     task_queue: TaskQueue = Depends(get_queue),
# ):
#     # raise ClientActionException(
#     #     message=f"Repo too big"
#     # )

#     try:
#         existing_repo = get_repo(
#             db_session=db_session,
#             curr_user=curr_user,
#             owner=repo_in.owner,
#             repo_name=repo_in.repo_name,
#         )
#         if existing_repo:
#             if curr_user not in existing_repo.users:
#                 # add mapping between user and existing repo
#                 existing_repo.users.append(curr_user)
#                 db_session.add(existing_repo)
#                 db_session.commit()

#             return RepoResponse(
#                 owner=existing_repo.owner, repo_name=existing_repo.repo_name
#             )
        
#         # GH API call to figure out size and language
#         # language = get_repo_main_language(repo_in.owner, repo_in.repo_name, GITHUB_API_TOKEN)
#         # if language.lower() not in SUPPORTED_LANGS:
#         #     raise ClientActionException(
#         #         message=f"Language {language} not supported. Supported languages: {SUPPORTED_LANGS}"
#         #     )

#         language = "python"
#         repo_size = get_repo_size(repo_in.owner, repo_in.repo_name, GITHUB_API_TOKEN) 
#         print(type(repo_size), type(REPO_MAX_SIZE_MB))
#         if repo_size > REPO_MAX_SIZE_MB:
#             raise RepoSizeExceededError(
#                 f"Repository size exceeded limit. Please try a smaller repository. Size: {repo_size:.2f} MB"
#             )
                
#         # TODO: add error logging
#         task = InitIndexGraphTask(
#             task_args={
#                 "url": repo_in.url,
#                 "owner": repo_in.owner,
#                 "repo_name": repo_in.repo_name,
#                 "language": language,
#                 "repo_size": repo_size,
#                 "user_id": curr_user.id,
#             }
#         )
#         enqueue_task(task_queue=task_queue, task=task, user_id=curr_user.id)
#         return TaskResponse(task_id=task.task_id, status=task.status)

#     except RepoSizeExceededError as e:
#         raise ClientActionException(
#             message="Repository size exceeded limit. Please try a smaller repository.",
#         )

#     except PrivateRepoError as e:
#         raise ClientActionException(message="Private repo not yet supported")
    

# Using this version right now because easier to just return
# the indexed results in a single request instead of relying on client polling

@repo_router.post("/repo/create")
def create_repo_sync(
    repo_in: RepoCreate,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
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
        
        # GH API call to figure out size and language
        # language = get_repo_main_language(repo_in.owner, repo_in.repo_name, GITHUB_API_TOKEN)
        # if language.lower() not in SUPPORTED_LANGS:
        #     raise ClientActionException(
        #         message=f"Language {language} not supported. Supported languages: {SUPPORTED_LANGS}"
        #     )

        language = "python"
        repo_size = get_repo_size(repo_in.owner, repo_in.repo_name, GITHUB_API_TOKEN) 
        if repo_size > REPO_MAX_SIZE_MB:
            raise RepoSizeExceededError(
                f"Repository size exceeded limit. Please try a smaller repository. Size: {repo_size:.2f} MB"
            )
                
        # TODO: add error logging
        task = InitIndexGraphTaskLocal(
            task_args={
                "db_session": db_session,
                "url": repo_in.url,
                "owner": repo_in.owner,
                "repo_name": repo_in.repo_name,
                "language": language,
                "repo_size": repo_size,
                "user_id": curr_user.id,
            }
        )
        enqueue_task_and_wait(task_queue=task_queue, task=task, user_id=curr_user.id)
        return HTTPSuccess(detail="Successfully indexed repository.")

    except RepoSizeExceededError as e:
        raise ClientActionException(
            message="Repository size exceeded limit. Please try a smaller repository.",
        )

    except PrivateRepoError as e:
        raise ClientActionException(message="Private repo not yet supported")


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

    rp = repo_path(request.owner, request.repo_name)
    full_files = GitRepo(rp).to_json()
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
    
    gp = graph_path(request.owner, request.repo_name)
    rp = repo_path(request.owner, request.repo_name)
    if gp.exists():
        print("Loading summary from", gp)
        with open(gp, "r") as f:
            cg = ClusterGraph.from_json(rp, json.loads(f.read()))
            print("SUMMARUOZED", cg.get_clusters())
            return SummarizedClusterResponse(
                summarized_clusters=cg.get_clusters()
            )
    else:
        return HTTPException(status_code=404, detail="Repository not indexed yet")

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
