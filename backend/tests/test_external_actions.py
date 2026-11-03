import smtplib
import time
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from dayloom.api import create_app
from dayloom.automation import materialize_due
from dayloom.db import (
    LEGACY_WORKSPACE_ID,
    Action,
    AutomationRule,
    Integration,
    Workspace,
    identifier,
)
from dayloom.secrets import SecretVault
from dayloom.worker import run_once
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def connect_and_propose(client):
    connection = client.post(
        "/api/integrations/smtp",
        json={
            "label": "Personal mail",
            "host": "smtp.gmail.com",
            "username": "owner@example.com",
            "password": "private-mail-test-key",
        },
    )
    assert connection.status_code == 201
    assert "private-mail-test-key" not in connection.text
    configured = connection.json()
    response = client.post(
        "/api/actions",
        json={
            "tool": "SendEmail",
            "payload": {
                "connection_id": configured["id"],
                "connection_version": configured["version"],
                "sender": "owner@example.com",
                "to": ["recipient@example.com"],
                "subject": "Approved subject",
                "body": "Approved body",
            },
        },
    )
    assert response.status_code == 201
    return configured, response.json()


def test_smtp_requires_approval_and_records_acceptance(engine, settings, monkeypatch):
    settings.credential_key = Fernet.generate_key().decode()
    sent = []

    class MailServer:
        def __init__(self, host, port, **kwargs):
            assert (host, port) == ("smtp.gmail.com", 465)

        def login(self, username, password):
            assert (username, password) == ("owner@example.com", "private-mail-test-key")

        def send_message(self, message):
            with Session(engine) as session:
                assert session.scalar(select(Action.effect_started_at)) is not None
            sent.append(message)
            return {}

        def close(self):
            pass

    monkeypatch.setattr(smtplib, "SMTP_SSL", MailServer)
    with TestClient(create_app(settings)) as client:
        _, action = connect_and_propose(client)
        assert not run_once(engine, settings)
        assert sent == []
        assert (
            client.post(
                f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
            ).status_code
            == 200
        )
        assert run_once(engine, settings)
        assert not run_once(engine, settings)
        assert len(sent) == 1
        result = client.get("/api/actions").json()[0]
        assert result["status"] == "succeeded"
        assert result["result"]["delivery_confirmed"] is False
        assert "private-mail-test-key" not in client.get("/api/integrations").text
        with Session(engine) as session:
            assert "private-mail-test-key" not in session.scalar(select(Integration.secret))


def test_abandoned_external_effect_never_blindly_retries(engine, settings, monkeypatch):
    settings.credential_key = Fernet.generate_key().decode()

    def forbidden(*args, **kwargs):
        raise AssertionError("Must not contact mail server")

    monkeypatch.setattr(smtplib, "SMTP_SSL", forbidden)
    with TestClient(create_app(settings)) as client:
        _, action = connect_and_propose(client)
        with Session(engine) as session:
            stored = session.get(Action, action["id"])
            stored.approved_digest = stored.digest
            stored.status = "running"
            stored.lease_until = time.time() - 10
            stored.effect_started_at = time.time() - 20
            session.commit()
        assert run_once(engine, settings)
        assert client.get("/api/actions").json()[0]["status"] == "outcome_unknown"
        assert client.post(f"/api/actions/{action['id']}/retry").status_code == 409


def test_disconnected_account_cannot_send_and_smtp_destination_is_restricted(engine, settings):
    settings.credential_key = Fernet.generate_key().decode()
    with TestClient(create_app(settings)) as client:
        assert (
            client.post(
                "/api/integrations/smtp",
                json={
                    "label": "Private network",
                    "host": "127.0.0.1",
                    "username": "owner@example.com",
                    "password": "test",
                },
            ).status_code
            == 422
        )
        connection, action = connect_and_propose(client)
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        assert client.delete(f"/api/integrations/{connection['id']}").status_code == 204
        run_once(engine, settings)
        assert client.get("/api/actions").json()[0]["status"] == "failed"


