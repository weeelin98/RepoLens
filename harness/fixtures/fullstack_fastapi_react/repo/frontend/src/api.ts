export type Task = { id: number; title: string };

export async function fetchTask(taskId: number): Promise<Task> {
  const response = await fetch(`/api/tasks/${taskId}`, { method: "GET" });
  return response.json() as Promise<Task>;
}
