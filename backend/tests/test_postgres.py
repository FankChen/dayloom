import os
from uuid import uuid4

import pytest
from dayloom.db import Task, Workspace, build_engine, identifier
from dayloom.migrations import migrate, verify_production_database
from dayloom.workspaces import WorkspaceSession
from psycopg import sql
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.mark.skipif(
    not os.environ.get("DAYLOOM_TEST_POSTGRES_URL"),
    reason="PostgreSQL integration service is not configured",
)
def test_postgres_runtime_role_and_rls():
    admin = build_engine(os.environ["DAYLOOM_TEST_POSTGRES_URL"])
    migrate(admin)
    role_name = f"dayloom_test_{uuid4().hex}"
    password = uuid4().hex
    raw = admin.raw_connection()
    try:
        with raw.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS").format(
                    sql.Identifier(role_name), sql.Literal(password)
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role_name))
            )
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}"
                ).format(sql.Identifier(role_name))
            )
        raw.commit()
    finally:
        raw.close()
    runtime_url = make_url(os.environ["DAYLOOM_TEST_POSTGRES_URL"]).set(
        username=role_name, password=password
    )
    runtime = build_engine(runtime_url.render_as_string(hide_password=False))
    first, second = identifier(), identifier()
    try:
        verify_production_database(runtime)
        with pytest.raises(ValueError, match="must not bypass"):
            verify_production_database(admin)
        with Session(admin) as session:
            session.add_all([Workspace(id=first), Workspace(id=second)])
            session.commit()
        with WorkspaceSession(runtime, workspace_id=first) as session:
            session.add(Task(title="First private task"))
            session.commit()
        with WorkspaceSession(runtime, workspace_id=second) as session:
            assert session.scalars(select(Task)).all() == []
            session.add(Task(title="Second private task"))
            session.commit()
        with runtime.begin() as connection:
            assert connection.execute(text("SELECT count(*) FROM tasks")).scalar() == 0
            connection.execute(
                text("SELECT set_config('dayloom.workspace_id', :workspace, true)"),
                {"workspace": first},
            )
            assert connection.execute(text("SELECT title FROM tasks")).scalars().all() == [
                "First private task"
            ]
            assert (
                connection.execute(
                    text("DELETE FROM tasks WHERE workspace_id = :workspace"), {"workspace": second}
                ).rowcount
                == 0
            )
    finally:
        runtime.dispose()
        raw = admin.raw_connection()
        try:
            with raw.cursor() as cursor:
                cursor.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role_name)))
                cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role_name)))
            raw.commit()
        finally:
            raw.close()
            admin.dispose()
