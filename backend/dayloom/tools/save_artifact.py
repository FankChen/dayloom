from urllib.parse import urlsplit

from pydantic import Field, field_validator

from dayloom.db import Action, Artifact
from dayloom.registry import tools
from dayloom.schemas import StrictModel


class ArtifactInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50000)
    sources: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("sources")
    @classmethod
    def https_sources(cls, values):
        for value in values:
            parsed = urlsplit(value)
            if (
                len(value) > 2000
                or parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Source links must be HTTPS URLs without credentials")
        return values


@tools.register
class SaveArtifact:
    label = "Save a work artifact"
    description = "Save a Markdown research note or other text result in the workspace with source links. This creates a downloadable artifact, not a task, and never installs or executes software."
    input_model = ArtifactInput

    def __init__(self, session, action_id):
        self.session = session
        self.action_id = action_id

    def execute(self, payload):
        action = self.session.get(Action, self.action_id)
        artifact = Artifact(**payload.model_dump(), agent_run_id=action.agent_run_id)
        self.session.add(artifact)
        self.session.flush()
        return {
            "kind": "artifact",
            "id": artifact.id,
            "title": artifact.title,
            "sources": artifact.sources,
            "download_url": f"/api/artifacts/{artifact.id}/download",
        }
