from src.auth.models import User
from src.utils import rm_tree

from .repository import GitRepo
from .models import Repo
from .utils import repo_path, index_path, graph_path

from typing import List, Tuple
from pathlib import Path
from logging import getLogger
import glob

logger = getLogger(__name__)


def get_repo(*, db_session, curr_user: User, owner: str, repo_name: str) -> Repo:
    """Returns a repo if it exists for the current user"""

    # TODO: do we need this?
    existing_user_repo = (
        db_session.query(Repo)
        .filter(
            Repo.owner == owner,
            Repo.repo_name == repo_name,
            Repo.users.contains(curr_user),
        )
        .one_or_none()
    )
    if existing_user_repo:
        return existing_user_repo

    existing_global_repo = (
        db_session.query(Repo)
        .filter(Repo.owner == owner, Repo.repo_name == repo_name)
        .one_or_none()
    )
    return existing_global_repo


def delete(*, db_session, curr_user: User, owner: str, repo_name: str) -> Repo:
    """Deletes a repo based on the given repo name."""

    repo = get_repo(
        db_session=db_session, curr_user=curr_user, owner=owner, repo_name=repo_name
    )
    if repo:
        db_session.delete(repo)
        db_session.commit()

        # if there is only one user of repo then delete the repo
        if len(repo.users) == 1:
            rp = repo_path(owner, repo_name)
            ip = index_path(owner, repo_name)
            gp = graph_path(owner, repo_name)

            GitRepo.delete_repo(rp)
            rm_tree(gp)
            rm_tree(ip)

        return repo
    return None


def list_repos(*, db_session, curr_user: User) -> Tuple[List[Repo], List[Repo]]:
    """
    Lists all the repos on the user's frontpage
    """
    recommended_repos = db_session.query(Repo).all()
    user_repos = db_session.query(Repo).filter(Repo.users.contains(curr_user)).all()

    return user_repos, recommended_repos


def get_repo_contents(*, db_session, curr_user: User, repo_name: str) -> Repo:
    """
    Returns the contents of a repo
    """
    repo = get_repo(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    rp = repo_path(repo.owner, repo.repo_name)
    return GitRepo(rp).to_json()


def predict_time_to_index(*, db_session) -> int:
    """
    Predicts the time it will take to index a repo
    """
    repo = db_session.query(Repo).all()