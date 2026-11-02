import time
from typing import Literal
from uuid import UUID

from dayloom.db import Action, AutomationRule, as_dict, record, timestamp
from dayloom.dependencies import get_session
from dayloom.policy import automation_digest
from dayloom.registry import routers, tools
from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select, update


class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action_id: UUID
    action_digest: str = Field(min_length=64, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    starts_at: AwareDatetime
    interval_seconds: int = Field(default=86400, ge=60, le=604800)
    max_runs: int = Field(default=1, ge=1, le=100)
    expires_at: AwareDatetime
    approval_digest: str | None = Field(default=None, min_length=64, max_length=64)


class ResolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    outcome: Literal["confirmed_sent", "confirmed_not_sent"]
    evidence: str = Field(min_length=10, max_length=2000)


@routers.register
class AutomationRoutes:
    def install(self, app):
        router = APIRouter(tags=["automation"])

        def proposed_rule(payload, session):
            action = session.get(Action, str(payload.action_id))
            if not action or action.status != "pending" or action.digest != payload.action_digest:
                raise HTTPException(409, "The source action changed or is no longer pending")
            if not getattr(tools.classes[action.tool], "automation_allowed", False):
                raise HTTPException(422, "This tool does not support standing automation authority")
            starts_at, expires_at = payload.starts_at.timestamp(), payload.expires_at.timestamp()
            if (
                starts_at < time.time() - 60
                or expires_at <= starts_at
                or expires_at > time.time() + 90 * 86400
            ):
                raise HTTPException(422, "Choose a future schedule that expires within 90 days")
            rule = AutomationRule(
                name=payload.name,
                tool=action.tool,
                payload=action.payload,
                starts_at=starts_at,
                next_run_at=starts_at,
                interval_seconds=payload.interval_seconds,
                max_runs=payload.max_runs,
                expires_at=expires_at,
            )
            rule.approved_digest = automation_digest(rule)
            return rule, action

        @router.get("/api/automations")
        def list_rules(session=Depends(get_session)):
            return [
                as_dict(rule)
                for rule in session.scalars(
                    select(AutomationRule).order_by(AutomationRule.created_at.desc())
                )
            ]

        @router.post("/api/automations/preview")
        def preview(payload: ScheduleInput, session=Depends(get_session)):
            rule, _action = proposed_rule(payload, session)
            return {
                "approval_digest": rule.approved_digest,
                "tool": rule.tool,
                "payload": rule.payload,
                "starts_at": rule.starts_at,
                "expires_at": rule.expires_at,
                "max_runs": rule.max_runs,
                "interval_seconds": rule.interval_seconds,
            }

        @router.post("/api/automations", status_code=201)
        def create_rule(payload: ScheduleInput, session=Depends(get_session)):
            rule, action = proposed_rule(payload, session)
            if payload.approval_digest != rule.approved_digest:
                raise HTTPException(409, "Review and approve this exact schedule first")
            changed = session.execute(
                update(Action)
                .where(
                    Action.id == action.id,
                    Action.status == "pending",
                    Action.digest == payload.action_digest,
                )
                .values(status="cancelled", approved_digest=None, updated_at=timestamp())
            )
            if changed.rowcount != 1:
                raise HTTPException(409, "The source action changed")
            session.add(rule)
            session.flush()
            record(session, "automation.authorized", rule.id, digest=rule.approved_digest)
            session.commit()
            return as_dict(rule)

        @router.post("/api/automations/{rule_id}/pause", status_code=204)
        def pause_rule(rule_id: str, session=Depends(get_session)):
            rule = session.get(AutomationRule, rule_id)
            if not rule:
                raise HTTPException(404, "Automation not found")
            rule.active = 0
            session.execute(
                update(Action)
                .where(Action.automation_id == rule_id, Action.status.in_(["pending", "queued"]))
                .values(status="cancelled", approved_digest=None, updated_at=timestamp())
            )
            record(session, "automation.paused", rule.id)
            session.commit()

        @router.post("/api/actions/{action_id}/resolve")
        def resolve_action(action_id: str, payload: ResolutionInput, session=Depends(get_session)):
            action = session.get(Action, action_id)
            if not action or action.status != "outcome_unknown":
                raise HTTPException(409, "Only uncertain outcomes can be resolved")
            status = "succeeded" if payload.outcome == "confirmed_sent" else "failed"
            result = {
                "kind": "manual_resolution",
                "title": "Outcome reported by the account owner",
                "source": "user_report",
                "outcome": payload.outcome,
                "evidence": payload.evidence,
            }
            changed = session.execute(
                update(Action)
                .where(Action.id == action.id, Action.status == "outcome_unknown")
                .values(status=status, result=result, error=None, updated_at=timestamp())
            )
            if changed.rowcount != 1:
                raise HTTPException(409, "The outcome changed; refresh before resolving")
            record(session, "action.resolved_by_user", action.id, outcome=payload.outcome)
            session.commit()
            return {"status": status, "result": result}

        app.include_router(router)
