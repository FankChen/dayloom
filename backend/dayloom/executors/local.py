from sqlalchemy import select

from dayloom.db import Action, record, timestamp
from dayloom.policy import require_action_authority
from dayloom.registry import executors, tools
from dayloom.workspaces import WorkspaceSession


@executors.register
class LocalExecution:
    def __init__(self, engine, settings, workspace_id, action_id, claim):
        self.engine = engine
        self.settings = settings
        self.workspace_id = workspace_id
        self.action_id = action_id
        self.claim = claim

    def run(self):
        with (
            WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session,
            session.begin(),
        ):
            action = session.scalar(
                select(Action).where(Action.id == self.action_id).with_for_update()
            )
            if not action or action.claim_token != self.claim or action.status != "running":
                return
            if action.attempts > 3:
                raise ValueError("Recovery limit reached")
            require_action_authority(action, session)
            tool = tools.build(
                action.tool, session=session, settings=self.settings, action_id=action.id
            )
            action.result = tool.execute(tool.input_model.model_validate(action.payload))
            action.status = "succeeded"
            action.error = None
            action.lease_until = None
            action.updated_at = timestamp()
            record(session, "action.succeeded", action.id, tool=action.tool)
