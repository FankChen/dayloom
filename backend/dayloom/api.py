import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from dayloom.access import PUBLIC_AUTH_PATHS
from dayloom.actions import action_view, add_proposal, get_action, validate_proposal
from dayloom.config import Settings
from dayloom.db import (
    Action,
    AgentRun,
    AgentStep,
    Artifact,
    Audit,
    AutomationRule,
    CalendarEvent,
    Integration,
    Memory,
    Message,
    Preference,
    Task,
    as_dict,
    build_engine,
    record,
    timestamp,
)
from dayloom.dependencies import get_session
from dayloom.executors import AuthorityRevoked
from dayloom.migrations import initialize_runtime
from dayloom.models import model_status, reserve_model_request, resolve_model
from dayloom.planning import build_plan, preferences_for
from dayloom.policy import action_digest, require_agent_authority
from dayloom.registry import access, connectors, discover_plugins, providers, routers, tools
from dayloom.schemas import (
    ActionUpdate,
    Approval,
    CalendarImport,
    ChatInput,
    MemoryInput,
    MemoryUpdate,
    Preferences,
    Proposal,
    TaskInput,
    TaskUpdate,
)


def local_day(session):
    return datetime.now(ZoneInfo(preferences_for(session).timezone)).date()


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    engine = build_engine(settings.database_url)
    discover_plugins()
    if settings.model_provider not in providers.classes:
        raise ValueError("Unknown model provider")

    @asynccontextmanager
    async def lifespan(_app):
        initialize_runtime(engine, settings)
        yield
        engine.dispose()

    app = FastAPI(
        title="Dayloom",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.engine = engine
    app.state.settings = settings
    app.state.access = access.build(settings.auth_backend, settings=settings, engine=engine)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Dayloom-Confirm", "X-Dayloom-CSRF"],
        allow_credentials=True,
    )

    @app.middleware("http")
    async def secure_api(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path.startswith("/api/") and request.url.path != "/api/health":
            if request.url.path not in PUBLIC_AUTH_PATHS:
                try:
                    principal = await app.state.access.authenticate(request)
                    request.state.principal = principal
                    request.state.workspace_id = principal.workspace_id
                except HTTPException as error:
                    return JSONResponse({"detail": error.detail}, status_code=error.status_code)
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins:
                return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
            length = request.headers.get("content-length", "0")
            if not length.isdigit() or int(length) > 600000:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/settings")
    def settings_view(session: Session = Depends(get_session)):
        heartbeat = session.get(Preference, "worker")
        last_seen = heartbeat.value.get("heartbeat", 0) if heartbeat else 0
        return {
            "preferences": preferences_for(session).model_dump(),
            "provider": model_status(session, settings),
            "worker_online": time.time() - last_seen < 30,
            "tools": [
                {
                    "name": name,
                    "label": implementation.label,
                    "automation_allowed": getattr(implementation, "automation_allowed", False),
                    "available": getattr(implementation, "available", lambda _settings: True)(
                        settings
                    ),
                }
                for name, implementation in tools.classes.items()
            ],
        }

    @app.put("/api/settings")
    def save_preferences(payload: Preferences, session: Session = Depends(get_session)):
        stored = session.get(Preference, "planning")
        if stored:
            stored.value = payload.model_dump()
        else:
            session.add(Preference(key="planning", value=payload.model_dump()))
        record(session, "preferences.updated", "planning")
        session.commit()
        return payload

    @app.get("/api/tasks")
    def tasks_list(session: Session = Depends(get_session)):
        return [
            as_dict(task) for task in session.scalars(select(Task).order_by(Task.created_at.desc()))
        ]

    @app.post("/api/tasks", status_code=201)
    def task_create(payload: TaskInput, session: Session = Depends(get_session)):
        task = Task(**payload.model_dump(mode="json"))
        session.add(task)
        session.flush()
        record(session, "task.created", task.id)
        session.commit()
        return as_dict(task)

    @app.put("/api/tasks/{task_id}")
    def task_update(task_id: str, payload: TaskUpdate, session: Session = Depends(get_session)):
        values = payload.model_dump(mode="json", exclude={"version"})
        changed = session.execute(
            update(Task)
            .where(Task.id == task_id, Task.version == payload.version)
            .values(**values, version=payload.version + 1, updated_at=timestamp())
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Task changed or was removed. Refresh before editing.")
        record(session, "task.updated", task_id, status=payload.status)
        session.commit()
        return as_dict(session.get(Task, task_id))

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def task_delete(task_id: str, session: Session = Depends(get_session)):
        if not session.execute(delete(Task).where(Task.id == task_id)).rowcount:
            raise HTTPException(404, "Task not found")
        record(session, "task.deleted", task_id)
        session.commit()

    @app.get("/api/memories")
    def memories_list(session: Session = Depends(get_session)):
        return [
            as_dict(memory)
            for memory in session.scalars(select(Memory).order_by(Memory.updated_at.desc()))
        ]

    @app.post("/api/memories", status_code=201)
    def memory_create(payload: MemoryInput, session: Session = Depends(get_session)):
        memory = Memory(**payload.model_dump(mode="json"))
        session.add(memory)
        session.flush()
        record(session, "memory.created", memory.id)
        session.commit()
        return as_dict(memory)

    @app.put("/api/memories/{memory_id}")
    def memory_update(
        memory_id: str, payload: MemoryUpdate, session: Session = Depends(get_session)
    ):
        values = payload.model_dump(mode="json", exclude={"version"})
        changed = session.execute(
            update(Memory)
            .where(Memory.id == memory_id, Memory.version == payload.version)
            .values(**values, version=payload.version + 1, updated_at=timestamp())
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Memory changed or was removed. Refresh before editing.")
        record(session, "memory.updated", memory_id)
        session.commit()
        return as_dict(session.get(Memory, memory_id))

    @app.delete("/api/memories/{memory_id}", status_code=204)
    def memory_delete(memory_id: str, session: Session = Depends(get_session)):
        if not session.execute(delete(Memory).where(Memory.id == memory_id)).rowcount:
            raise HTTPException(404, "Memory not found")
        record(session, "memory.deleted", memory_id)
        session.commit()

    @app.get("/api/plan")
    def plan(day: date | None = None, session: Session = Depends(get_session)):
        return build_plan(session, day or local_day(session))

    @app.get("/api/messages")
    def messages_list(session: Session = Depends(get_session)):
        messages = list(
            session.scalars(
                select(Message)
                .order_by(Message.created_at.desc(), Message.role.asc(), Message.id.desc())
                .limit(100)
            )
        )
        return [as_dict(message) for message in reversed(messages)]

    @app.post("/api/chat")
    async def chat(payload: ChatInput, session: Session = Depends(get_session)):
        if model_status(session, settings)["external"] and not payload.allow_external:
            raise HTTPException(
                400,
                "Approve sharing this message, recent conversation, task titles and active memories with the configured model provider.",
            )
        configured = resolve_model(session, settings)
        provider = providers.build(configured.model_provider, settings=configured)
        today = local_day(session)
        context = {
            "today": today.isoformat(),
            "timezone": preferences_for(session).timezone,
            "tasks": [
                {"title": task.title, "status": task.status, "due_date": task.due_date}
                for task in session.scalars(
                    select(Task)
                    .where(Task.status != "done")
                    .order_by(Task.updated_at.desc())
                    .limit(20)
                )
            ],
            "memories": [
                {"content": memory.content, "category": memory.category}
                for memory in session.scalars(
                    select(Memory)
                    .where(or_(Memory.expires_on.is_(None), Memory.expires_on >= today.isoformat()))
                    .order_by(Memory.updated_at.desc())
                    .limit(25)
                )
            ],
            "conversation": [
                {"role": message.role, "content": message.content[:2000]}
                for message in reversed(
                    list(
                        session.scalars(
                            select(Message)
                            .order_by(
                                Message.created_at.desc(), Message.role.asc(), Message.id.desc()
                            )
                            .limit(8)
                        )
                    )
                )
            ],
            "connections": [
                {
                    "id": connection.id,
                    "kind": connection.kind,
                    "version": connection.version,
                    "sender": connection.configuration.get("username"),
                }
                for connection in session.scalars(select(Integration))
            ],
        }
        reserve_model_request(session)
        try:
            reply = await provider.reply(payload.content, context)
            for proposal in reply.proposals:
                validate_proposal(proposal)
        except Exception as error:
            raise HTTPException(
                502,
                "The model is unavailable or returned invalid action data. Nothing was changed.",
            ) from error
        user_message = Message(role="user", content=payload.content)
        response_message = Message(
            role="assistant", content=reply.message, provider=configured.model_provider
        )
        session.add_all([user_message, response_message])
        actions = [add_proposal(session, proposal) for proposal in reply.proposals]
        session.commit()
        return {
            "message": as_dict(response_message),
            "actions": [action_view(action) for action in actions],
        }

    @app.get("/api/actions")
    def actions_list(session: Session = Depends(get_session)):
        return [
            action_view(action)
            for action in session.scalars(
                select(Action).order_by(Action.created_at.desc()).limit(200)
            )
        ]

    @app.post("/api/actions", status_code=201)
    def action_create(payload: Proposal, session: Session = Depends(get_session)):
        action = add_proposal(session, payload)
        session.commit()
        return action_view(action)

    @app.patch("/api/actions/{action_id}")
    def action_edit(action_id: str, payload: ActionUpdate, session: Session = Depends(get_session)):
        action = get_action(session, action_id)
        if action.status not in {"pending", "queued", "failed"} or action.digest != payload.digest:
            raise HTTPException(409, "This action changed or can no longer be edited")
        validated = validate_proposal(Proposal(tool=action.tool, payload=payload.payload))
        action.payload = validated
        action.digest = action_digest(action.tool, validated)
        action.approved_digest = None
        action.status = "pending"
        action.result = None
        action.error = None
        action.attempts = 0
        action.effect_started_at = None
        action.updated_at = timestamp()
        record(session, "action.revised", action.id)
        session.commit()
        return action_view(action)

    @app.post("/api/actions/{action_id}/approve")
    def action_approve(action_id: str, payload: Approval, session: Session = Depends(get_session)):
        action = get_action(session, action_id)
        try:
            require_agent_authority(action, session)
        except AuthorityRevoked as error:
            raise HTTPException(
                409, "Resume the Agent run before approving its actions."
            ) from error
        if action.status != "pending" or action.digest != payload.digest:
            raise HTTPException(409, "This action changed or has already been approved")
        action.approved_digest = action.digest
        action.status = "queued"
        action.updated_at = timestamp()
        record(session, "action.approved", action.id, digest=action.digest)
        session.commit()
        return action_view(action)

    @app.post("/api/actions/{action_id}/cancel")
    def action_cancel(action_id: str, session: Session = Depends(get_session)):
        action = get_action(session, action_id)
        if action.status not in {"pending", "queued", "failed"}:
            raise HTTPException(409, "Only unstarted actions can be cancelled")
        action.status = "cancelled"
        action.approved_digest = None
        action.updated_at = timestamp()
        record(session, "action.cancelled", action.id)
        session.commit()
        return action_view(action)

    @app.post("/api/actions/{action_id}/retry")
    def action_retry(action_id: str, session: Session = Depends(get_session)):
        action = get_action(session, action_id)
        if action.status != "failed":
            raise HTTPException(409, "Only failed actions can be retried")
        action.status = "pending"
        action.approved_digest = None
        action.attempts = 0
        action.effect_started_at = None
        action.error = None
        action.updated_at = timestamp()
        record(session, "action.retry_requested", action.id)
        session.commit()
        return action_view(action)

    @app.get("/api/audit")
    def audit_list(session: Session = Depends(get_session)):
        return [
            as_dict(entry)
            for entry in session.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(100))
        ]

    @app.get("/api/calendar")
    def calendar_list(session: Session = Depends(get_session)):
        return [
            as_dict(event)
            for event in session.scalars(select(CalendarEvent).order_by(CalendarEvent.start))
        ]

    @app.post("/api/calendar/import")
    def calendar_import(payload: CalendarImport, session: Session = Depends(get_session)):
        try:
            events = connectors.build("IcsCalendar").read(
                payload.content,
                payload.source,
                preferences_for(session).timezone,
                local_day(session),
            )
        except Exception as error:
            raise HTTPException(
                422, "Invalid or oversized calendar. The previous calendar is unchanged."
            ) from error
        session.execute(delete(CalendarEvent).where(CalendarEvent.source == payload.source))
        session.add_all([CalendarEvent(**event) for event in events])
        record(session, "calendar.imported", payload.source, count=len(events))
        session.commit()
        return {"imported": len(events), "source": payload.source}

    @app.delete("/api/calendar", status_code=204)
    def calendar_clear(session: Session = Depends(get_session)):
        session.execute(delete(CalendarEvent))
        record(session, "calendar.cleared", "calendar")
        session.commit()

    @app.get("/api/data")
    def export_data(session: Session = Depends(get_session)):
        return {
            "version": 1,
            "exported_at": timestamp(),
            "tasks": [as_dict(item) for item in session.scalars(select(Task))],
            "memories": [as_dict(item) for item in session.scalars(select(Memory))],
            "messages": [as_dict(item) for item in session.scalars(select(Message))],
            "actions": [action_view(item) for item in session.scalars(select(Action))],
            "calendar": [as_dict(item) for item in session.scalars(select(CalendarEvent))],
            "audit": [as_dict(item) for item in session.scalars(select(Audit))],
            "preferences": preferences_for(session).model_dump(),
            "automations": [as_dict(rule) for rule in session.scalars(select(AutomationRule))],
            "agent_runs": [
                {
                    key: value
                    for key, value in as_dict(run).items()
                    if key not in {"claim_token", "lease_until"}
                }
                for run in session.scalars(select(AgentRun))
            ],
            "agent_steps": [as_dict(step) for step in session.scalars(select(AgentStep))],
            "artifacts": [as_dict(artifact) for artifact in session.scalars(select(Artifact))],
        }

    @app.delete("/api/data", status_code=204)
    def erase_data(request: Request, session: Session = Depends(get_session)):
        if request.headers.get("x-dayloom-confirm") != "DELETE MY DATA":
            raise HTTPException(400, "Explicit deletion confirmation is required")
        if session.scalar(
            select(func.count())
            .select_from(Action)
            .where(Action.status.in_(["running", "outcome_unknown"]))
        ):
            raise HTTPException(
                409, "Finish or reconcile running and uncertain actions before deleting data"
            )
        for model in [
            AgentStep,
            Artifact,
            Action,
            AgentRun,
            AutomationRule,
            Message,
            Memory,
            Task,
            CalendarEvent,
            Audit,
            Preference,
        ]:
            session.execute(delete(model))
        session.commit()

    @app.post("/api/demo", status_code=201)
    def seed_demo(session: Session = Depends(get_session)):
        if any(
            session.scalar(select(func.count()).select_from(model))
            for model in [Task, Memory, Message, Action, CalendarEvent]
        ):
            raise HTTPException(409, "Sample data can only be loaded into an empty workspace")
        today = local_day(session)
        session.add_all(
            [
                Task(
                    title="Shape the first version of Dayloom",
                    notes="Write down one complete workflow and its acceptance criteria.",
                    priority="high",
                    minutes=45,
                    due_date=today.isoformat(),
                    source="Sample data",
                ),
                Task(
                    title="Read the research notes",
                    notes="Pick three observations worth keeping.",
                    minutes=30,
                    source="Sample data",
                ),
                Task(
                    title="Make room for a walk", priority="low", minutes=20, source="Sample data"
                ),
                Task(
                    title="Review next week's priorities",
                    minutes=25,
                    due_date=(today + timedelta(days=3)).isoformat(),
                    source="Sample data",
                ),
                Memory(
                    content="I prefer a small number of focused tasks over a packed schedule.",
                    category="preference",
                    source="Sample data",
                ),
                Memory(
                    content="Build a personal assistant that keeps people in control.",
                    category="goal",
                    source="Sample data",
                ),
            ]
        )
        record(session, "demo.loaded", "workspace")
        session.commit()
        return {"loaded": True}

    @app.get("/api/schema")
    def schema():
        return app.openapi()

    for name in routers.classes:
        routers.build(name, settings=settings, engine=engine).install(app)

    @app.get("/{asset_path:path}")
    def frontend(asset_path: str):
        if asset_path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        root = settings.static_dir.resolve()
        asset = (root / asset_path).resolve()
        if not asset.is_relative_to(root):
            raise HTTPException(404)
        if asset.is_file():
            return FileResponse(asset)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(404, "Build the web client or start the development server")

    return app
