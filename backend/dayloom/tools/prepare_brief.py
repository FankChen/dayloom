from dayloom.planning import build_plan
from dayloom.registry import tools
from dayloom.schemas import BriefInput


@tools.register
class PrepareBrief:
    label = "Prepare a daily brief"
    description = (
        "Build a local daily brief from task priorities and imported calendar availability."
    )
    input_model = BriefInput

    def __init__(self, session):
        self.session = session

    def execute(self, payload: BriefInput) -> dict:
        plan = build_plan(self.session, payload.day)
        return {"kind": "brief", "title": f"Daily brief / {payload.day}", "plan": plan}
