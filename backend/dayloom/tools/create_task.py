from dayloom.db import Task
from dayloom.registry import tools
from dayloom.schemas import TaskInput


@tools.register
class CreateTask:
    label = "Create a task"
    description = "Create one local task with an estimate and optional deadline."
    input_model = TaskInput

    def __init__(self, session):
        self.session = session

    def execute(self, payload: TaskInput) -> dict:
        task = Task(**payload.model_dump(mode="json"), source="Approved assistant suggestion")
        self.session.add(task)
        self.session.flush()
        return {"kind": "task", "id": task.id, "title": task.title}
