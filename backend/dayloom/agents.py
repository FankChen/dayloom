import asyncio
import json
import time

from fastapi import HTTPException
from sqlalchemy import func, select, update

from dayloom.actions import action_view, add_proposal
from dayloom.db import (
    Action,
    AgentRun,
    AgentStep,
    Integration,
    as_dict,
    identifier,
    record,
    timestamp,
)
from dayloom.models import model_status, reserve_model_request, resolve_model
from dayloom.registry import providers, tools
from dayloom.schemas import AgentDecision
from dayloom.workspaces import WorkspaceSession


def model_binding(session, settings):
    status = model_status(session, settings)
    return {key: status.get(key) for key in ("name", "model", "base_url", "version", "managed")}


def tool_catalog(session, settings):
    connections = {connection.kind for connection in session.scalars(select(Integration))}
    return [
        {
            "name": name,
            "label": implementation.label,
            "description": implementation.description,
            "input_schema": implementation.input_model.model_json_schema(),
            "read_only": bool(getattr(implementation, "read_only", False)),
            "execution": getattr(implementation, "executor", "LocalExecution"),
            "available": bool(
                getattr(implementation, "available", lambda _settings: True)(settings)
            )
            and (
                not getattr(implementation, "connection_kind", None)
                or implementation.connection_kind in connections
            )
            and bool(
                getattr(implementation, "ready", lambda _session, _settings: True)(
                    session, settings
                )
            ),
            "connection_kind": getattr(implementation, "connection_kind", None),
        }
        for name, implementation in tools.classes.items()
    ]


def next_ordinal(session, run_id):
    return (
        session.scalar(select(func.max(AgentStep.ordinal)).where(AgentStep.agent_run_id == run_id))
        or 0
    ) + 1


def run_summary(run):
    return {
        key: value
        for key, value in as_dict(run).items()
        if key not in {"claim_token", "lease_until", "model_binding"}
    }


def run_view(session, run):
    result = run_summary(run)
    result["steps_history"] = [
        {
            **as_dict(step),
            "action": action_view(action)
            if (action := session.get(Action, step.action_id))
            else None,
        }
        if step.action_id
        else {**as_dict(step), "action": None}
        for step in session.scalars(
            select(AgentStep).where(AgentStep.agent_run_id == run.id).order_by(AgentStep.ordinal)
        )
    ]
    return result


def require_model(session, settings, allow_external):
    status = model_status(session, settings)
    configured = resolve_model(session, settings)
    provider = providers.build(configured.model_provider, settings=configured)
    if not status["configured"] or not callable(getattr(provider, "plan", None)):
        raise HTTPException(422, "Connect an Agent-compatible model before starting.")
    if status["external"] and not allow_external:
        raise HTTPException(
            400, "Allow sharing this goal and approved tool results with your model first."
        )
    return provider


def pause_run(session, run, reason):
    changed = session.execute(
        update(AgentRun)
        .where(
            AgentRun.id == run.id,
            AgentRun.status == run.status,
            AgentRun.steps == run.steps,
            AgentRun.claim_token == run.claim_token,
        )
        .values(
            status="paused",
            error=reason,
            claim_token=None,
            lease_until=None,
            updated_at=timestamp(),
        )
    )
    if changed.rowcount:
        record(session, "agent.paused", run.id)
    session.commit()


def planning_context(session, run, settings):
    history = []
    results = []
    connection_kinds = {
        kind
        for name in run.allowed_tools
        if (implementation := tools.classes.get(name)) is not None
        and (kind := getattr(implementation, "connection_kind", None))
    }
    steps = list(
        session.scalars(
            select(AgentStep)
            .where(AgentStep.agent_run_id == run.id)
            .order_by(AgentStep.ordinal.desc())
            .limit(12)
        )
    )
    for step in reversed(steps):
        history.append({"decision": step.decision, "message": step.message})
        if step.action_id and (action := session.get(Action, step.action_id)):
            serialized = json.dumps(action.result, ensure_ascii=False)
            result = (
                action.result
                if len(serialized) <= 6000
                else {"excerpt": serialized[:6000], "truncated": True}
            )
            results.append(
                {
                    "action_id": action.id,
                    "tool": action.tool,
                    "payload": action.payload,
                    "status": action.status,
                    "result": result,
                    "error": action.error,
                }
            )
    return {
        "agent": {
            "run_id": run.id,
            "steps_used": run.steps,
            "max_steps": run.max_steps,
            "expires_at": run.expires_at,
        },
        "tools": [
            item
            for item in tool_catalog(session, settings)
            if item["name"] in run.allowed_tools and item["available"]
        ],
        "history": history,
        "tool_results": results,
        "connections": [
            {
                "id": connection.id,
                "kind": connection.kind,
                "label": connection.label,
                "version": connection.version,
                "sender": connection.configuration.get("username"),
                "tools": connection.configuration.get("tools", []),
            }
            for connection in session.scalars(
                select(Integration).where(Integration.kind.in_(connection_kinds))
            )
        ],
    }


