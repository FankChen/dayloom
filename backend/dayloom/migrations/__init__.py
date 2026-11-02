from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from dayloom.db import Base, WorkspaceOwned


def owned_tables():
    return sorted(
        mapper.local_table.name
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, WorkspaceOwned)
    )


def install_row_security(connection):
    if connection.dialect.name != "postgresql":
        return
    for name in owned_tables():
        table = connection.dialect.identifier_preparer.quote(name)
        connection.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        connection.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        connection.execute(text(f"DROP POLICY IF EXISTS dayloom_workspace ON {table}"))
        connection.execute(
            text(
                f"CREATE POLICY dayloom_workspace ON {table} USING (workspace_id = current_setting('dayloom.workspace_id', true)) WITH CHECK (workspace_id = current_setting('dayloom.workspace_id', true))"
            )
        )


def verify_production_database(engine):
    if engine.dialect.name != "postgresql":
        raise ValueError("Production requires PostgreSQL")
    with engine.connect() as connection:
        role = connection.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
        if role.rolsuper or role.rolbypassrls:
            raise ValueError("Application database role must not bypass row-level security")
        for name in owned_tables():
            table = connection.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity, pg_get_userbyid(relowner) = current_user AS is_owner FROM pg_class WHERE oid = to_regclass(:name)"
                ),
                {"name": name},
            ).one_or_none()
            if (
                not table
                or not table.relrowsecurity
                or not table.relforcerowsecurity
                or table.is_owner
            ):
                raise ValueError(
                    "Run migrations with a separate owner role and enable workspace RLS"
                )
        if (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            != ScriptDirectory(str(Path(__file__).parent)).get_current_head()
        ):
            raise ValueError("Database migrations must be applied before production startup")


def migrate(engine):
    configuration = Config()
    configuration.set_main_option("script_location", str(Path(__file__).parent))
    with engine.begin() as connection:
        configuration.attributes["connection"] = connection
        tables = set(inspect(connection).get_table_names())
        if not tables or ("workspaces" in tables and "alembic_version" not in tables):
            if tables:
                for table in Base.metadata.sorted_tables:
                    if table.name in tables and not set(table.columns.keys()).issubset(
                        {column["name"] for column in inspect(connection).get_columns(table.name)}
                    ):
                        raise ValueError(
                            "Unversioned partial schema requires an explicit migration"
                        )
            Base.metadata.create_all(connection)
            command.stamp(configuration, "head")
        else:
            command.upgrade(configuration, "head")
        install_row_security(connection)


def initialize_runtime(engine, settings):
    if settings.production:
        verify_production_database(engine)
    else:
        migrate(engine)
