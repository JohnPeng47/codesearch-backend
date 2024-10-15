from .models import Task, TaskStatus

from fastapi import Request
from threading import Lock, Event
from collections import defaultdict
from typing import List, Dict, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future


class TaskQueue:
    """
    A set of queues separated by user_id
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            print("Creating new TaskQueue instance")
            cls._instance = super(TaskQueue, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False

        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Initialize instance variables only once
            self.queue: Dict[str, List[Task]] = defaultdict(list)
            self.locks = defaultdict(list)
            self.executor = ThreadPoolExecutor(
                max_workers=5
            )  # Adjust max_workers as needed
            self._initialized = True  # Mark as initialized

    def _acquire_lock(self, user_id: int):
        if self.locks.get(user_id, None) is None:
            self.locks[user_id] = Lock()
        return self.locks.get(user_id)

    def get(self, task_id: str) -> Task:
        for user_queue in self.queue.values():
            task = next((t for t in user_queue if t.task_id == task_id), None)
            if task:
                return task
        return None

    def put(self, user_id: int, task: Task):
        with self._acquire_lock(user_id):
            if task.status != TaskStatus.PENDING.value:
                raise ValueError("Task must be in PENDING state to be added to queue")

            self.queue[user_id].append(task)
            self.executor.submit(self._execute_and_complete, task, user_id)

    def put_and_wait(self, user_id: int, task: Task) -> Any:
        with self._acquire_lock(user_id):
            if task.status != TaskStatus.PENDING.value:
                raise ValueError("Task must be in PENDING state to be added to queue")

            self.queue[user_id].append(task)
            completion_event = Event()
            future = self.executor.submit(
                self._execute_and_complete_with_event, task, user_id, completion_event
            )

        # Wait for the task to complete
        completion_event.wait()

        # Get the result or raise the exception if one occurred
        try:
            return future.result()
        except Exception as e:
            raise e

    def _execute_and_complete_with_event(
        self, task: Task, user_id: int, completion_event: Event
    ) -> Any:
        try:
            result = self._execute_and_complete(task, user_id)
            return result
        finally:
            completion_event.set()

    def _execute_and_complete(self, task: Task, user_id: int) -> Any:
        with self._acquire_lock(user_id):
            task.status = TaskStatus.STARTED.value

        try:
            print("Started task: ", task.task_id)
            task.result = task.task(**task.task_args)
            task.status = TaskStatus.COMPLETE.value
            return task.result
        except Exception as e:
            print("Task failed with : ", e)
            task.result = str(e)
            task.status = TaskStatus.FAILED.value
            raise e
        finally:
            with self._acquire_lock(user_id):
                for i in range(len(self.queue[user_id])):
                    if self.queue[user_id][i].task_id == task.task_id:
                        self.queue[user_id].pop(i)
                        break

    def get_all(self, user_id: int) -> List[Task]:
        if len(self.queue[user_id]) == 0:
            return []

        tasks = []
        for t in filter(
            lambda t: t.status == TaskStatus.PENDING.value, self.queue[user_id]
        ):
            t.status = TaskStatus.STARTED.value
            tasks.append(t.task)

        return tasks

    def peak(self, user_id: int, n: int) -> List[Task]:
        """
        Get the first n tasks in queue without removing
        """
        if len(self.queue[user_id]) == 0:
            return []

        return [t.task for t in self.queue[user_id][:n]]


def get_queue(request: Request):
    return request.state.task_queue


def get_token_registry(request: Request):
    from main import token_registry

    return token_registry


def get_token(request: Request):
    """
    Returns the user id
    """
    token = request.headers.get("x-task-auth", None)
    # need this or else we end up converting None to "None" **shakes fist @ python moment"
    return str(token) if token else None
