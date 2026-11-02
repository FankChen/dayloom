from uuid import UUID

from sqlalchemy import event, inspect, text
from sqlalchemy.orm import Session, with_loader_criteria

from dayloom.db import LEGACY_WORKSPACE_ID, WorkspaceOwned


class WorkspaceSession(Session):
    def __init__(self, *args, workspace_id=LEGACY_WORKSPACE_ID, **kwargs):
        super().__init__(*args, **kwargs)
        self._workspace_id = str(UUID(workspace_id))

    @property
    def workspace_id(self):
        return self._workspace_id

    def get(self, entity, ident, **kwargs):
        keys = [column.key for column in inspect(entity).primary_key]
        if isinstance(ident, str) and "workspace_id" in keys and len(keys) == 2:
            key = next(name for name in keys if name != "workspace_id")
            ident = {key: ident, "workspace_id": self.workspace_id}
        return super().get(entity, ident, **kwargs)


@event.listens_for(WorkspaceSession, "after_begin")
def set_database_workspace(session, _transaction, connection):
    if connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT set_config('dayloom.workspace_id', :workspace_id, true)"),
            {"workspace_id": session.workspace_id},
        )


@event.listens_for(WorkspaceSession, "do_orm_execute")
def scope_statements(state):
    if not state.is_orm_statement or state.is_insert:
        raise ValueError("Use scoped ORM operations for workspace data")
    if state.is_update and any(
        getattr(key, "key", str(key)) == "workspace_id" for key in state.statement._values
    ):
        raise ValueError("Workspace ownership cannot be changed")
    workspace_id = state.session.workspace_id
    state.statement = state.statement.options(
        with_loader_criteria(
            WorkspaceOwned,
            lambda entity: entity.workspace_id == workspace_id,
            include_aliases=True,
        )
    )


@event.listens_for(WorkspaceSession, "before_flush")
def scope_changes(session, _context, _instances):
    for entity in session.new | session.dirty | session.deleted:
        if not isinstance(entity, WorkspaceOwned):
            continue
        state = inspect(entity)
        if entity in session.new and entity.workspace_id is None:
            entity.workspace_id = session.workspace_id
        if entity.workspace_id != session.workspace_id:
            raise ValueError("Cross-workspace writes are forbidden")
        if state.persistent and state.attrs.workspace_id.history.has_changes():
            raise ValueError("Workspace ownership cannot be changed")
