import logging
import signal
import threading
import time
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from dayloom.config import Settings
from dayloom.db import Action, Base, Preference, build_engine, record, timestamp
from dayloom.policy import require_approval
from dayloom.registry import discover_plugins, tools

logger = logging.getLogger("dayloom.worker")


def run_once(engine, settings: Settings) -> bool:
    now = time.time()
    eligible = or_(
        (Action.status == "queued") & (Action.run_after <= now),
        (Action.status == "running") & (Action.lease_until < now),
    )
    claim = str(uuid4())
    with Session(engine) as session:
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
            return False
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
    try:
        with Session(engine) as session, session.begin():
            action = session.scalar(select(Action).where(Action.id == action_id).with_for_update())
            if not action or action.claim_token != claim or action.status != "running":
                return False
            if action.attempts > 3:
                raise ValueError("Recovery limit reached. Review and retry this action.")
            require_approval(action.tool, action.payload, action.approved_digest)
            tool = tools.build(action.tool, session=session, settings=settings)
            result = tool.execute(tool.input_model.model_validate(action.payload))
            action.result = result
            action.status = "succeeded"
            action.error = None
            action.lease_until = None
            action.updated_at = timestamp()
            record(session, "action.succeeded", action.id, tool=action.tool)
    except Exception:
        logger.warning("Action %s failed; payload and credentials omitted", action_id)
        with Session(engine) as session, session.begin():
            changed = session.execute(
                update(Action)
                .where(
                    Action.id == action_id,
                    Action.claim_token == claim,
                    Action.status == "running",
                )
                .values(
                    status="failed",
                    lease_until=None,
                    error="Execution failed. Review the action before retrying.",
                    updated_at=timestamp(),
                )
            )
            if changed.rowcount:
                record(session, "action.failed", action_id)
    return True


def main():
    settings = Settings()
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    discover_plugins()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_args: stop.set())
    signal.signal(signal.SIGINT, lambda *_args: stop.set())
    logging.basicConfig(level=logging.INFO)
    logger.info("Dayloom worker started")
    try:
        while not stop.is_set():
            if not run_once(engine, settings):
                stop.wait(settings.worker_poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
