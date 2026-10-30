from dayloom.db import Memory
from dayloom.registry import tools
from dayloom.schemas import MemoryInput


@tools.register
class SaveMemory:
    label = "Remember a detail"
    description = "Save an explicitly approved preference, fact, goal, or temporary context."
    input_model = MemoryInput

    def __init__(self, session):
        self.session = session

    def execute(self, payload: MemoryInput) -> dict:
        memory = Memory(**payload.model_dump(mode="json"), source="User-approved conversation")
        self.session.add(memory)
        self.session.flush()
        return {"kind": "memory", "id": memory.id, "title": "Memory saved"}
