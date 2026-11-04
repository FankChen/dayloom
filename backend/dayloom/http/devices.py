from dayloom.db import Integration, identifier, record
from dayloom.dependencies import get_session
from dayloom.devices import DeviceDiscoveryInput, DeviceInput, device_view, validate_device_endpoint
from dayloom.executors import KnownFailure
from dayloom.integrations import reserve_integration_request
from dayloom.registry import connectors, routers
from dayloom.secrets import SecretVault
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update


@routers.register
class DeviceRoutes:
    def __init__(self, settings):
        self.settings = settings

    def install(self, app):
        router = APIRouter(prefix="/api/devices", tags=["devices"])

        def connection_for(session, connection_id):
            connection = session.get(Integration, connection_id)
            if not connection or connection.kind != "mcp":
                raise HTTPException(404, "Device connection not found")
            return connection

        def endpoint_for(value):
            try:
                return validate_device_endpoint(value, self.settings)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

        @router.get("")
        def connections(session=Depends(get_session)):
            return {
                "connections": [
                    device_view(connection)
                    for connection in session.scalars(
                        select(Integration).where(Integration.kind == "mcp")
                    )
                ],
                "allowed_servers": self.settings.mcp_allowed_servers,
            }

        @router.post("", status_code=201)
        def connect(payload: DeviceInput, session=Depends(get_session)):
            endpoint = endpoint_for(payload.endpoint)
            if payload.tools:
                raise HTTPException(422, "Discover device tools before authorizing them.")
            if (
                session.scalar(
                    select(func.count()).select_from(Integration).where(Integration.kind == "mcp")
                )
                >= 10
            ):
                raise HTTPException(422, "This workspace already has ten device connections.")
            connection_id = identifier()
            token = payload.token.get_secret_value() if payload.token else ""
            connection = Integration(
                id=connection_id,
                kind="mcp",
                label=payload.label,
                configuration={"endpoint": endpoint, "tools": [], "schemas": {}},
                secret=SecretVault(self.settings).seal(
                    {"token": token}, f"mcp:{session.workspace_id}:{connection_id}:{endpoint}"
                ),
            )
            session.add(connection)
            record(session, "device.connected", connection_id)
            session.commit()
            return device_view(connection)

        @router.put("/{connection_id}")
        def edit(connection_id: str, payload: DeviceInput, session=Depends(get_session)):
            connection = connection_for(session, connection_id)
            if connection.version != payload.version:
                raise HTTPException(409, "Device connection changed. Refresh before editing.")
            endpoint = endpoint_for(payload.endpoint)
            changed_endpoint = endpoint != connection.configuration["endpoint"]
            schemas = {} if changed_endpoint else connection.configuration.get("schemas", {})
            if not set(payload.tools).issubset(schemas):
                raise HTTPException(422, "Choose only tools from the latest device discovery.")
            if changed_endpoint and payload.token is None:
                raise HTTPException(422, "Enter the device token again when changing its address.")
            secret = connection.secret
            if payload.token is not None:
                secret = SecretVault(self.settings).seal(
                    {"token": payload.token.get_secret_value()},
                    f"mcp:{session.workspace_id}:{connection_id}:{endpoint}",
                )
            changed = session.execute(
                update(Integration)
                .where(Integration.id == connection_id, Integration.version == payload.version)
                .values(
                    label=payload.label,
                    configuration={
                        "endpoint": endpoint,
                        "tools": payload.tools,
                        "schemas": schemas,
                    },
                    secret=secret,
                    version=payload.version + 1,
                )
            )
            if changed.rowcount != 1:
                raise HTTPException(409, "Device connection changed. Refresh before editing.")
            record(session, "device.permissions_changed", connection_id, tools=payload.tools)
            session.commit()
            return device_view(session.get(Integration, connection_id))

        @router.post("/{connection_id}/discover")
        async def discover(
            connection_id: str, payload: DeviceDiscoveryInput, session=Depends(get_session)
        ):
            connection = connection_for(session, connection_id)
            if connection.version != payload.version:
                raise HTTPException(409, "Device connection changed. Refresh before discovery.")
            if not payload.allow_external:
                raise HTTPException(
                    400, "Confirm connecting to this device service before discovery."
                )
            endpoint = endpoint_for(connection.configuration["endpoint"])
            secret = SecretVault(self.settings).open(
                connection.secret, f"mcp:{session.workspace_id}:{connection_id}:{endpoint}"
            )
            try:
                reserve_integration_request(
                    session, "mcp_discovery", self.settings.device_daily_limit
                )
            except KnownFailure as error:
                raise HTTPException(429, "Daily device connection limit reached.") from error
            try:
                catalog = await connectors.build("McpDevice").describe(endpoint, secret["token"])
            except Exception as error:
                raise HTTPException(
                    502,
                    "Could not connect to the device service or read its tools. Check the address and token.",
                ) from error
            changed = session.execute(
                update(Integration)
                .where(Integration.id == connection_id, Integration.version == payload.version)
                .values(
                    configuration={"endpoint": endpoint, "tools": [], "schemas": catalog},
                    version=payload.version + 1,
                )
            )
            if changed.rowcount != 1:
                raise HTTPException(409, "Device connection changed. Refresh before discovery.")
            record(session, "device.discovered", connection_id, tool_count=len(catalog))
            session.commit()
            return device_view(session.get(Integration, connection_id))

        @router.delete("/{connection_id}", status_code=204)
        def disconnect(connection_id: str, session=Depends(get_session)):
            session.delete(connection_for(session, connection_id))
            record(session, "device.disconnected", connection_id)
            session.commit()

        app.include_router(router)
