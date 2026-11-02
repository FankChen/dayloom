from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from dayloom.db import IntegrationUsage
from dayloom.executors import KnownFailure


def reserve_integration_request(session, kind, limit):
    day = datetime.now(UTC).date().isoformat()
    if (
        session.scalar(
            select(IntegrationUsage).where(
                IntegrationUsage.day == day, IntegrationUsage.kind == kind
            )
        )
        is None
    ):
        session.add(IntegrationUsage(day=day, kind=kind, requests=0))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
    changed = session.execute(
        update(IntegrationUsage)
        .where(
            IntegrationUsage.day == day,
            IntegrationUsage.kind == kind,
            IntegrationUsage.requests < limit,
        )
        .values(requests=IntegrationUsage.requests + 1)
    )
    session.commit()
    if changed.rowcount != 1:
        raise KnownFailure("Daily integration request limit reached")
