from fastapi import HTTPException, Request

from dayloom.workspaces import WorkspaceSession


def get_session(request: Request):
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        raise HTTPException(401, "Workspace authentication is required")
    with WorkspaceSession(request.app.state.engine, workspace_id=workspace_id) as session:
        yield session
