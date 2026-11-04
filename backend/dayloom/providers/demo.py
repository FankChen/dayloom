from dayloom.registry import providers
from dayloom.schemas import AgentDecision, ModelReply, Proposal


@providers.register
class DemoProvider:
    external = False
    label = "Offline demo"

    async def plan(self, content: str, context: dict) -> AgentDecision:
        results = context.get("tool_results", [])
        if results:
            saved = next(
                (
                    result
                    for result in results
                    if result["tool"] == "SaveArtifact" and result["status"] == "succeeded"
                ),
                None,
            )
            if saved:
                return AgentDecision(
                    decision="finish",
                    message="Offline demo complete: an explicitly approved demonstration artifact was saved. No research, purchase, device operation or model service was used.",
                )
            return AgentDecision(
                decision="ask_user",
                message="The offline demo cannot recover this operation. Review the tool result before continuing.",
            )
        if not any(tool["name"] == "SaveArtifact" for tool in context.get("tools", [])):
            return AgentDecision(
                decision="ask_user",
                message="This is the offline rules demo, not an AI model. Start a goal with SaveArtifact to test approval and download, or connect a real model.",
            )
        return AgentDecision(
            decision="act",
            message="Offline demo: review this demonstration artifact before saving. No external action will be performed.",
            proposal=Proposal(
                tool="SaveArtifact",
                payload={
                    "title": "Offline demo artifact",
                    "content": f"# Offline demonstration\n\nThis is a rule-based demonstration artifact, not researched content or a completed external action.\n\nRequested goal:\n\n{content}",
                    "sources": [],
                },
            ),
        )

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
