from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, root_validator, field_validator, model_validator

from src.models import RTFSBase
from src.database.core import Base
from src.model_relations import user_repo

import re
from typing import List, Optional


class Repo(Base):
    """
    Stores configuration for a repository
    """

    __tablename__ = "repos"

    id = Column(Integer, primary_key=True)
    owner = Column(String)
    repo_name = Column(String)
    url = Column(String)
    language = Column(String)
    repo_size = Column(Integer)
    file_path = Column(String)
    # TODO: probably want to make this a separate RepoStats table
    views = Column(Integer)

    users = relationship("User", secondary=user_repo, uselist=True, cascade="all, delete-orphan", back_populates="repos", single_parent=True)

    def to_dict(self):
        return {
            # "repo_name": self.repo_name,
            "url": self.url,
        }

class RepoBase(RTFSBase):
    url: str


class RepoGet(RepoBase):
    pass

class RepoBase(BaseModel):
    pass

class RepoCreate(BaseModel):
    url: str
    owner: Optional[str] = None
    repo_name: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("URL is required")

        patterns = [
            r"^https?://github\.com/([\w.-]+)/([\w.-]+)\.git?$",
            r"^git@github\.com:([\w.-]+)/([\w.-]+)(?:\.git)?$",
        ]

        if not any(re.match(pattern, v) for pattern in patterns):
            raise ValueError(
                "Invalid GitHub URL format. Must be either HTTP(S) or SSH form."
            )

        return v

    @model_validator(mode="after")
    def extract_info(self) -> "RepoCreate":
        if self.owner is None or self.repo_name is None:
            match = re.match(
                r"(?:https?://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+)(?:\.git)?$",
                self.url,
            )

            if match:
                self.owner = self.owner or match.group(1)
                self.repo_name = self.repo_name or match.group(2)
            else:
                raise ValueError("Could not extract owner and repo_name from URL")

        return self
    
class RepoResponse(RepoBase):
    name: str

class RepoListResponse(RTFSBase):
    user_repos: List[RepoResponse]
    recommended_repos: List[RepoResponse]


class RepoRemoteCommit(RTFSBase):
    sha: str


class PrivateRepoAccess(Exception):
    pass
