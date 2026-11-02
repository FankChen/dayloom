import time

from sqlalchemy import select, update

from dayloom.db import Action, record, timestamp
from dayloom.executors import AuthorityRevoked, KnownFailure, OutcomeUnknown
from dayloom.executors.local import LocalExecution
from dayloom.policy import require_action_authority
from dayloom.registry import executors, tools
from dayloom.workspaces import WorkspaceSession


@executors.register
class ExternalExecution(LocalExecution):
    def run(self):
        with WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session:
            action = session.scalar(
                select(Action).where(Action.id == self.action_id).with_for_update()
            )
            if not action or action.claim_token != self.claim or action.status != "running":
                return
            require_action_authority(action, session)
            if action.effect_started_at is not None:
                raise OutcomeUnknown()
            tool = tools.build(
                action.tool,
                engine=self.engine,
                settings=self.settings,
                workspace_id=self.workspace_id,
                action_id=action.id,
                claim=self.claim,
            )
            payload = tool.input_model.model_validate(action.payload)
            changed = session.execute(
                update(Action)
                .where(
                    Action.id == self.action_id,
                    Action.claim_token == self.claim,
                    Action.status == "running",
                    Action.effect_started_at.is_(None),
                )
                .values(effect_started_at=time.time())
            )
            if changed.rowcount != 1:
                session.rollback()
                return
            record(session, "action.external_started", action.id, tool=action.tool)
            session.commit()
        try:
            result = tool.execute(payload)
            with (
                WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session,
                session.begin(),
            ):
                changed = session.execute(
                    update(Action)
                    .where(
                        Action.id == self.action_id,
                        Action.claim_token == self.claim,
                        Action.status == "running",
                    )
                    .values(
                        result=result,
                        status="succeeded",
                        error=None,
                        lease_until=None,
                        updated_at=timestamp(),
                    )
                )
                if changed.rowcount:
                    record(session, "action.succeeded", self.action_id)
        except (KnownFailure, AuthorityRevoked):
            raise
        except Exception as error:
            raise OutcomeUnknown() from error
