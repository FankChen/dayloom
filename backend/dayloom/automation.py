import copy
import time

from sqlalchemy import select, update

from dayloom.db import Action, AutomationRule, record
from dayloom.policy import action_digest, automation_digest
from dayloom.workspaces import WorkspaceSession


def materialize_due(engine, workspace_id):
    now = time.time()
    with WorkspaceSession(engine, workspace_id=workspace_id) as session:
        candidates = session.scalars(
            select(AutomationRule)
            .where(
                AutomationRule.active == 1,
                AutomationRule.next_run_at <= now,
                AutomationRule.expires_at > now,
                AutomationRule.runs_created < AutomationRule.max_runs,
            )
            .order_by(AutomationRule.next_run_at)
            .limit(20)
        ).all()
        for rule in candidates:
            if rule.approved_digest != automation_digest(rule):
                continue
            previous_run = rule.next_run_at
            changed = session.execute(
                update(AutomationRule)
                .where(
                    AutomationRule.id == rule.id,
                    AutomationRule.active == 1,
                    AutomationRule.next_run_at == previous_run,
                    AutomationRule.runs_created < AutomationRule.max_runs,
                )
                .values(
                    next_run_at=now + rule.interval_seconds,
                    runs_created=AutomationRule.runs_created + 1,
                )
            )
            if changed.rowcount != 1:
                continue
            digest = action_digest(rule.tool, rule.payload)
            action = Action(
                tool=rule.tool,
                payload=copy.deepcopy(rule.payload),
                digest=digest,
                approved_digest=digest,
                automation_id=rule.id,
                status="queued",
            )
            session.add(action)
            session.flush()
            record(session, "automation.enqueued", action.id, automation_id=rule.id)
        session.commit()
