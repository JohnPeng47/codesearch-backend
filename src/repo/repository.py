from cowboy_lib.utils import gen_random_name
from cowboy_lib.repo.diff import CommitDiff

import os
import tempfile
import hashlib
from pathlib import Path
from logging import getLogger
from git import Repo, GitCommandError
import shutil
import random
from typing import List, Union, Tuple, Dict
from pydantic import BaseModel
import dotenv

from src.utils import rm_tree
from src.repo.extensions import EXTTOFILE, FILETOEXT

dotenv.load_dotenv()
logger = getLogger(__name__)


class NoRemoteException(Exception):
    pass


class NoMainBranch(Exception):
    pass


class PrivateRepoError(Exception):
    pass


class RepoSizeExceededError(Exception):
    pass


def del_file(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat

    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


class GitRepo:
    """
    Used to manage git operations on a git repo
    """

    def __init__(self, repo_path: Path, remote: str = "origin", main: str = ""):
        if not repo_path.exists():
            # test suite may be renamed or deleted
            raise Exception("GitRepo does not exist: ", repo_path)

        # used for reversing patches
        self.patched_files = {}
        self.repo_folder = repo_path
        self.repo = Repo(repo_path)
        self.head = self.repo.head

        if main:
            if not self.branch_exists(main):
                raise NoMainBranch(main)
        else:
            potential = ["master", "main"]
            for branch in potential:
                main = branch if self.branch_exists(branch) else ""
                if main:
                    break
            if not main:
                raise NoMainBranch(main)

        self.main = main
        try:
            self.origin = self.repo.remotes.__getattr__(remote)
        except AttributeError:
            raise NoRemoteException(remote)

        self.username = self.origin.url.split("/")[-2]
        self.repo_name = self.origin.url.split("/")[-1]

        self.branch_prefix = "cowboy_"

    @classmethod
    def clone_repo(
        cls, clone_dst: Path, url: str, max_size: int, language: str
    ) -> "GitRepo":
        """
        Creates a clone of the repo locally
        """
        if not os.path.exists(clone_dst):
            os.makedirs(clone_dst)
        try:
            # Clone with depth 1 to only get the latest commit
            temp_repo = Repo.clone_from(url, clone_dst, depth=1)

            # Check repo size
            repo_size = sum(
                blob.size
                for blob in temp_repo.tree().traverse()
                if blob.path.endswith(FILETOEXT[language])
            )
            if repo_size > max_size:
                logger.error(
                    f"Repo: {url} size {repo_size} exceeds maximum allowed size {max_size}, diff => {repo_size - max_size}"
                )

                raise RepoSizeExceededError(
                    f"Repo size {repo_size} exceeds maximum allowed size {max_size}"
                )

            # If size is okay, fetch the full repo
            temp_repo.git.fetch("--unshallow")

            return cls(clone_dst)
        except GitCommandError as e:
            if "Permission denied (publickey)." in str(e):
                raise PrivateRepoError
            raise e

    @classmethod
    def delete_repo(cls, repo_dst: Path):
        """
        Deletes a repo from the db and all its cloned folders
        """
        import platform

        if not repo_dst.exists():
            return

        if platform.system() == "Windows":
            # rm_tree(str(repo_dst))
            shutil.rmtree(repo_dst, onerror=del_file)
        else:
            shutil.rmtree(repo_dst)

    def to_json(self) -> Dict:
        """
        Iterates through the repo and returns a json that represents
        the filepaths
        """
        content_dict = {}
        for root, dirs, files in os.walk(self.repo.working_dir):
            for file in files:
                file_path = os.path.relpath(
                    os.path.join(root, file), self.repo.working_dir
                )
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    try:
                        content = f.read()
                        content_dict[file_path] = content

                    # TODO: log this somewhere
                    except UnicodeDecodeError:
                        continue

        return content_dict

    def get_lang_and_size(self):
        """
        Identifies language of repo
        """
        max_content_length = 0
        identified_language = None
        lang_len = {}

        content_dict = self.to_json()
        for file_path, content in content_dict.items():
            for ext, language in EXTTOFILE.items():
                if language == "JSON":
                    continue
                if file_path.endswith(ext) and len(content) > max_content_length:
                    max_content_length = len(content)
                    identified_language = language
                    if not lang_len.get(language, None):
                        lang_len[language] = 0

                    lang_len[language] += len(content)

        return identified_language, lang_len[identified_language]

    def reset_to_commit(self, commit_sha, parent=None, head: int = 0):
        """
        Resets the index of the repository to a specific commit.
        """
        self.repo.git.reset(f"--hard", commit_sha)
        return f"Successfully reset to commit {commit_sha}"

    def reset_to_commit_head(self, head: int = 0):
        head = f"HEAD~{str(head)}" if head else ""

        self.repo.git.reset(f"--hard", head)
        return f"Successfully reset to commit {head}"

    def commit_exists(self, commit_sha: str) -> bool:
        """
        Checks if a commit exists in the repo
        """
        try:
            self.repo.commit(commit_sha)
            return True
        except Exception:
            return False

    def get_curr_commit(self):
        """
        Returns the current commit sha
        """
        return self.head.commit.hexsha

    def get_prev_commit(self, commit_sha):
        """
        Returns the previous commit of a given commit sha
        """
        return self.repo.commit(commit_sha).parents[0]

    def apply_patch(self, patch: str) -> None:
        """
        Applies a patch from a .diff file to a single file in the repository
        """
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as patch_file:
            patch_file.write(patch.encode("utf-8") + b"\n")
            patch_file.flush()

        patch_hash = hashlib.md5(patch.encode("utf-8")).hexdigest()
        self.repo.git.apply(patch_file.name, whitespace="nowarn")
        self.patched_files[patch_hash] = patch_file.name

    def reverse_patch(self, patch: str) -> None:
        """
        Reverses a patch from a .diff
        """
        patch_hash = hashlib.md5(patch.encode()).hexdigest()
        patch_file = self.patched_files[patch_hash]

        self.repo.git.apply(patch_file, reverse=True)
        self.patched_files.pop(patch_hash)

    def branch_exists(self, branch: str):
        """
        Checks if a branch exists in the repo
        """
        # print(f"Branch: {branch}")
        # print(f"Branches {[str(br) for br in self.repo.heads]} in {self.repo_folder}")
        if branch in [str(br) for br in self.repo.heads]:
            print(
                branch,
                [str(br) for br in self.repo.heads],
                branch in [str(br) for br in self.repo.heads],
            )
            return True

        return False

    def checkout(self, branch_name: str, new=False):
        """
        Checks out an existing branch in the repo
        """
        if new:
            branch = self.repo.create_head(branch_name)
        else:
            branch = self.repo.heads[branch_name]

        print(f"Checking out: {branch}")
        branch.checkout()

    def clean_branches(self, branch_prefix: str):
        """
        Deletes all branches with a specific prefix
        """
        removed = []
        for branch in self.repo.branches:
            if branch.name.startswith(branch_prefix):
                removed.append(branch.name)
                self.repo.delete_head(branch)

        return removed

    @property
    def remote_commit(self) -> str:
        """
        Gets the sha of latest commit on origin
        """
        self.repo.remotes.origin.fetch()
        remote_sha = self.repo.remotes.origin.refs.__getattr__(self.main).commit.hexsha

        return remote_sha

    @property
    def local_commit(self) -> str:
        return self.repo.head.commit.hexsha

    # TODO: move this into sync_repo
    def fetch_diffs(self) -> Tuple[CommitDiff, str]:
        """
        Diffs the remote with our local repo
        """
        try:
            if self.local_commit == self.remote_commit:
                print("No updates available.")
                return None, None
            else:
                print("Updates found!")

                # Get the diff between the old commit and the new HEAD
                diff = self.repo.git.diff(self.local_commit, self.remote_commit)
                commit_diff = CommitDiff(diff)

                return commit_diff, self.remote_commit
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def pull(self):
        self.repo.remotes.origin.pull()

    def add_n_commit(self, files: List[str], msg: str):
        self.repo.index.add(files)
        self.repo.index.commit(msg)

    def push(self, branch_name: str = "", force: bool = False):
        if not branch_name:
            branch_name = self.main
        self.origin.push(refspec=f"{branch_name}:{branch_name}", force=True)

    def checkout_and_push(
        self,
        name: str,
        commit_message: str,
        files_to_commit: list,
    ):
        """
        Checks out a new branch, commits changes, and pushes to the remote. Returns the
        URL for the merge request of our new branch against main

        Args:
        - name: The "suggested" name
        - commit_message: The commit message to use.
        - files_to_commit: List of file paths (relative to the repo root) to commit.

        Returns:
        - None
        """
        branch_name = name
        if self.branch_exists(name):
            branch_name = self.branch_prefix + name + "_" + gen_random_name()

        # Check out a new branch
        try:
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            # Add and commit changes
            self.repo.index.add(files_to_commit)
            self.repo.index.commit(commit_message)
            self.push(branch_name=branch_name)
            origin_url = self.origin.url.replace(".git", "")
        except Exception as e:
            logger.error(f"Exception in {self.repo_name}: {str(e)}")
            pass
        finally:
            self.checkout(self.main)
            logger.info(f"Resetting to branch {self.main}")

        # url for branch merge request
        return f"{origin_url}/compare/{self.main}...{self.username}:{self.repo_name}:{branch_name}?expand=1"


class PatchApplyExcepion(Exception):
    pass


class IncompatibleCommit(Exception):
    pass


class PatchFile(BaseModel):
    path: Path
    patch: str


class PatchFileContext:
    """
    Context manager for applying and reversing patches
    """

    def __init__(
        self, repo: GitRepo, patch: Union[str, PatchFile], revert: bool = True
    ):

        self.repo = repo
        self.patch = patch
        # assume all cases repo and patch are both specified, or neither are
        self.head_commit = self.repo.head.commit if self.patch else None
        self.failed_id = random.randint(0, 1000000)
        # for debugging
        self.revert = revert

    # def _write_broken_patch(self):
    #     with open(
    #         f"log/failed_patches/patch_{self.failed_id}.diff", "w+", encoding="utf-8"
    #     ) as f:
    #         f.write(self.patch)

    def __enter__(self):
        if not self.patch:
            return

        try:
            if isinstance(self.patch, PatchFile):
                with open(self.patch.path, "w", encoding="utf-8") as f:
                    f.write(self.patch.patch)
            elif isinstance(self.patch, str):
                self.repo.apply_patch(self.patch)

        except GitCommandError as e:
            # self._write_broken_patch()
            raise PatchApplyExcepion(e)

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.patch:
            return

        try:
            if isinstance(self.patch, PatchFile) and self.revert:
                self.repo.reset_to_commit(self.head_commit)
            elif isinstance(self.patch, str) and self.revert:
                self.repo.reverse_patch(self.patch)

        except GitCommandError as e:
            logger.info(f"Error reversing patch")
            raise PatchApplyExcepion(e)


class ResetLocalCommitContext:
    """
    Resets the repository to a specific commit
    """

    def __init__(self, repo: GitRepo, fd_reset: bool = False, revert: bool = True):
        self.repo = repo
        self.revert = revert
        self.fd_reset = fd_reset

    def __enter__(self):
        """
        Saves the current commit hash when entering the context.
        """
        self.original_commit = self.repo.head.commit.hexsha
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Restores the repository to the original commit when exiting the context.
        """
        if exc_type is not None:
            print(f"An exception occurred: {exc_type.__name__}: {exc_value}")
            # Optionally, log the traceback here

        if self.fd_reset:
            self._add_files()

        if self.original_commit and self.revert:
            self.repo.reset_to_commit(self.original_commit)

        # reset the patched files in GitRepo
        self.repo.patched_files = {}

    def _add_files(self):
        """
        Adds all files in repo so that they are tracked by git and can be resetted
        when the context is exited
        """
        self.repo.repo.git.add(".")
        print(self.repo.repo.git.status())

    def reset_to_commit(self, commit_sha: str, parent=None):
        """
        Resets the index of the repository to a specific commit.
        """
        return self.repo.reset_to_commit(commit_sha, parent)


class ResetRemoteCommitContext:
    """
    Pushes a single commit to remote repo and then reverts it in the remote
    by pushing HEAD~1. Used for unit tests
    """

    def __init__(self, repo: GitRepo):
        self.repo = repo
        self._called = False

    def __enter__(self):
        """
        Saves the current commit hash when entering the context.
        """
        self.original_commit = self.repo.head.commit.hexsha
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Restores remote repo to HEAD~1
        """
        if not self._called:
            # reset local repo state if we dont end up pushing
            self.repo.reset_to_commit(self.original_commit)
            print("Resetting to og state")
            return

        self.repo.reset_to_commit_head(head=1)
        self.repo.push()

    def add_commit_push(self, files: List[str], msg: str):
        """
        Adds a commit to the repo and pushes it to the remote
        """
        try:
            self.repo.add_n_commit(files, msg)
            self.repo.push()
        except Exception as e:
            print("Error adding commit")
            self.repo.reset_to_commit(self.original_commit)
            raise e
        finally:
            self._called = True