def test_smtp_edit_preserves_id_and_invalidates_old_approved_mail(engine, settings, monkeypatch):
    settings.credential_key = Fernet.generate_key().decode()

    def forbidden(*args, **kwargs):
        raise AssertionError("Editing or stale mail must not contact the email server")

    monkeypatch.setattr(smtplib, "SMTP_SSL", forbidden)
    with TestClient(create_app(settings)) as client:
        connection, action = connect_and_propose(client)
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        payload = {
            "label": "Updated mail",
            "host": "smtp.gmail.com",
            "username": "updated@example.com",
            "password": "updated-synthetic-password",
            "version": connection["version"],
        }
        response = client.put(f"/api/integrations/smtp/{connection['id']}", json=payload)
        assert response.status_code == 200
        assert response.json()["id"] == connection["id"]
        assert response.json()["version"] == connection["version"] + 1
        assert "updated-synthetic-password" not in response.text
        assert (
            client.put(f"/api/integrations/smtp/{connection['id']}", json=payload).status_code
            == 409
        )
        with Session(engine) as session:
            stored = session.get(Integration, connection["id"])
            assert "updated-synthetic-password" not in stored.secret
            credentials = SecretVault(settings).open(
                stored.secret,
                f"smtp:{LEGACY_WORKSPACE_ID}:{stored.id}:smtp.gmail.com:updated@example.com",
            )
            assert credentials["password"] == "updated-synthetic-password"
        assert run_once(engine, settings)
        assert client.get("/api/actions").json()[0]["status"] == "failed"


def test_smtp_edit_keeps_password_only_for_the_same_account(engine, settings):
    settings.credential_key = Fernet.generate_key().decode()
    with TestClient(create_app(settings)) as client:
        connection, _ = connect_and_propose(client)
        with Session(engine) as session:
            original_secret = session.get(Integration, connection["id"]).secret
        payload = {
            "label": "Renamed mail",
            **connection["configuration"],
            "version": connection["version"],
        }
        response = client.put(f"/api/integrations/smtp/{connection['id']}", json=payload)
        assert response.status_code == 200
        with Session(engine) as session:
            assert session.get(Integration, connection["id"]).secret == original_secret
        payload["version"] = response.json()["version"]
        payload["username"] = "different@example.com"
        assert (
            client.put(f"/api/integrations/smtp/{connection['id']}", json=payload).status_code
            == 422
        )
        payload.update(host="127.0.0.1", password="synthetic-password")
        assert (
            client.put(f"/api/integrations/smtp/{connection['id']}", json=payload).status_code
            == 422
        )
        assert (
            client.get("/api/integrations").json()["connections"][0]["version"]
            == payload["version"]
        )


