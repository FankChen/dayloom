import asyncio
import json
from uuid import UUID

from pydantic import Field, field_validator
from sqlalchemy import select

from dayloom.db import Action, Integration
from dayloom.devices import validate_device_endpoint, validate_tool_arguments
from dayloom.executors import KnownFailure, OutcomeUnknown
from dayloom.integrations import reserve_integration_request
from dayloom.policy import require_action_authority
from dayloom.registry import connectors, tools
from dayloom.schemas import StrictModel
from dayloom.secrets import SecretVault
from dayloom.workspaces import WorkspaceSession


def authorized_connection(session, settings, connection_id, version=None):
    connection = session.get(Integration, str(connection_id))
    if (
        not connection
        or connection.kind != "mcp"
        or (version is not None and connection.version != version)
    ):
        raise KnownFailure("Device connection was removed or changed. Review its permissions.")
    try:
        validate_device_endpoint(connection.configuration["endpoint"], settings)
    except ValueError as error:
        raise KnownFailure("This device service is no longer enabled.") from error
    return connection


class DeviceToolsInput(StrictModel):
    connection_id: UUID
    tool_name: str | None = Field(default=None, max_length=80)


class DeviceCallInput(StrictModel):
    connection_id: UUID
    connection_version: int = Field(ge=1)
    tool_name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    arguments: dict = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def bounded_arguments(cls, values):
        if len(json.dumps(values, allow_nan=False)) > 16000:
            raise ValueError("Device arguments exceed the size limit")
        return values


class DeviceCapability:
    connection_kind = "mcp"

    @staticmethod
    def available(settings):
        return bool(settings.mcp_allowed_servers)

    @staticmethod
    def ready(session, settings):
        return any(
            connection.configuration.get("tools")
            for connection in session.scalars(select(Integration).where(Integration.kind == "mcp"))
        )


@tools.register
class ListDeviceTools(DeviceCapability):
    label = "Inspect authorized device tools"
    description = "List the selected device's authorized tool names, or supply tool_name to inspect its exact input schema. This reads the saved discovery snapshot without executing device commands."
    input_model = DeviceToolsInput
    read_only = True

    def __init__(self, session, settings):
        self.session = session
        self.settings = settings

    def execute(self, payload):
        connection = authorized_connection(self.session, self.settings, payload.connection_id)
        names = connection.configuration.get("tools", [])
        if payload.tool_name and payload.tool_name not in names:
            raise KnownFailure("This device tool is not authorized.")
        catalog = connection.configuration.get("schemas", {})
        descriptions = [
            catalog[name]
            if payload.tool_name
            else {"name": name, "description": catalog[name]["description"]}
            for name in names
            if name in catalog and (not payload.tool_name or name == payload.tool_name)
        ]
        return {
            "kind": "device_tools",
            "title": connection.label,
            "connection_id": connection.id,
            "connection_version": connection.version,
            "tools": descriptions,
        }


@tools.register
class CallDeviceTool(DeviceCapability):
    label = "Run an authorized device tool"
    description = "Execute one exact, user-approved call on the connected MCP device service. Inspect its schema with ListDeviceTools first. Every device call requires separate approval, even when the remote service labels it read-only. A service result is not proof of purchase, payment or installation."
    input_model = DeviceCallInput
    executor = "ExternalExecution"

    def __init__(self, engine, settings, workspace_id, action_id, claim):
        self.engine = engine
        self.settings = settings
        self.workspace_id = workspace_id
        self.action_id = action_id
        self.claim = claim

    def execute(self, payload):
        with WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session:
            connection = authorized_connection(
                session, self.settings, payload.connection_id, payload.connection_version
            )
            if payload.tool_name not in connection.configuration.get("tools", []):
                raise KnownFailure("This device tool is not authorized.")
            specification = connection.configuration.get("schemas", {}).get(payload.tool_name)
            if not specification:
                raise KnownFailure("Discover and authorize this device tool again.")
            schema = specification["input_schema"]
            try:
                validate_tool_arguments(schema, payload.arguments)
            except Exception as error:
                raise KnownFailure(
                    "Device tool arguments do not match its approved schema."
                ) from error
            endpoint, label = connection.configuration["endpoint"], connection.label
            credentials = SecretVault(self.settings).open(
                connection.secret, f"mcp:{self.workspace_id}:{connection.id}:{endpoint}"
            )
            reserve_integration_request(session, "mcp_call", self.settings.device_daily_limit)

        def authorize():
            with WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session:
                authorized_connection(
                    session, self.settings, payload.connection_id, payload.connection_version
                )
                action = session.get(Action, self.action_id)
                if not action or action.claim_token != self.claim or action.status != "running":
                    raise KnownFailure("Device action was cancelled before execution.")
                require_action_authority(action, session)

        state = {"attempted": False}
        try:
            result = asyncio.run(
                connectors.build("McpDevice").invoke(
                    endpoint,
                    credentials["token"],
                    payload.tool_name,
                    payload.arguments,
                    schema,
                    self.action_id,
                    authorize,
                    state,
                )
            )
        except Exception as error:
            if state["attempted"]:
                raise OutcomeUnknown() from error
            raise KnownFailure(
                "Could not start the authorized device tool. Check the connection and permissions."
            ) from error
        if result["blocked"]:
            raise KnownFailure(
                "Device tool definitions changed. Discover and authorize them again."
            )
        if result["is_error"]:
            raise OutcomeUnknown()
        return {
            "kind": "device",
            "title": label,
            "tool": payload.tool_name,
            "text": result["text"],
            "data": result["data"],
            "execution_location": "connected MCP service",
        }
