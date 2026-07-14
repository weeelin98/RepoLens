from backend.models import Task
from backend.repository import get_task


def require_task(task_id: int) -> Task:
    task = get_task(task_id)
    if task is None:
        raise LookupError(task_id)
    return task
