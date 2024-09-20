from enum import Enum
from typing import Dict, Optional, Any, Callable
from pydantic import BaseModel, Field, model_validator
from cowboy_lib.api.runner.shared import generate_id
from abc import abstractmethod


class TaskType(str, Enum):
    INIT_GRAPH = "INIT_GRAPH"


class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class TaskResult(BaseModel):
    coverage: Optional[Dict] = None
    failed: Optional[Dict] = None
    exception: Optional[str] = None

    @model_validator(mode="before")
    def check_coverage_or_exception(cls, values):
        coverage, failed, exception = (
            values.get("coverage"),
            values.get("failed"),
            values.get("exception"),
        )
        if exception and (coverage or failed):
            raise ValueError(
                "If 'exception' is specified, 'coverage' and 'failed' must not be specified."
            )
        if not exception and not (coverage or failed):
            raise ValueError(
                "Either 'coverage' and 'failed' or 'exception' must be specified."
            )
        return values


class Task(BaseModel):
    """
    Task datatype
    """

    type: TaskType
    task_id: str = Field(default_factory=lambda: generate_id())
    result: Optional[TaskResult] = Field(default=None)
    status: str = Field(default=TaskStatus.PENDING.value)
    task_args: Optional[Any] = Field(default=None)

    @abstractmethod
    def task(self, **kwargs):
        raise NotImplementedError()


class TaskResponse(BaseModel):
    task_id: str


class CompleteTaskRequest(Task):
    pass


class GetTaskResponse(Task):
    pass
