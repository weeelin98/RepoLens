import { useEffect, useState } from "react";
import { fetchTask, type Task } from "./api";

export function TaskPanel({ taskId }: { taskId: number }) {
  const [task, setTask] = useState<Task | null>(null);
  useEffect(() => { void fetchTask(taskId).then(setTask); }, [taskId]);
  return <section>{task?.title ?? "Loading"}</section>;
}
