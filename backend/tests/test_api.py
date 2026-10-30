from datetime import date

import pytest
from dayloom.api import create_app
from dayloom.db import Action, Memory
from dayloom.registry import providers
from dayloom.schemas import ModelReply
from dayloom.worker import run_once
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def test_chat_approval_and_background_execution(client, settings):
    response = client.post("/api/chat", json={"content": "Draft an outline"})
    assert response.status_code == 200
    action = response.json()["actions"][0]
    assert client.get("/api/tasks").json() == []
    approved = client.post(
        f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
    )
    assert approved.status_code == 200
    assert run_once(client.app.state.engine, settings)
    assert client.get("/api/tasks").json()[0]["title"] == "Draft an outline"
    assert not run_once(client.app.state.engine, settings)


def test_revision_invalidates_previous_approval(client, settings):
    action = client.post(
        "/api/actions", json={"tool": "CreateTask", "payload": {"title": "Original"}}
    ).json()
    client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
    edited = client.patch(
        f"/api/actions/{action['id']}",
        json={"digest": action["digest"], "payload": {"title": "Revised"}},
    )
    assert edited.json()["status"] == "pending"
    assert not run_once(client.app.state.engine, settings)
    assert (
        client.post(
            f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
        ).status_code
        == 409
    )


def test_cancelled_and_duplicate_approvals(client, settings):
    action = client.post(
        "/api/actions", json={"tool": "CreateTask", "payload": {"title": "No"}}
    ).json()
    assert client.post(f"/api/actions/{action['id']}/cancel").status_code == 200
    assert (
        client.post(
            f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
        ).status_code
        == 409
    )
    assert not run_once(client.app.state.engine, settings)


def test_task_version_conflict_and_validation(client):
    task = client.post("/api/tasks", json={"title": "Read"}).json()
    edited = {"title": "Read carefully", "version": task["version"], "status": "doing"}
    assert client.put(f"/api/tasks/{task['id']}", json=edited).status_code == 200
    assert client.put(f"/api/tasks/{task['id']}", json=edited).status_code == 409
    assert client.post("/api/tasks", json={"title": "", "minutes": -1}).status_code == 422


def test_memory_crud_and_expiration(client, monkeypatch):
    seen = {}

    async def capture(self, content, context):
        seen.update(context)
        return ModelReply(message="Noted")

    monkeypatch.setattr(providers.classes["DemoProvider"], "reply", capture)
    expired = client.post(
        "/api/memories", json={"content": "Old preference", "expires_on": "2000-01-01"}
    ).json()
    active = client.post("/api/memories", json={"content": "Current preference"}).json()
    assert client.post("/api/chat", json={"content": "Hello"}).status_code == 200
    assert [memory["content"] for memory in seen["memories"]] == ["Current preference"]
    assert client.delete(f"/api/memories/{active['id']}").status_code == 204
    assert client.delete(f"/api/memories/{expired['id']}").status_code == 204
    assert client.get("/api/memories").json() == []


def test_external_provider_requires_explicit_consent(settings):
    settings.model_provider = "OpenAIProvider"
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/chat", json={"content": "Hello"}).status_code == 400
        assert client.get("/api/messages").json() == []
        assert client.get("/api/settings").json()["provider"]["configured"] is False


def test_authentication_and_cross_origin_rejection(settings):
    settings.access_token = "test-access-token"
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/tasks").status_code == 401
        headers = {"Authorization": "Bearer test-access-token"}
        assert client.get("/api/tasks", headers=headers).status_code == 200
        assert (
            client.post(
                "/api/tasks",
                json={"title": "Injected"},
                headers={**headers, "Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )
        assert "test-access-token" not in client.get("/api/settings", headers=headers).text
        preflight = client.options(
            "/api/data",
            headers={
                "Origin": "capacitor://localhost",
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "authorization,x-dayloom-confirm",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "capacitor://localhost"


def test_calendar_import_replaces_snapshot_and_handles_recurrence(client):
    today = date.fromisoformat(client.get("/api/plan").json()["day"])
    day = today.strftime("%Y%m%d")
    calendar = f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:weekly\nDTSTART:{day}T010000Z\nDTEND:{day}T020000Z\nRRULE:FREQ=DAILY;COUNT=2\nSUMMARY:Standup\nEND:VEVENT\nEND:VCALENDAR"
    assert client.post("/api/calendar/import", json={"content": calendar}).json()["imported"] == 2
    assert client.post("/api/calendar/import", json={"content": calendar}).json()["imported"] == 2
    assert len(client.get("/api/calendar").json()) == 2
    assert client.post("/api/calendar/import", json={"content": "broken"}).status_code == 422
    assert len(client.get("/api/calendar").json()) == 2


def test_data_export_and_explicit_deletion(client):
    assert client.post("/api/demo").status_code == 201
    assert client.post("/api/demo").status_code == 409
    exported = client.get("/api/data").json()
    assert len(exported["tasks"]) == 4
    assert len(exported["memories"]) == 2
    assert client.delete("/api/data").status_code == 400
    assert (
        client.delete("/api/data", headers={"x-dayloom-confirm": "DELETE MY DATA"}).status_code
        == 204
    )
    assert client.get("/api/tasks").json() == []
    assert client.get("/api/audit").json() == []


def test_failed_action_requires_fresh_approval(client, settings):
    action = client.post(
        "/api/actions", json={"tool": "CreateTask", "payload": {"title": "Review"}}
    ).json()
    with Session(client.app.state.engine) as session:
        stored = session.get(Action, action["id"])
        stored.status = "failed"
        stored.attempts = 3
        session.commit()
    assert client.post(f"/api/actions/{action['id']}/retry").json()["status"] == "pending"
    assert not run_once(client.app.state.engine, settings)


def test_memory_action_records_only_metadata_in_audit(client, settings):
    action = client.post("/api/chat", json={"content": "remember: Private personal detail"}).json()[
        "actions"
    ][0]
    client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
    run_once(client.app.state.engine, settings)
    assert "Private personal detail" not in client.get("/api/audit").text
    with Session(client.app.state.engine) as session:
        assert session.scalar(select(Memory)).content == "Private personal detail"