def test_smtp_edit_and_verification_cannot_access_another_workspace(engine, settings, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Must not contact another workspace's email server")

    monkeypatch.setattr(smtplib, "SMTP_SSL", forbidden)
    with Session(engine) as session:
        workspace_id = identifier()
        session.add(Workspace(id=workspace_id))
        session.commit()
        foreign = Integration(
            workspace_id=workspace_id,
            kind="smtp",
            label="Other workspace",
            configuration={"host": "smtp.gmail.com", "username": "other@example.com"},
            secret="unreadable-foreign-secret",
        )
        session.add(foreign)
        session.commit()
        connection_id = foreign.id
    with TestClient(create_app(settings)) as client:
        endpoint = f"/api/integrations/smtp/{connection_id}"
        assert (
            client.put(
                endpoint,
                json={
                    "label": "Not allowed",
                    "host": "smtp.gmail.com",
                    "username": "owner@example.com",
                    "password": "synthetic-password",
                    "version": 1,
                },
            ).status_code
            == 404
        )
        assert (
            client.post(f"{endpoint}/test", json={"version": 1, "allow_external": True}).status_code
            == 404
        )
    with Session(engine) as session:
        assert session.get(Integration, connection_id).version == 1


def test_smtp_verification_requires_consent_and_never_sends_mail(settings, monkeypatch):
    settings.credential_key = Fernet.generate_key().decode()
    settings.mail_daily_limit = 1
    logins = []

    class MailServer:
        def __init__(self, host, port, **kwargs):
            assert (host, port) == ("smtp.gmail.com", 465)

        def login(self, username, password):
            logins.append((username, password))

        def send_message(self, message):
            raise AssertionError("Connection checks must not send email")

        def close(self):
            pass

    monkeypatch.setattr(smtplib, "SMTP_SSL", MailServer)
    with TestClient(create_app(settings)) as client:
        connection, _ = connect_and_propose(client)
        endpoint = f"/api/integrations/smtp/{connection['id']}/test"
        payload = {"version": connection["version"]}
        assert client.post(endpoint, json=payload).status_code == 400
        assert logins == []
        payload["allow_external"] = True
        response = client.post(endpoint, json=payload)
        assert response.status_code == 200
        assert response.json() == {
            "connection_id": connection["id"],
            "version": connection["version"],
            "connected": True,
            "emails_sent": 0,
        }
        assert logins == [("owner@example.com", "private-mail-test-key")]
        assert client.post(endpoint, json=payload).status_code == 429
        assert client.post(endpoint, json={**payload, "version": 99}).status_code == 409
        assert len(logins) == 1
        assert "private-mail-test-key" not in client.get("/api/audit").text


@pytest.mark.parametrize(
    ("failure", "status", "detail"),
    [
        (smtplib.SMTPAuthenticationError(535, b"rejected"), 422, "Email sign-in was rejected"),
        (OSError("unreachable"), 502, "Could not reach the email server"),
    ],
)
def test_smtp_verification_distinguishes_credentials_from_network(
    settings, monkeypatch, failure, status, detail
):
    settings.credential_key = Fernet.generate_key().decode()
    closed = []

    class MailServer:
        def __init__(self, *args, **kwargs):
            pass

        def login(self, username, password):
            raise failure

        def close(self):
            closed.append(True)

    monkeypatch.setattr(smtplib, "SMTP_SSL", MailServer)
    with TestClient(create_app(settings)) as client:
        connection, _ = connect_and_propose(client)
        response = client.post(
            f"/api/integrations/smtp/{connection['id']}/test",
            json={"version": connection["version"], "allow_external": True},
        )
        assert response.status_code == status
        assert response.json()["detail"].startswith(detail)
        assert "private-mail-test-key" not in response.text
        assert closed == [True]


def test_scheduled_authority_is_exact_bounded_and_revocable(engine, settings):
    settings.credential_key = Fernet.generate_key().decode()
    with TestClient(create_app(settings)) as client:
        _, action = connect_and_propose(client)
        now = datetime.now(UTC)
        request = {
            "action_id": action["id"],
            "action_digest": action["digest"],
            "name": "One approved email",
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "interval_seconds": 3600,
            "max_runs": 1,
        }
        preview = client.post("/api/automations/preview", json=request)
        assert preview.status_code == 200
        assert client.post("/api/automations", json=request).status_code == 409
        request["approval_digest"] = preview.json()["approval_digest"]
        assert client.post("/api/automations", json={**request, "max_runs": 2}).status_code == 409
        rule = client.post("/api/automations", json=request)
        assert rule.status_code == 201
        materialize_due(engine, LEGACY_WORKSPACE_ID)
        materialize_due(engine, LEGACY_WORKSPACE_ID)
        with Session(engine) as session:
            assert (
                len(
                    session.scalars(
                        select(Action).where(Action.automation_id == rule.json()["id"])
                    ).all()
                )
                == 1
            )
            assert session.get(AutomationRule, rule.json()["id"]).runs_created == 1
        assert client.post(f"/api/automations/{rule.json()['id']}/pause").status_code == 204
        assert not run_once(engine, settings)
        assert all(stored["status"] == "cancelled" for stored in client.get("/api/actions").json())
