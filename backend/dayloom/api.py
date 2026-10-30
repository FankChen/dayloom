import hmac
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from dayloom.config import Settings
from dayloom.db import (
    Action,
    Audit,
    Base,
    CalendarEvent,
    Memory,
    Message,
    Preference,
    Task,
    as_dict,
    build_engine,
    record,
    timestamp,
)
from dayloom.planning import build_plan, preferences_for
from dayloom.policy import action_digest
from dayloom.registry import connectors, discover_plugins, providers, tools
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


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


def action_view(action):
    return {
        key: value
        for key, value in as_dict(action).items()
        if key not in {"approved_digest", "claim_token", "lease_until"}
    }


def get_action(session, action_id):
    action = session.scalar(select(Action).where(Action.id == action_id).with_for_update())
    if not action:
        raise HTTPException(404, "Action not found")
    return action


def validate_proposal(proposal: Proposal):
    implementation = tools.classes.get(proposal.tool)
    if implementation is None:
        raise HTTPException(422, "Unknown tool")
    try:
        return implementation.input_model.model_validate(proposal.payload).model_dump(mode="json")
    except ValidationError as error:
        raise HTTPException(422, "Invalid action payload") from error


def add_proposal(session, proposal: Proposal):
    payload = validate_proposal(proposal)
    action = Action(
        tool=proposal.tool, payload=payload, digest=action_digest(proposal.tool, payload)
    )
    session.add(action)
    session.flush()
    record(session, "action.proposed", action.id, tool=action.tool)
    return action


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
        Base.metadata.create_all(engine)
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Dayloom-Confirm"],
    )

    @app.middleware("http")
    async def secure_api(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path.startswith("/api/") and request.url.path != "/api/health":
            token = settings.access_token.get_secret_value()
            if token:
                supplied = request.headers.get("authorization", "")
                if not hmac.compare_digest(supplied, f"Bearer {token}"):
                    return JSONResponse({"detail": "An access token is required"}, status_code=401)
            elif not request.client or request.client.host not in {
                "127.0.0.1",
                "::1",
                "testclient",
            }:
                return JSONResponse(
                    {"detail": "Configure an access token for remote access"}, status_code=401
                )
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
        provider = providers.classes[settings.model_provider]
        return {
            "preferences": preferences_for(session).model_dump(),
            "provider": {
                "name": settings.model_provider,
                "label": provider.label,
                "external": provider.external,
                "model": settings.model_name if provider.external else None,
                "configured": not provider.external
                or bool(settings.model_api_key.get_secret_value()),
            },
            "worker_online": time.time() - last_seen < 30,
            "tools": [
                {"name": name, "label": implementation.label}
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
            session.scalars(select(Message).order_by(Message.created_at.desc()).limit(100))
        )
        return [as_dict(message) for message in reversed(messages)]

    @app.post("/api/chat")
    async def chat(payload: ChatInput, session: Session = Depends(get_session)):
        provider = providers.build(settings.model_provider, settings=settings)
        if provider.external and not payload.allow_external:
            raise HTTPException(
                400,
                "Approve sharing this message, recent conversation, task titles and active memories with the configured model provider.",
            )
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
                            select(Message).order_by(Message.created_at.desc()).limit(8)
                        )
                    )
                )
            ],
        }
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
            role="assistant", content=reply.message, provider=settings.model_provider
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
        action.updated_at = timestamp()
        record(session, "action.revised", action.id)
        session.commit()
        return action_view(action)

    @app.post("/api/actions/{action_id}/approve")
    def action_approve(action_id: str, payload: Approval, session: Session = Depends(get_session)):
        action = get_action(session, action_id)
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
        }

    @app.delete("/api/data", status_code=204)
    def erase_data(request: Request, session: Session = Depends(get_session)):
        if request.headers.get("x-dayloom-confirm") != "DELETE MY DATA":
            raise HTTPException(400, "Explicit deletion confirmation is required")
        if session.scalar(
            select(func.count()).select_from(Action).where(Action.status == "running")
        ):
            raise HTTPException(409, "Wait for running actions to finish before deleting data")
        for model in [Action, Message, Memory, Task, CalendarEvent, Audit, Preference]:
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
