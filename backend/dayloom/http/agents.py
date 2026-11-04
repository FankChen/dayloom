import time

from dayloom.agents import (
    model_binding,
    next_ordinal,
    require_model,
    run_summary,
    run_view,
    tool_catalog,
)
from dayloom.db import Action, AgentRun, AgentStep, record, timestamp
from dayloom.dependencies import get_session
from dayloom.models import model_status
from dayloom.registry import providers, routers
from dayloom.schemas import AgentInput, AgentResumeInput
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update


@routers.register
class AgentRoutes:
    def __init__(self, settings):
        self.settings = settings

    def install(self, app):
        router = APIRouter(prefix="/api/agent", tags=["agent"])

        def get_run(session, run_id):
            run = session.scalar(select(AgentRun).where(AgentRun.id == run_id).with_for_update())
            if not run:
                raise HTTPException(404, "Agent run not found")
            return run

        @router.get("/tools")
        def catalog(session=Depends(get_session)):
            status = model_status(session, self.settings)
            return {
                "tools": tool_catalog(session, self.settings),
                "model_ready": bool(
                    status["configured"]
                    and callable(getattr(providers.classes.get(status["name"]), "plan", None))
                ),
                "model_external": status["external"],
            }

        @router.get("/runs")
        def runs(session=Depends(get_session)):
            return [
                {**run_summary(run), "goal": run.goal[:160], "summary": run.summary[:300]}
                for run in session.scalars(
                    select(AgentRun).order_by(AgentRun.created_at.desc()).limit(50)
                )
            ]

        @router.get("/runs/{run_id}")
        def run_detail(run_id: str, session=Depends(get_session)):
            return run_view(session, get_run(session, run_id))

        @router.post("/runs", status_code=201)
        def create_run(payload: AgentInput, session=Depends(get_session)):
            require_model(session, self.settings, payload.allow_external)
            if (
                session.scalar(
                    select(func.count())
                    .select_from(AgentRun)
                    .where(AgentRun.status.not_in(["completed", "cancelled"]))
                )
                >= 10
            ):
                raise HTTPException(
                    409, "Finish or cancel an existing Agent run before starting another."
                )
            allowed = set(payload.allowed_tools)
            available = {
                item["name"] for item in tool_catalog(session, self.settings) if item["available"]
            }
            if not allowed.issubset(available):
                raise HTTPException(422, "Choose only tools available in this workspace.")
            run = AgentRun(
                goal=payload.goal,
                allowed_tools=sorted(allowed),
                model_binding=model_binding(session, self.settings),
                allow_external=int(payload.allow_external),
                auto_readonly=int(payload.auto_readonly),
                max_steps=payload.max_steps,
            )
            session.add(run)
            session.flush()
            record(
                session, "agent.created", run.id, tools=run.allowed_tools, max_steps=run.max_steps
            )
            session.commit()
            return run_view(session, run)

        @router.post("/runs/{run_id}/pause")
        def pause(run_id: str, session=Depends(get_session)):
            run = get_run(session, run_id)
            if run.status in {"completed", "cancelled"}:
                raise HTTPException(409, "This Agent run has already ended.")
            run.status = "paused"
            run.claim_token = None
            run.lease_until = None
            run.updated_at = timestamp()
            session.execute(
                update(Action)
                .where(Action.agent_run_id == run.id, Action.status == "queued")
                .values(status="pending", approved_digest=None, updated_at=timestamp())
            )
            record(session, "agent.paused", run.id)
            session.commit()
            return run_view(session, run)

        @router.post("/runs/{run_id}/cancel")
        def cancel(run_id: str, session=Depends(get_session)):
            run = get_run(session, run_id)
            if run.status == "completed":
                raise HTTPException(409, "This Agent run has already ended.")
            run.status = "cancelled"
            run.claim_token = None
            run.lease_until = None
            run.updated_at = timestamp()
            session.execute(
                update(Action)
                .where(Action.agent_run_id == run.id, Action.status.in_(["pending", "queued"]))
                .values(status="cancelled", approved_digest=None, updated_at=timestamp())
            )
            record(session, "agent.cancelled", run.id)
            session.commit()
            return run_view(session, run)

        @router.post("/runs/{run_id}/resume")
        def resume(run_id: str, payload: AgentResumeInput, session=Depends(get_session)):
            run = get_run(session, run_id)
            if run.status not in {"paused", "needs_input"}:
                raise HTTPException(409, "Only paused runs or runs needing input can continue.")
            if session.scalar(
                select(Action.id)
                .where(
                    Action.agent_run_id == run.id, Action.status.in_(["running", "outcome_unknown"])
                )
                .limit(1)
            ):
                raise HTTPException(
                    409, "Wait for or reconcile the running tool before continuing."
                )
            if payload.max_steps <= run.steps:
                raise HTTPException(422, "Choose a step limit larger than the steps already used.")
            require_model(session, self.settings, payload.allow_external)
            session.execute(
                update(Action)
                .where(Action.agent_run_id == run.id, Action.status.in_(["pending", "queued"]))
                .values(status="cancelled", approved_digest=None, updated_at=timestamp())
            )
            if payload.message:
                session.add(
                    AgentStep(
                        agent_run_id=run.id,
                        ordinal=next_ordinal(session, run.id),
                        decision="user",
                        message=payload.message,
                    )
                )
            run.status = "queued"
            run.max_steps = payload.max_steps
            run.model_binding = model_binding(session, self.settings)
            run.allow_external = int(payload.allow_external)
            run.expires_at = time.time() + 3600
            run.error = None
            run.updated_at = timestamp()
            record(session, "agent.resumed", run.id, max_steps=run.max_steps)
            session.commit()
            return run_view(session, run)

        app.include_router(router)