def advance_agent(engine, settings, workspace_id):
    now = time.time()
    with WorkspaceSession(engine, workspace_id=workspace_id) as session:
        candidates = session.scalars(
            select(AgentRun)
            .where(AgentRun.status.in_(["queued", "waiting_approval", "planning"]))
            .order_by(AgentRun.created_at)
            .limit(50)
        ).all()
        selected = None
        for run in candidates:
            if run.status == "planning":
                if run.lease_until is not None and run.lease_until < now:
                    pause_run(
                        session, run, "Planning was interrupted. Review the run before continuing."
                    )
                    return True
                continue
            if run.expires_at <= now:
                pause_run(
                    session, run, "Agent authorization expired. Review and continue to renew it."
                )
                return True
            if run.status == "waiting_approval":
                step = session.scalar(
                    select(AgentStep)
                    .where(AgentStep.agent_run_id == run.id)
                    .order_by(AgentStep.ordinal.desc())
                    .limit(1)
                )
                action = session.get(Action, step.action_id) if step and step.action_id else None
                if not action:
                    pause_run(
                        session, run, "A tool action is missing. Review the run before continuing."
                    )
                    return True
                if action.status in {"pending", "queued", "running"}:
                    continue
                if action.status in {"cancelled", "outcome_unknown"}:
                    pause_run(
                        session,
                        run,
                        "A tool was cancelled or its outcome is uncertain. Review it before continuing.",
                    )
                    return True
            selected = run
            break
        if selected is None:
            return False
        run = selected
        if run.steps >= run.max_steps:
            pause_run(
                session,
                run,
                "Step limit reached. Review the results and explicitly increase the limit to continue.",
            )
            return True
        try:
            provider = require_model(session, settings, bool(run.allow_external))
            if model_binding(session, settings) != run.model_binding:
                raise HTTPException(
                    409, "Model settings changed. Review sharing permission before continuing."
                )
        except Exception as error:
            pause_run(
                session,
                run,
                getattr(error, "detail", "Model settings unavailable. Review before continuing."),
            )
            return True
        claim = identifier()
        run_id, goal = run.id, run.goal
        changed = session.execute(
            update(AgentRun)
            .where(
                AgentRun.id == run_id, AgentRun.status == run.status, AgentRun.steps == run.steps
            )
            .values(
                status="planning",
                steps=AgentRun.steps + 1,
                claim_token=claim,
                lease_until=now + max(settings.worker_lease_seconds, 120),
                updated_at=timestamp(),
                error=None,
            )
        )
        session.commit()
        if changed.rowcount != 1:
            return False
        try:
            reserve_model_request(session)
            run = session.get(AgentRun, run_id)
            context = planning_context(session, run, settings)
        except Exception:
            pause_run(
                session,
                session.get(AgentRun, run_id),
                "Model request limit reached or context unavailable. Review before continuing.",
            )
            return True
    try:

        async def plan():
            return await asyncio.wait_for(provider.plan(goal, context), timeout=60)

        decision = AgentDecision.model_validate(asyncio.run(plan()))
        if decision.decision == "finish" and not any(
            result["status"] == "succeeded" for result in context["tool_results"]
        ):
            raise ValueError("A completed Agent run requires a real successful tool result")
        with WorkspaceSession(engine, workspace_id=workspace_id) as session, session.begin():
            run = session.scalar(select(AgentRun).where(AgentRun.id == run_id).with_for_update())
            if not run or run.status != "planning" or run.claim_token != claim:
                return True
            if run.expires_at <= time.time():
                run.status = "paused"
                run.error = "Agent authorization expired. Review and continue to renew it."
                run.claim_token = None
                run.lease_until = None
                return True
            action = None
            if decision.proposal:
                available = {
                    item["name"] for item in tool_catalog(session, settings) if item["available"]
                }
                if (
                    decision.proposal.tool not in run.allowed_tools
                    or decision.proposal.tool not in available
                ):
                    raise ValueError("Tool outside the authorized available set")
                action = add_proposal(session, decision.proposal, agent_run_id=run.id)
                if run.auto_readonly and getattr(tools.classes[action.tool], "read_only", False):
                    action.status = "queued"
                    action.approved_digest = action.digest
                    record(session, "action.approved_readonly", action.id, agent_run_id=run.id)
            session.add(
                AgentStep(
                    agent_run_id=run.id,
                    ordinal=next_ordinal(session, run.id),
                    decision=decision.decision,
                    message=decision.message,
                    action_id=action.id if action else None,
                )
            )
            run.status = {
                "act": "waiting_approval",
                "finish": "completed",
                "ask_user": "needs_input",
            }[decision.decision]
            run.summary = decision.message
            run.claim_token = None
            run.lease_until = None
            run.updated_at = timestamp()
            record(session, "agent.progressed", run.id, decision=decision.decision, steps=run.steps)
    except Exception:
        with WorkspaceSession(engine, workspace_id=workspace_id) as session:
            run = session.get(AgentRun, run_id)
            if run and run.status == "planning" and run.claim_token == claim:
                pause_run(
                    session,
                    run,
                    "Agent planning failed or requested an unavailable tool. Review before continuing.",
                )
    return True
