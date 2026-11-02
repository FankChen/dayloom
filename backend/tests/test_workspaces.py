import pytest
from dayloom.db import (
    LEGACY_WORKSPACE_ID,
    Action,
    Audit,
    CalendarEvent,
    Memory,
    Message,
    Preference,
    Task,
    Workspace,
    build_engine,
    identifier,
)
from dayloom.migrations import migrate
from dayloom.policy import action_digest
from dayloom.worker import run_once
from dayloom.workspaces import WorkspaceSession
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, aliased


def test_workspace_queries_and_bulk_writes_are_isolated(engine):
    first_workspace, second_workspace = identifier(), identifier()
    with Session(engine) as session:
        session.add_all([Workspace(id=first_workspace), Workspace(id=second_workspace)])
        session.commit()
    with WorkspaceSession(engine, workspace_id=first_workspace) as session:
        first_task = Task(title="First account task")
        session.add(first_task)
        session.commit()
        first_id = first_task.id
    with WorkspaceSession(engine, workspace_id=second_workspace) as session:
        second_task = Task(title="Second account task")
        session.add(second_task)
        session.commit()
        assert second_task.workspace_id == second_workspace
        assert session.get(Task, first_id) is None
        task_alias = aliased(Task)
        assert session.scalars(select(task_alias.title)).all() == ["Second account task"]
        assert session.execute(update(Task).values(title="Scoped edit")).rowcount == 1
        assert session.execute(delete(Task).where(Task.id == first_id)).rowcount == 0
        session.commit()
    with WorkspaceSession(engine, workspace_id=first_workspace) as session:
        assert session.get(Task, first_id).title == "First account task"


def test_workspace_rejects_foreign_inserts_and_ownership_changes(engine):
    workspace_id = identifier()
    with Session(engine) as session:
        session.add(Workspace(id=workspace_id))
        session.commit()
    with WorkspaceSession(engine, workspace_id=workspace_id) as session:
        session.add(Task(title="Wrong owner", workspace_id=identifier()))
        with pytest.raises(ValueError, match="Cross-workspace"):
            session.flush()
        session.rollback()
        task = Task(title="Owned task")
        session.add(task)
        session.commit()
        task.workspace_id = identifier()
        with pytest.raises(ValueError, match="Cross-workspace"):
            session.flush()
        session.rollback()
        with pytest.raises(ValueError, match="ownership"):
            session.execute(update(Task).values(workspace_id=identifier()))


def test_all_workspace_records_and_worker_remain_scoped(engine, settings):
    first_workspace, second_workspace = identifier(), identifier()
    with Session(engine) as session:
        session.add_all([Workspace(id=first_workspace), Workspace(id=second_workspace)])
        session.commit()
    payload = {"title": "Scoped worker task"}
    for workspace_id in [first_workspace, second_workspace]:
        with WorkspaceSession(engine, workspace_id=workspace_id) as session:
            session.add_all(
                [
                    Preference(key="planning", value={"daily_minutes": 90}),
                    CalendarEvent(
                        id="same-external-id",
                        title="Event",
                        start="2026-10-30T09:00:00+00:00",
                        end="2026-10-30T10:00:00+00:00",
                        source="test",
                    ),
                    Memory(content="Private memory"),
                    Message(role="user", content="Private conversation"),
                    Audit(event="test", entity_id="test"),
                    Action(
                        tool="CreateTask",
                        payload=payload,
                        digest=action_digest("CreateTask", payload),
                        approved_digest=action_digest("CreateTask", payload),
                        status="queued",
                    ),
                ]
            )
            session.commit()
            for model in [Preference, CalendarEvent, Memory, Message, Audit, Action]:
                assert len(session.scalars(select(model)).all()) == 1
    assert run_once(engine, settings, first_workspace)
    with WorkspaceSession(engine, workspace_id=second_workspace) as session:
        assert session.scalars(select(Task)).all() == []
        assert session.scalar(select(Action.status)) == "queued"
        for model in [Action, Message, Memory, Task, CalendarEvent, Audit, Preference]:
            session.execute(delete(model))
        session.commit()
    with WorkspaceSession(engine, workspace_id=first_workspace) as session:
        assert session.scalar(select(Task.title)) == "Scoped worker task"
        assert session.scalar(select(Action.status)) == "succeeded"


def test_legacy_database_upgrade_preserves_data(tmp_path):
    from sqlalchemy import inspect, text

    engine = build_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE tasks (id VARCHAR(36) PRIMARY KEY, title VARCHAR(200) NOT NULL)")
        )
        connection.execute(text("INSERT INTO tasks VALUES ('existing', 'Keep this task')"))
        connection.execute(
            text("CREATE TABLE preferences (key VARCHAR(80) PRIMARY KEY, value JSON NOT NULL)")
        )
        connection.execute(text("INSERT INTO preferences VALUES ('planning', '{}')"))
    migrate(engine)
    migrate(engine)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT workspace_id FROM tasks")).scalar()
            == LEGACY_WORKSPACE_ID
        )
        assert connection.execute(text("SELECT title FROM tasks")).scalar() == "Keep this task"
        assert set(inspect(connection).get_pk_constraint("preferences")["constrained_columns"]) == {
            "key",
            "workspace_id",
        }
    engine.dispose()
