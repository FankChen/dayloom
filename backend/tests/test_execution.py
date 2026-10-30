import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dayloom.db import Action, CalendarEvent, Task
from dayloom.planning import build_plan
from dayloom.policy import action_digest
from dayloom.worker import run_once
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def queued_action(**overrides):
    payload = {"title": "Write outline", "minutes": 30}
    digest = action_digest("CreateTask", payload)
    return Action(
        tool="CreateTask",
        payload=payload,
        digest=digest,
        approved_digest=digest,
        status="queued",
        **overrides,
    )


def test_approved_action_executes_once(engine, settings):
    with Session(engine) as session:
        session.add(queued_action())
        session.commit()
    assert run_once(engine, settings)
    assert not run_once(engine, settings)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Task)) == 1
        assert session.scalar(select(Action)).status == "succeeded"


def test_tampered_payload_cannot_execute(engine, settings):
    with Session(engine) as session:
        action = queued_action()
        action.payload = {"title": "Different instruction", "minutes": 30}
        session.add(action)
        session.commit()
    run_once(engine, settings)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Task)) == 0
        assert session.scalar(select(Action)).status == "failed"


def test_abandoned_lease_is_recovered(engine, settings):
    with Session(engine) as session:
        action = queued_action(lease_until=time.time() - 10, claim_token="old-worker")
        action.status = "running"
        session.add(action)
        session.commit()
    run_once(engine, settings)
    with Session(engine) as session:
        assert session.scalar(select(Action)).status == "succeeded"
        assert session.scalar(select(func.count()).select_from(Task)) == 1


def test_pending_action_never_runs(engine, settings):
    with Session(engine) as session:
        action = queued_action()
        action.status = "pending"
        session.add(action)
        session.commit()
    assert not run_once(engine, settings)


def test_plan_respects_calendar_capacity_and_excludes_blocked(engine):
    with Session(engine) as session:
        session.add_all(
            [
                Task(title="Urgent", minutes=30, priority="high", due_date="2026-10-30"),
                Task(title="Blocked", minutes=30, status="blocked"),
                Task(title="Too large", minutes=240),
                CalendarEvent(
                    id="meeting",
                    title="Meeting",
                    start="2026-10-30T09:00:00+08:00",
                    end="2026-10-30T10:00:00+08:00",
                    source="Test",
                ),
            ]
        )
        session.commit()
        plan = build_plan(
            session, date(2026, 10, 30), datetime(2026, 10, 30, 8, tzinfo=ZoneInfo("Asia/Shanghai"))
        )
        assert len(plan["items"]) == 1
        assert plan["items"][0]["start"] == "2026-10-30T10:00:00+08:00"
        assert plan["planned_minutes"] <= plan["capacity_minutes"]
        assert plan["deadlines"][0]["title"] == "Urgent"


def test_today_does_not_schedule_in_the_past(engine):
    with Session(engine) as session:
        session.add(Task(title="Afternoon work", minutes=30))
        session.commit()
        now = datetime(2026, 10, 30, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        plan = build_plan(session, now.date(), now)
        assert datetime.fromisoformat(plan["items"][0]["start"]) > now
        after_hours = now.replace(hour=21)
        assert build_plan(session, now.date(), after_hours)["items"] == []
