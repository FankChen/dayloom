from dayloom.db import Artifact, as_dict
from dayloom.dependencies import get_session
from dayloom.registry import routers
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select


@routers.register
class ArtifactRoutes:
    def install(self, app):
        router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])

        def get_artifact(session, artifact_id):
            artifact = session.get(Artifact, artifact_id)
            if not artifact:
                raise HTTPException(404, "Artifact not found")
            return artifact

        @router.get("")
        def artifacts(session=Depends(get_session)):
            return [
                {key: value for key, value in as_dict(artifact).items() if key != "content"}
                for artifact in session.scalars(
                    select(Artifact).order_by(Artifact.created_at.desc()).limit(100)
                )
            ]

        @router.get("/{artifact_id}")
        def artifact(artifact_id: str, session=Depends(get_session)):
            return as_dict(get_artifact(session, artifact_id))

        @router.get("/{artifact_id}/download")
        def download(artifact_id: str, session=Depends(get_session)):
            artifact = get_artifact(session, artifact_id)
            return Response(
                content=artifact.content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="{artifact.id}.md"',
                    "X-Content-Type-Options": "nosniff",
                },
            )

        app.include_router(router)
