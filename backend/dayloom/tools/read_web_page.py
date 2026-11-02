import httpx
from pydantic import BaseModel, ConfigDict, HttpUrl

from dayloom.browser_policy import allowed_page
from dayloom.executors import KnownFailure
from dayloom.integrations import reserve_integration_request
from dayloom.registry import tools
from dayloom.workspaces import WorkspaceSession


class WebPageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: HttpUrl


@tools.register
class ReadWebPage:
    label = "Read a public webpage"
    description = "Read a public HTTPS page on an administrator-approved origin using an isolated browser. No login, checkout, arbitrary JavaScript or form submission."
    input_model = WebPageInput
    executor = "ExternalExecution"

    def __init__(self, engine, settings, workspace_id, action_id):
        self.engine = engine
        self.settings = settings
        self.workspace_id = workspace_id
        self.action_id = action_id

    @staticmethod
    def available(settings):
        return bool(
            settings.browser_runner_url
            and settings.browser_shared_token.get_secret_value()
            and settings.browser_allowed_origins
        )

    def execute(self, payload):
        if not self.available(self.settings) or not allowed_page(
            payload.url, self.settings.browser_allowed_origins
        ):
            raise KnownFailure("Browser execution is unavailable for this origin")
        with WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session:
            reserve_integration_request(session, "browser", 20)
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            response = client.post(
                f"{self.settings.browser_runner_url.rstrip('/')}/read",
                headers={
                    "Authorization": f"Bearer {self.settings.browser_shared_token.get_secret_value()}"
                },
                json={
                    "run_id": self.action_id,
                    "workspace_id": self.workspace_id,
                    "url": str(payload.url),
                },
            )
            response.raise_for_status()
            result = response.json()
        if not allowed_page(result["url"], self.settings.browser_allowed_origins):
            raise KnownFailure("Browser result left the approved origin")
        return {
            "kind": "webpage",
            "title": str(result["title"])[:200],
            "url": result["url"],
            "text": str(result["text"])[:16000],
        }
