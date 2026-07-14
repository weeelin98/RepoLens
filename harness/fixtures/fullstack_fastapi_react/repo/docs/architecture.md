# Task flow

`TaskPanel` calls `fetchTask`, which issues `GET /api/tasks/{task_id}`. FastAPI dispatches
to `read_task`, then `require_task` loads a `Task` through `get_task`.

Dynamic URLs and proxy rewrites are outside this fixture.
