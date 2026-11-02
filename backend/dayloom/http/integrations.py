from dayloom.db import Integration, identifier, record
from dayloom.dependencies import get_session
from dayloom.registry import routers
from dayloom.secrets import SecretVault
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr
from sqlalchemy import select


class SmtpInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=100)
    host: str = Field(max_length=200)
    username: EmailStr
    password: SecretStr = Field(min_length=1, max_length=4096)


def integration_view(connection):
    return {
        "id": connection.id,
        "kind": connection.kind,
        "label": connection.label,
        "configuration": connection.configuration,
        "version": connection.version,
    }


@routers.register
class IntegrationRoutes:
    def __init__(self, settings):
        self.settings = settings

    def install(self, app):
        router = APIRouter(prefix="/api/integrations", tags=["integrations"])

        @router.get("")
        def connections(session=Depends(get_session)):
            return {
                "connections": [
                    integration_view(connection)
                    for connection in session.scalars(select(Integration))
                ],
                "smtp_hosts": list(self.settings.smtp_servers),
                "mail_daily_limit": self.settings.mail_daily_limit,
            }

        @router.post("/smtp", status_code=201)
        def connect_mail(payload: SmtpInput, session=Depends(get_session)):
            if payload.host not in self.settings.smtp_servers:
                raise HTTPException(422, "This SMTP server is not approved")
            connection_id = identifier()
            purpose = (
                f"smtp:{session.workspace_id}:{connection_id}:{payload.host}:{payload.username}"
            )
            connection = Integration(
                id=connection_id,
                kind="smtp",
                label=payload.label,
                configuration={"host": payload.host, "username": str(payload.username)},
                secret=SecretVault(self.settings).seal(
                    {"password": payload.password.get_secret_value()}, purpose
                ),
            )
            session.add(connection)
            record(session, "integration.connected", connection_id, kind="smtp")
            session.commit()
            return integration_view(connection)

        @router.delete("/{connection_id}", status_code=204)
        def disconnect(connection_id: str, session=Depends(get_session)):
            connection = session.get(Integration, connection_id)
            if not connection:
                raise HTTPException(404, "Connection not found")
            session.delete(connection)
            record(session, "integration.disconnected", connection_id)
            session.commit()

        app.include_router(router)
