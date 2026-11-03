import smtplib
from contextlib import suppress

from dayloom.db import Integration, identifier, record
from dayloom.dependencies import get_session
from dayloom.executors import KnownFailure
from dayloom.integrations import reserve_integration_request
from dayloom.registry import connectors, routers
from dayloom.secrets import SecretVault
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr
from sqlalchemy import select, update


class SmtpInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=100)
    host: str = Field(max_length=200)
    username: EmailStr
    password: SecretStr = Field(min_length=1, max_length=4096)


class SmtpUpdate(SmtpInput):
    password: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    version: int = Field(ge=1)


class SmtpVerificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    allow_external: bool = False


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

        @router.put("/smtp/{connection_id}")
        def update_mail(connection_id: str, payload: SmtpUpdate, session=Depends(get_session)):
            connection = session.get(Integration, connection_id)
            if not connection or connection.kind != "smtp":
                raise HTTPException(404, "Connection not found")
            if connection.version != payload.version:
                raise HTTPException(
                    409, "Email connection changed. Reopen the editor and try again."
                )
            if payload.host not in self.settings.smtp_servers:
                raise HTTPException(422, "This SMTP server is not approved")
            configuration = {"host": payload.host, "username": str(payload.username)}
            secret = connection.secret
            if payload.password is not None:
                purpose = (
                    f"smtp:{session.workspace_id}:{connection_id}:{payload.host}:{payload.username}"
                )
                secret = SecretVault(self.settings).seal(
                    {"password": payload.password.get_secret_value()}, purpose
                )
            elif configuration != connection.configuration:
                raise HTTPException(
                    422, "Enter a new app password when changing the email address or server."
                )
            changed = session.execute(
                update(Integration)
                .where(Integration.id == connection_id, Integration.version == payload.version)
                .values(
                    label=payload.label,
                    configuration=configuration,
                    secret=secret,
                    version=payload.version + 1,
                )
            )
            if changed.rowcount != 1:
                raise HTTPException(
                    409, "Email connection changed. Reopen the editor and try again."
                )
            record(session, "integration.updated", connection_id, kind="smtp")
            session.commit()
            return integration_view(session.get(Integration, connection_id))

        @router.post("/smtp/{connection_id}/test")
        def verify_mail(
            connection_id: str, payload: SmtpVerificationInput, session=Depends(get_session)
        ):
            connection = session.get(Integration, connection_id)
            if not connection or connection.kind != "smtp":
                raise HTTPException(404, "Connection not found")
            if connection.version != payload.version:
                raise HTTPException(409, "Email connection changed. Refresh before testing.")
            if not payload.allow_external:
                raise HTTPException(
                    400, "Confirm the email sign-in check before contacting the server."
                )
            configuration = connection.configuration
            if configuration["host"] not in self.settings.smtp_servers:
                raise HTTPException(422, "This SMTP server is not approved")
            credentials = SecretVault(self.settings).open(
                connection.secret,
                f"smtp:{session.workspace_id}:{connection_id}:{configuration['host']}:{configuration['username']}",
            )
            try:
                reserve_integration_request(session, "smtp_test", self.settings.mail_daily_limit)
            except KnownFailure as error:
                raise HTTPException(
                    429, "Daily email verification limit reached. Try again tomorrow."
                ) from error
            client = None
            try:
                client = connectors.build(self.settings.smtp_servers[configuration["host"]]).open(
                    configuration["host"]
                )
                client.login(configuration["username"], credentials["password"])
            except smtplib.SMTPAuthenticationError as error:
                raise HTTPException(
                    422,
                    "Email sign-in was rejected. Check the app password and that SMTP access is enabled.",
                ) from error
            except (smtplib.SMTPException, OSError) as error:
                raise HTTPException(
                    502, "Could not reach the email server. Check the connection and try again."
                ) from error
            finally:
                if client is not None:
                    with suppress(smtplib.SMTPException, OSError):
                        client.close()
            record(
                session, "integration.verified", connection_id, kind="smtp", version=payload.version
            )
            session.commit()
            return {
                "connection_id": connection_id,
                "version": payload.version,
                "connected": True,
                "emails_sent": 0,
            }

        @router.delete("/{connection_id}", status_code=204)
        def disconnect(connection_id: str, session=Depends(get_session)):
            connection = session.get(Integration, connection_id)
            if not connection:
                raise HTTPException(404, "Connection not found")
            session.delete(connection)
            record(session, "integration.disconnected", connection_id)
            session.commit()

        app.include_router(router)
