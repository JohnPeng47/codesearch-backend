from sqlalchemy import Column, Integer, String, ARRAY
from sqlalchemy.orm import relationship
from pydantic import BaseModel, field_validator, model_validator, Field, ConfigDict
import re
from typing import List, Optional

from rtfs.cluster.graph import Cluster
from src.models import RTFSBase
from src.database.core import Base
from src.model_relations import user_repo

from .graph import GraphType

# TODO: redefine all backend models using FastAPI SQLModel
# create separate path objects for the file paths, especially graph_path
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
    cluster_files = Column(ARRAY(String))
    time = Column(Integer) # clone + indexing duration

    # TODO: probably want to make this a separate RepoStats table
    views = Column(Integer)
    users = relationship(
        "User",
        secondary=user_repo,
        uselist=True,
        back_populates="repos",
        single_parent=True,
    )

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
    owner: Optional[str] = Field(default=None)
    repo_name: Optional[str] = Field(default=None)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("URL is required")
        
        http_match = re.match(r"^https?://github\.com/([\w.-]+)/([\w.-]+)$", v)
        ssh_match = re.match(r"^git@github\.com:([\w.-]+)/([\w.-]+)(?:\.git)?$", v)
        
        if not (http_match or ssh_match):
            raise ValueError("Invalid GitHub URL format. Must be either HTTP(S) or SSH form.")
        
        return v

    @model_validator(mode="after")
    def extract_info(self) -> "RepoCreate":
        if self.owner is None or self.repo_name is None:
            match = re.match(
                r"(?:https?://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?$",
                self.url,
            )

            if match:
                self.owner = self.owner or match.group(1)
                self.repo_name = self.repo_name or match.group(2)
            else:
                raise ValueError("Could not extract owner and repo_name from URL")

        return self
    
    @property
    def repo_ident(self):
        return f"{self.owner}_{self.repo_name}" 

class RepoResponse(RepoCreate):
    url: Optional[str] = None


class RepoGetRequest(RepoCreate):
    url: Optional[str] = None

class RepoSummaryRequest(RepoGetRequest):
    graph_type: GraphType


class SummarizedClusterResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True, warnings=False)
    summarized_clusters: List[Cluster]

class RepoListResponse(RTFSBase):
    user_repos: List[RepoResponse]
    recommended_repos: List[RepoResponse]


class RepoRemoteCommit(RTFSBase):
    sha: str


class PrivateRepoAccess(Exception):
    pass
