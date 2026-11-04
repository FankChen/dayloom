import logging
import signal
import threading
import time
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from dayloom.automation import materialize_due
from dayloom.config import Settings
from dayloom.db import (
    LEGACY_WORKSPACE_ID,
    Action,
    Preference,
    Workspace,
    build_engine,
    record,
    timestamp,
)
from dayloom.migrations import initialize_runtime
from dayloom.registry import discover_plugins, executors, jobs, tools
from dayloom.workspaces import WorkspaceSession

logger = logging.getLogger("dayloom.worker")


def run_once(engine, settings: Settings, workspace_id=LEGACY_WORKSPACE_ID) -> bool:
    materialize_due(engine, workspace_id)
    now = time.time()
    eligible = or_(
        (Action.status == "queued") & (Action.run_after <= now),
        (Action.status == "running") & (Action.lease_until < now),
    )
    claim = str(uuid4())
    with WorkspaceSession(engine, workspace_id=workspace_id) as session:
        heartbeat = session.get(Preference, "worker")
        if heartbeat:
            heartbeat.value = {"heartbeat": now}
        else:
            session.add(Preference(key="worker", value={"heartbeat": now}))
        session.commit()
        action_id = session.scalar(
            select(Action.id).where(eligible).order_by(Action.created_at).limit(1)
        )
        if not action_id:
            session.rollback()
            return any(
                jobs.build(
                    name, engine=engine, settings=settings, workspace_id=workspace_id
                ).run_once()
                for name in jobs.classes
            )
        changed = session.execute(
            update(Action)
            .where(Action.id == action_id, eligible)
            .values(
                status="running",
                lease_until=now + settings.worker_lease_seconds,
                claim_token=claim,
                attempts=Action.attempts + 1,
                updated_at=timestamp(),
            )
        )
        session.commit()
        if changed.rowcount != 1:
            return False
        tool_name = session.scalar(select(Action.tool).where(Action.id == action_id))
    try:
        implementation = tools.classes[tool_name]
        executors.build(
            getattr(implementation, "executor", "LocalExecution"),
            engine=engine,
            settings=settings,
            workspace_id=workspace_id,
            action_id=action_id,
            claim=claim,
        ).run()
    except Exception as error:
        logger.warning("Action %s failed; payload and credentials omitted", action_id)
        status = getattr(error, "status", "failed")
        with WorkspaceSession(engine, workspace_id=workspace_id) as session, session.begin():
            changed = session.execute(
                update(Action)
                .where(
                    Action.id == action_id,
                    Action.claim_token == claim,
                    Action.status == "running",
                )
                .values(
                    status=status,
                    lease_until=None,
                    error=getattr(
                        error,
                        "public_message",
                        "Execution failed. Review the action before retrying.",
                    ),
                    updated_at=timestamp(),
                )
            )
            if changed.rowcount:
                record(session, f"action.{status}", action_id)
    return True


def main():
    settings = Settings()
    engine = build_engine(settings.database_url)
    initialize_runtime(engine, settings)
    discover_plugins()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_args: stop.set())
    signal.signal(signal.SIGINT, lambda *_args: stop.set())
    logging.basicConfig(level=logging.INFO)
    logger.info("Dayloom worker started")
    try:
        while not stop.is_set():
            with Session(engine) as session:
                workspace_ids = session.scalars(select(Workspace.id)).all()
            worked = False
            for workspace_id in workspace_ids:
                worked = run_once(engine, settings, workspace_id) or worked
            if not worked:
                stop.wait(settings.worker_poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
