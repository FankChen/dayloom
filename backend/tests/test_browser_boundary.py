from dayloom.browser_policy import allowed_page
from dayloom.browser_server import BrowserSettings, create_app
from dayloom.db import identifier
from fastapi.testclient import TestClient


def test_browser_service_authentication_and_origin_boundary():
    settings = BrowserSettings(
        shared_token="test-runner-token-" * 3,
        allowed_origins=["https://example.com"],
        egress_proxy="http://approved-egress:3128",
    )
    calls = []

    async def reader(payload, _settings):
        calls.append(str(payload.url))
        return {"title": "Example", "url": str(payload.url), "text": "Public content"}

    with TestClient(create_app(settings, reader=reader)) as client:
        payload = {
            "run_id": identifier(),
            "workspace_id": identifier(),
            "url": "https://example.com/",
        }
        assert client.post("/read", json=payload).status_code == 401
        headers = {"Authorization": f"Bearer {settings.shared_token.get_secret_value()}"}
        assert (
            client.post(
                "/read", json={**payload, "url": "http://127.0.0.1/"}, headers=headers
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/read",
                json={**payload, "url": "https://example.com.attacker.test/"},
                headers=headers,
            ).status_code
            == 403
        )
        assert (
            client.post("/read", json=payload, headers=headers).json()["text"] == "Public content"
        )
        assert len(calls) == 1
    assert not allowed_page("https://user:password@example.com/", settings.allowed_origins)


def test_browser_rejects_result_redirecting_outside_allowlist():
    settings = BrowserSettings(
        shared_token="test-runner-token-" * 3,
        allowed_origins=["https://example.com"],
        egress_proxy="http://approved-egress:3128",
    )

    async def reader(_payload, _settings):
        return {"title": "Unexpected", "url": "http://169.254.169.254/", "text": "Never released"}

    with TestClient(create_app(settings, reader=reader)) as client:
        response = client.post(
            "/read",
            json={
                "run_id": identifier(),
                "workspace_id": identifier(),
                "url": "https://example.com/",
            },
            headers={"Authorization": f"Bearer {settings.shared_token.get_secret_value()}"},
        )
        assert response.status_code == 403
        assert "Never released" not in response.text
