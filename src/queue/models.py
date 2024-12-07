from enum import Enum
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from abc import abstractmethod, ABC
from sqlalchemy.orm import Session

from src.utils import generate_id

class TaskResult(BaseModel):
    result: Any
    ex_time: float
    
    class Config:
        arbitrary_types_allowed = True


class TaskType(str, Enum):
    INIT_GRAPH = "INIT_GRAPH"

class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None

class TaskCompleteCallback(ABC):
    @abstractmethod
    def __call__(self, db_session: Session, task_result: TaskResult, ex_time: float):
        raise NotImplementedError()

class Task(BaseModel):
    """
    Task datatype
    """
    type: TaskType
    task_id: str = Field(default_factory=lambda: generate_id())
    result: Optional[Any] = Field(default=None)
    status: str = Field(default=TaskStatus.PENDING.value)
    task_args: Optional[Any] = Field(default=None)
    post_complete: Optional[Any] = Field(default=None)

    @abstractmethod
    def task(self, **kwargs):
        raise NotImplementedError()
