from dayloom.registry import providers
from dayloom.schemas import ModelReply, Proposal


@providers.register
class DemoProvider:
    external = False
    label = "Offline demo"

    async def reply(self, content: str, context: dict) -> ModelReply:
        normalized = content.casefold()
        if normalized.startswith("remember:") and content[9:].strip():
            return ModelReply(
                message="I've prepared a memory for your review. Nothing is saved until you approve it.",
                proposals=[
                    Proposal(
                        tool="SaveMemory",
                        payload={"content": content[9:].strip()[:3000], "category": "preference"},
                    )
                ],
            )
        if normalized in {"plan my day", "daily brief", "prepare my day"}:
            return ModelReply(
                message="Your daily brief is ready to queue. It will use your tasks and imported calendar.",
                proposals=[Proposal(tool="PrepareBrief", payload={"day": context["today"]})],
            )
        return ModelReply(
            message="I've turned your note into a task suggestion. Review the title and estimate before approving. This is the offline demo, not a language model.",
            proposals=[
                Proposal(
                    tool="CreateTask",
                    payload={"title": content[:200], "notes": content[:5000], "minutes": 30},
                )
            ],
        )
