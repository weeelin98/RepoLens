from fastapi import FastAPI, HTTPException

from backend.models import Task
from backend.service import require_task

app = FastAPI()


@app.get("/api/tasks/{task_id}")
def read_task(task_id: int) -> Task:
    try:
        return require_task(task_id)
    except LookupError as error:
        raise HTTPException(status_code=404) from error
