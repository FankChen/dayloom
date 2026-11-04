import hashlib
import json
import time
from typing import Any


def action_digest(tool: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        {"tool": tool, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def require_approval(tool: str, payload: dict[str, Any], approved_digest: str | None) -> None:
    if approved_digest is None or approved_digest != action_digest(tool, payload):
        raise ValueError("This exact action has not been approved.")


def automation_digest(rule) -> str:
    return action_digest(
        "Automation",
        {
            "tool": rule.tool,
            "payload": rule.payload,
            "starts_at": rule.starts_at,
            "interval_seconds": rule.interval_seconds,
            "max_runs": rule.max_runs,
            "expires_at": rule.expires_at,
        },
    )


def require_agent_authority(action, session):
    from dayloom.db import AgentRun
    from dayloom.executors import AuthorityRevoked

    if action.agent_run_id:
        run = session.get(AgentRun, action.agent_run_id)
        if (
            not run
            or run.status != "waiting_approval"
            or run.expires_at <= time.time()
            or action.tool not in run.allowed_tools
        ):
            raise AuthorityRevoked()


def require_action_authority(action, session):
    from dayloom.db import AutomationRule
    from dayloom.executors import AuthorityRevoked

    require_approval(action.tool, action.payload, action.approved_digest)
    require_agent_authority(action, session)
    if action.automation_id:
        rule = session.get(AutomationRule, action.automation_id)
        if (
            not rule
            or not rule.active
            or rule.expires_at <= time.time()
            or automation_digest(rule) != rule.approved_digest
            or action_digest(rule.tool, rule.payload) != action.digest
        ):
            raise AuthorityRevoked()
