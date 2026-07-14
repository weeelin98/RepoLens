from backend.models import Task

TASKS = {1: Task(id=1, title="Ship RepoLens")}


def get_task(task_id: int) -> Task | None:
    return TASKS.get(task_id)
