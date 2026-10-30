import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Float, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def identifier() -> str:
    return str(uuid4())


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="ready")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    minutes: Mapped[int] = mapped_column(Integer, default=30)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(200), default="Manual entry")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20), default="preference")
    source: Mapped[str] = mapped_column(String(200), default="User confirmed")
    expires_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(80), default="user")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    tool: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    approved_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_after: Mapped[float] = mapped_column(Float, default=time.time)
    lease_until: Mapped[float | None] = mapped_column(Float, nullable=True)
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Audit(Base):
    __tablename__ = "audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    event: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    start: Mapped[str] = mapped_column(String(40))
    end: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(200))
    imported_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Preference(Base):
    __tablename__ = "preferences"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)


def build_engine(database_url: str):
    from pathlib import Path

    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            database_url, connect_args={"check_same_thread": False, "timeout": 15}
        )

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _record):
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
    else:
        engine = create_engine(database_url, pool_pre_ping=True)
    return engine


def record(session, event_name: str, entity_id: str, **details):
    session.add(Audit(event=event_name, entity_id=entity_id, details=details))


def as_dict(entity) -> dict[str, Any]:
    return {column.name: getattr(entity, column.name) for column in entity.__table__.columns}
