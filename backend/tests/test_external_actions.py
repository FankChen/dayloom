import smtplib
import time
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from dayloom.api import create_app
from dayloom.automation import materialize_due
from dayloom.db import LEGACY_WORKSPACE_ID, Action, AutomationRule, Integration
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
