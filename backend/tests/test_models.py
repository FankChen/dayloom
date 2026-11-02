import httpx
from cryptography.fernet import Fernet
from dayloom.api import create_app
from dayloom.db import Action, ModelConnection
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def configuration(**changes):
    return {"model": "test-model", "api_key": "private-test-key", **changes}


def test_default_startup_does_not_silently_use_a_demo(settings):
    from dayloom.config import Settings

    configured = Settings(database_url=settings.database_url, _env_file=None)
    with TestClient(create_app(configured)) as client:
        assert client.get("/api/settings").json()["provider"]["configured"] is False
        assert (
            client.post("/api/chat", json={"content": "Hello", "allow_external": True}).status_code
            == 409
        )
        assert client.get("/api/messages").json() == []


def test_model_credentials_are_encrypted_and_never_exported(settings, engine):
    settings.credential_key = Fernet.generate_key().decode()
    with TestClient(create_app(settings)) as client:
        saved = client.put("/api/models", json=configuration())
        assert saved.status_code == 200
        assert saved.json()["version"] == 1
        assert "private-test-key" not in saved.text
        assert "private-test-key" not in client.get("/api/models").text
        assert "private-test-key" not in client.get("/api/data").text
        assert "private-test-key" not in client.get("/api/audit").text
        with Session(engine) as session:
            stored = session.scalar(select(ModelConnection))
            assert "private-test-key" not in stored.secret
        assert client.put("/api/models", json=configuration()).status_code == 409
        assert (
            client.put("/api/models", json=configuration(version=1, model="new-model")).status_code
            == 200
        )
        assert client.delete("/api/models").status_code == 204


def test_model_endpoint_allowlist_rejects_ssrf_targets(settings):
    settings.credential_key = Fernet.generate_key().decode()
    with TestClient(create_app(settings)) as client:
        for endpoint in [
            "http://127.0.0.1/v1",
            "https://169.254.169.254/v1",
            "https://api.openai.com@attacker.example/v1",
            "https://attacker.example/v1",
            "https://api.openai.com/v1?redirect=private",
        ]:
            assert (
                client.put("/api/models", json=configuration(base_url=endpoint)).status_code == 422
            )


def test_real_provider_transport_consent_and_quota(settings, engine, monkeypatch):
    settings.credential_key = Fernet.generate_key().decode()
    captured = []

    async def provider_response(_client, url, **kwargs):
        captured.append((url, kwargs))
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [
                    {"message": {"content": '{"message":"Provider response","proposals":[]}'}}
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", provider_response)
    with TestClient(create_app(settings)) as client:
        assert (
            client.put("/api/models", json=configuration(daily_limit=1, max_tokens=512)).status_code
            == 200
        )
        assert client.post("/api/chat", json={"content": "Hello"}).status_code == 400
        response = client.post("/api/chat", json={"content": "Hello", "allow_external": True})
        assert response.status_code == 200
        assert response.json()["message"]["provider"] == "OpenAIProvider"
        assert captured[0][1]["headers"]["Authorization"] == "Bearer private-test-key"
        assert captured[0][1]["json"]["model"] == "test-model"
        assert captured[0][1]["json"]["max_tokens"] == 512
        assert (
            client.post("/api/chat", json={"content": "Again", "allow_external": True}).status_code
            == 429
        )
        assert len(captured) == 1
        with Session(engine) as session:
            assert session.scalars(select(Action)).all() == []
