from cowboy_lib.api.runner.shared import Task

from typing import Optional, List, Dict

from src.queue.core import TaskQueue


def list_tasks(*, task_queue: TaskQueue, user_id: int, n: int) -> Optional[List[Task]]:
    """List all tasks in the queue."""

    return task_queue.peak(user_id, n)


def enqueue_task(*, task_queue: TaskQueue, task: Task, user_id: int):
    """Enqueue a task to the specified queue and wait for its completion."""
    task_queue.put(user_id, task)


def enqueue_task_and_wait(*, task_queue: TaskQueue, task: Task, user_id: int):
    """Enqueue a task to the specified queue and wait for its completion."""
    return task_queue.put_and_wait(user_id, task)


async def get_task(*, task_queue: TaskQueue, task_id: str) -> Optional[Task]:
    return task_queue.get(task_id)
