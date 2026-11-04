import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

LEGACY_WORKSPACE_ID = "00000000-0000-0000-0000-000000000000"


def identifier() -> str:
    return str(uuid4())


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(200), default="Personal workspace")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


@event.listens_for(Workspace.__table__, "after_create")
def create_legacy_workspace(_table, connection, **_kwargs):
    connection.execute(
        Workspace.__table__.insert().values(id=LEGACY_WORKSPACE_ID, name="Local workspace")
    )


class WorkspaceOwned:
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), default=LEGACY_WORKSPACE_ID, nullable=False, index=True
    )


class AccountIdentity(Base):
    __tablename__ = "account_identities"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_identity_subject"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    issuer: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="Personal account")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class AccountSession(Base):
    __tablename__ = "account_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    identity_id: Mapped[str] = mapped_column(ForeignKey("account_identities.id"), index=True)
    access_hash: Mapped[str] = mapped_column(String(64), unique=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    access_expires_at: Mapped[float] = mapped_column(Float)
    expires_at: Mapped[float] = mapped_column(Float)
    device: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class LoginFlow(Base):
    __tablename__ = "login_flows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[float] = mapped_column(Float, index=True)


class ModelConnection(WorkspaceOwned, Base):
    __tablename__ = "model_connections"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_workspace_model"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    provider: Mapped[str] = mapped_column(String(80))
    base_url: Mapped[str] = mapped_column(String(500))
    model: Mapped[str] = mapped_column(String(200))
    secret: Mapped[str] = mapped_column(Text)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2400)
    daily_limit: Mapped[int] = mapped_column(Integer, default=100)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class ModelUsage(WorkspaceOwned, Base):
    __tablename__ = "model_usage"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True, default=LEGACY_WORKSPACE_ID
    )
    requests: Mapped[int] = mapped_column(Integer, default=0)


class Integration(WorkspaceOwned, Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    kind: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(200))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    secret: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class IntegrationUsage(WorkspaceOwned, Base):
    __tablename__ = "integration_usage"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    kind: Mapped[str] = mapped_column(String(80), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True, default=LEGACY_WORKSPACE_ID
    )
    requests: Mapped[int] = mapped_column(Integer, default=0)


class AutomationRule(WorkspaceOwned, Base):
    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(200))
    tool: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    approved_digest: Mapped[str] = mapped_column(String(64))
    starts_at: Mapped[float] = mapped_column(Float)
    next_run_at: Mapped[float] = mapped_column(Float, index=True)
    interval_seconds: Mapped[int] = mapped_column(Integer)
    max_runs: Mapped[int] = mapped_column(Integer)
    runs_created: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[float] = mapped_column(Float)
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Task(WorkspaceOwned, Base):
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


class Memory(WorkspaceOwned, Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20), default="preference")
    source: Mapped[str] = mapped_column(String(200), default="User confirmed")
    expires_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Message(WorkspaceOwned, Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(80), default="user")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class AgentRun(WorkspaceOwned, Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    allowed_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_binding: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    allow_external: Mapped[int] = mapped_column(Integer, default=0)
    auto_readonly: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[int] = mapped_column(Integer, default=0)
    max_steps: Mapped[int] = mapped_column(Integer, default=8)
    expires_at: Mapped[float] = mapped_column(Float, default=lambda: time.time() + 3600)
    summary: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[float | None] = mapped_column(Float, nullable=True)
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class AgentStep(WorkspaceOwned, Base):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("agent_run_id", "ordinal", name="uq_agent_step_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    action_id: Mapped[str | None] = mapped_column(ForeignKey("actions.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Artifact(WorkspaceOwned, Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Action(WorkspaceOwned, Base):
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
    effect_started_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    automation_id: Mapped[str | None] = mapped_column(
        ForeignKey("automation_rules.id"), nullable=True
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True, index=True
    )
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Audit(WorkspaceOwned, Base):
    __tablename__ = "audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    event: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class CalendarEvent(WorkspaceOwned, Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True, default=LEGACY_WORKSPACE_ID
    )
    title: Mapped[str] = mapped_column(String(200))
    start: Mapped[str] = mapped_column(String(40))
    end: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(200))
    imported_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Preference(WorkspaceOwned, Base):
    __tablename__ = "preferences"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True, default=LEGACY_WORKSPACE_ID
    )
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
