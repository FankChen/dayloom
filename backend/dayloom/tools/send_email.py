import smtplib
from email.message import EmailMessage
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from dayloom.db import Action, Integration
from dayloom.executors import KnownFailure, OutcomeUnknown
from dayloom.integrations import reserve_integration_request
from dayloom.policy import require_action_authority
from dayloom.registry import connectors, tools
from dayloom.secrets import SecretVault
from dayloom.workspaces import WorkspaceSession


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    connection_id: UUID
    connection_version: int = Field(ge=1)
    sender: EmailStr
    to: list[EmailStr] = Field(min_length=1, max_length=10)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)

    @field_validator("subject")
    @classmethod
    def single_line_subject(cls, value):
        if "\n" in value or "\r" in value:
            raise ValueError("Subject must be a single line")
        return value


@tools.register
class SendEmail:
    label = "Send an email"
    description = "Send a plain-text email through a connected SMTP account. Requires the exact connection id/version, matching sender and explicit approval. Acceptance does not prove delivery."
    input_model = EmailInput
    executor = "ExternalExecution"
    automation_allowed = True

    def __init__(self, engine, settings, workspace_id, action_id, claim):
        self.engine = engine
        self.settings = settings
        self.workspace_id = workspace_id
        self.action_id = action_id
        self.claim = claim

    def execute(self, payload):
        with WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session:
            connection = session.get(Integration, str(payload.connection_id))
            if (
                not connection
                or connection.kind != "smtp"
                or connection.version != payload.connection_version
            ):
                raise KnownFailure("Mail connection was removed or changed")
            configuration = connection.configuration
            if (
                configuration["username"] != str(payload.sender)
                or configuration["host"] not in self.settings.smtp_servers
            ):
                raise KnownFailure("Mail account or destination is not authorized")
            credentials = SecretVault(self.settings).open(
                connection.secret,
                f"smtp:{self.workspace_id}:{connection.id}:{configuration['host']}:{configuration['username']}",
            )
            reserve_integration_request(session, "smtp", self.settings.mail_daily_limit)
        message = EmailMessage()
        message["From"] = str(payload.sender)
        message["To"] = ", ".join(str(address) for address in payload.to)
        message["Subject"] = payload.subject
        message["Message-ID"] = f"<{self.action_id}@dayloom.invalid>"
        message.set_content(payload.body)
        client = None
        try:
            try:
                client = connectors.build(self.settings.smtp_servers[configuration["host"]]).open(
                    configuration["host"]
                )
                client.login(configuration["username"], credentials["password"])
            except Exception as error:
                raise KnownFailure(
                    "SMTP connection or authentication failed before sending"
                ) from error
            with WorkspaceSession(self.engine, workspace_id=self.workspace_id) as session:
                current = session.get(Integration, str(payload.connection_id))
                action = session.get(Action, self.action_id)
                if (
                    not current
                    or current.version != payload.connection_version
                    or not action
                    or action.claim_token != self.claim
                    or action.status != "running"
                ):
                    raise KnownFailure("Execution authority changed before sending")
                require_action_authority(action, session)
            try:
                refused = client.send_message(message)
            except (
                smtplib.SMTPRecipientsRefused,
                smtplib.SMTPSenderRefused,
                smtplib.SMTPDataError,
            ) as error:
                raise KnownFailure("SMTP server rejected the message") from error
            except Exception as error:
                raise OutcomeUnknown() from error
            return {
                "kind": "email",
                "title": "Accepted by SMTP server"
                if not refused
                else "Partially accepted by SMTP server",
                "message_id": str(message["Message-ID"]),
                "rejected_recipients": list(refused),
                "delivery_confirmed": False,
            }
        finally:
            if client:
                client.close()
