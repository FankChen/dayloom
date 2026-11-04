import asyncio
import hashlib
import json

import httpx
import pytest
from cryptography.fernet import Fernet
from dayloom.api import create_app
from dayloom.connectors.mcp import McpDevice
from dayloom.db import Integration
from dayloom.device_server import (
    DeviceServerSettings,
    create_device_app,
    download_approved_software,
    open_approved_url,
)
from dayloom.devices import validate_device_endpoint, validate_tool_arguments
from dayloom.registry import connectors, providers
from dayloom.schemas import AgentDecision, Proposal
from dayloom.worker import run_once
from fastapi.testclient import TestClient
from pydantic import SecretStr
from referencing.exceptions import Unresolvable
from sqlalchemy import select
from sqlalchemy.orm import Session

ENDPOINT = "http://127.0.0.1:19888/mcp"
CATALOG = {
    "open_url": {
        "name": "open_url",
        "description": "Open a permitted page on the device",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    }
}


def connect_device(client, monkeypatch):
    async def describe(self, endpoint, token):
        assert endpoint == ENDPOINT
        assert token == "synthetic-device-token"
        return CATALOG

    monkeypatch.setattr(connectors.classes["McpDevice"], "describe", describe)
    connected = client.post(
        "/api/devices",
        json={"label": "My test device", "endpoint": ENDPOINT, "token": "synthetic-device-token"},
    )
    assert connected.status_code == 201
    assert "synthetic-device-token" not in connected.text
    connection = connected.json()
    endpoint = f"/api/devices/{connection['id']}"
    assert (
        client.post(f"{endpoint}/discover", json={"version": connection["version"]}).status_code
        == 400
    )
    discovered = client.post(
        f"{endpoint}/discover", json={"version": connection["version"], "allow_external": True}
    )
    assert discovered.status_code == 200
    assert discovered.json()["authorized_tools"] == []
    selected = client.put(
        endpoint,
        json={
            "label": connection["label"],
            "endpoint": ENDPOINT,
            "version": discovered.json()["version"],
            "tools": ["open_url"],
        },
    )
    assert selected.status_code == 200
    return selected.json()


def test_device_discovery_and_exact_approved_invocation(engine, settings, monkeypatch):
    settings.mcp_allowed_servers = [ENDPOINT]
    settings.credential_key = Fernet.generate_key().decode()
    calls = []

    async def invoke(self, endpoint, token, name, arguments, schema, action_id, authorize, state):
        authorize()
        state["attempted"] = True
        calls.append((name, arguments))
        return {
            "blocked": False,
            "is_error": False,
            "text": "Opened for the user",
            "data": {"status": "opened", "purchase_completed": False},
        }

    monkeypatch.setattr(connectors.classes["McpDevice"], "invoke", invoke)
    with TestClient(create_app(settings)) as client:
        connection = connect_device(client, monkeypatch)
        payload = {
            "connection_id": connection["id"],
            "connection_version": connection["version"],
            "tool_name": "open_url",
            "arguments": {"url": "https://example.com"},
        }
        action = client.post(
            "/api/actions", json={"tool": "CallDeviceTool", "payload": payload}
        ).json()
        assert not run_once(engine, settings)
        assert calls == []
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        assert run_once(engine, settings)
        assert calls == [("open_url", {"url": "https://example.com"})]
        assert client.get("/api/actions").json()[0]["result"]["data"]["purchase_completed"] is False
        assert not run_once(engine, settings)
        with Session(engine) as session:
            assert "synthetic-device-token" not in session.scalar(select(Integration.secret))


@pytest.mark.parametrize("failure", ["before", "after", "schema"])
def test_device_failure_boundary_never_blindly_replays(engine, settings, monkeypatch, failure):
    settings.mcp_allowed_servers = [ENDPOINT]
    settings.credential_key = Fernet.generate_key().decode()

    async def invoke(self, endpoint, token, name, arguments, schema, action_id, authorize, state):
        if failure == "schema":
            return {"blocked": True}
        state["attempted"] = failure == "after"
        raise OSError("Test disconnection")

    monkeypatch.setattr(connectors.classes["McpDevice"], "invoke", invoke)
    with TestClient(create_app(settings)) as client:
        connection = connect_device(client, monkeypatch)
        action = client.post(
            "/api/actions",
            json={
                "tool": "CallDeviceTool",
                "payload": {
                    "connection_id": connection["id"],
                    "connection_version": connection["version"],
                    "tool_name": "open_url",
                    "arguments": {"url": "https://example.com"},
                },
            },
        ).json()
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        assert run_once(engine, settings)
        result = client.get("/api/actions").json()[0]
        assert result["status"] == ("outcome_unknown" if failure == "after" else "failed")
        assert not run_once(engine, settings)
        if failure == "after":
            assert client.post(f"/api/actions/{action['id']}/retry").status_code == 409


def test_device_configuration_and_arguments_fail_closed(engine, settings, monkeypatch):
    settings.mcp_allowed_servers = [ENDPOINT]
    settings.credential_key = Fernet.generate_key().decode()
    with pytest.raises(ValueError):
        validate_device_endpoint("http://169.254.169.254/mcp", settings)
    with pytest.raises(ValueError):
        validate_device_endpoint("https://user:password@example.com/mcp", settings)
    with pytest.raises(Unresolvable):
        validate_tool_arguments({"$ref": "https://untrusted.example/schema"}, {})
    with TestClient(create_app(settings)) as client:
        connection = connect_device(client, monkeypatch)
        assert (
            client.put(
                f"/api/devices/{connection['id']}",
                json={
                    "label": connection["label"],
                    "endpoint": ENDPOINT,
                    "version": connection["version"],
                    "tools": ["run_arbitrary_command"],
                },
            ).status_code
            == 422
        )
        action = client.post(
            "/api/actions",
            json={
                "tool": "CallDeviceTool",
                "payload": {
                    "connection_id": connection["id"],
                    "connection_version": connection["version"],
                    "tool_name": "open_url",
                    "arguments": {"command": "not allowed"},
                },
            },
        ).json()
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        assert run_once(engine, settings)
        assert client.get("/api/actions").json()[0]["status"] == "failed"


def test_mcp_connector_uses_the_real_sdk_protocol_without_live_network(monkeypatch):
    calls = []

    def server(request):
        payload = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer synthetic-protocol-token"
        method = payload["method"]
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": payload["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "test-device", "version": "1"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "open_url",
                        "description": "Open a permitted page",
                        "inputSchema": CATALOG["open_url"]["input_schema"],
                    }
                ]
            }
        elif method == "tools/call":
            calls.append(payload["params"])
            result = {
                "content": [{"type": "text", "text": "opened"}],
                "structuredContent": {"status": "opened"},
                "isError": False,
            }
        else:
            raise AssertionError(method)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "dayloom.connectors.mcp.httpx.AsyncClient",
        lambda **options: original_client(transport=httpx.MockTransport(server), **options),
    )

    async def exercise():
        connector = McpDevice()
        catalog = await connector.describe(ENDPOINT, "synthetic-protocol-token")
        state = {"attempted": False}
        result = await connector.invoke(
            ENDPOINT,
            "synthetic-protocol-token",
            "open_url",
            {"url": "https://example.com"},
            catalog["open_url"]["input_schema"],
            "test-action",
            lambda: None,
            state,
        )
        assert state["attempted"]
        assert result["data"] == {"status": "opened"}
        blocked = {"attempted": False}
        result = await connector.invoke(
            ENDPOINT,
            "synthetic-protocol-token",
            "open_url",
            {"url": "https://example.com"},
            {},
            "test-action",
            lambda: None,
            blocked,
        )
        assert result["blocked"] and not blocked["attempted"]

    asyncio.run(exercise())
    assert len(calls) == 1
    assert calls[0]["_meta"]["io.dayloom/action_id"] == "test-action"


def test_agent_inspects_device_then_waits_for_exact_action_approval(engine, settings, monkeypatch):
    settings.mcp_allowed_servers = [ENDPOINT]
    settings.credential_key = Fernet.generate_key().decode()
    calls = []

    async def invoke(self, endpoint, token, name, arguments, schema, action_id, authorize, state):
        authorize()
        state["attempted"] = True
        calls.append(name)
        return {
            "blocked": False,
            "is_error": False,
            "text": "Opened for manual completion",
            "data": {"status": "opened", "purchase_completed": False},
        }

    async def plan(self, goal, context):
        device = next(
            connection for connection in context["connections"] if connection["kind"] == "mcp"
        )
        results = context["tool_results"]
        if not results:
            return AgentDecision(
                decision="act",
                message="Inspect approved device tool",
                proposal=Proposal(
                    tool="ListDeviceTools",
                    payload={"connection_id": device["id"], "tool_name": "open_url"},
                ),
            )
        if len(results) == 1:
            assert (
                results[0]["result"]["tools"][0]["input_schema"]
                == CATALOG["open_url"]["input_schema"]
            )
            return AgentDecision(
                decision="act",
                message="Ask approval to open the page",
                proposal=Proposal(
                    tool="CallDeviceTool",
                    payload={
                        "connection_id": device["id"],
                        "connection_version": device["version"],
                        "tool_name": "open_url",
                        "arguments": {"url": "https://example.com"},
                    },
                ),
            )
        assert results[-1]["result"]["data"]["purchase_completed"] is False
        return AgentDecision(
            decision="finish", message="The page was opened on your device. No purchase was made."
        )

    monkeypatch.setattr(connectors.classes["McpDevice"], "invoke", invoke)
    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        connect_device(client, monkeypatch)
        response = client.post(
            "/api/agent/runs",
            json={
                "goal": "Open the approved page on my device",
                "allowed_tools": ["ListDeviceTools", "CallDeviceTool"],
                "auto_readonly": True,
            },
        )
        assert response.status_code == 201
        run_id = response.json()["id"]
        assert run_once(engine, settings)
        assert run_once(engine, settings)
        assert run_once(engine, settings)
        action = client.get(f"/api/agent/runs/{run_id}").json()["steps_history"][-1]["action"]
        assert action["status"] == "pending" and calls == []
        assert not run_once(engine, settings)
        assert (
            client.post(
                f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
            ).status_code
            == 200
        )
        assert run_once(engine, settings)
        assert run_once(engine, settings)
        assert calls == ["open_url"]
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "completed"


def test_first_party_device_server_requires_token_and_approved_action(monkeypatch):
    opened = []
    monkeypatch.setattr(
        "dayloom.device_server.webbrowser.open", lambda url, **options: opened.append(url) or True
    )
    settings = DeviceServerSettings(
        _env_file=None,
        token=SecretStr("synthetic-device-service-token-0001"),
        allowed_origins=["https://example.com"],
    )
    headers = {
        "Authorization": "Bearer synthetic-device-service-token-0001",
        "Accept": "application/json, text/event-stream",
    }
    with TestClient(create_device_app(settings), base_url=ENDPOINT.removesuffix("/mcp")) as client:
        assert client.post("/mcp", json={}).status_code == 401
        assert (
            client.post("/mcp", headers={"Authorization": "Bearer invalid"}, json={}).status_code
            == 401
        )
        assert (
            client.post("/mcp", headers=[(b"authorization", b"Bearer \xff")], json={}).status_code
            == 401
        )
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "open_url", "arguments": {"url": "https://example.com"}},
        }
        response = client.post("/mcp", headers=headers, json=request)
        assert response.status_code == 200
        assert response.json()["result"]["isError"]
        assert opened == []
        request["params"]["_meta"] = {
            "io.dayloom/action_id": "00000000-0000-0000-0000-000000000001"
        }
        response = client.post("/mcp", headers=headers, json=request)
        assert response.status_code == 200
        assert response.json()["result"]["isError"] is False
        assert opened == ["https://example.com"]
        assert response.json()["result"]["structuredContent"]["purchase_completed"] is False


def test_device_download_is_hash_verified_bounded_and_never_overwrites(tmp_path, monkeypatch):
    body = b"synthetic software package"
    settings = DeviceServerSettings(
        _env_file=None,
        token=SecretStr("synthetic-device-service-token-0001"),
        download_dir=tmp_path / "downloads",
        software={
            "sample": {
                "title": "Sample package",
                "url": "https://example.com/software.bin",
                "filename": "sample.bin",
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        },
    )
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "dayloom.device_server.httpx.AsyncClient",
        lambda **options: original_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, stream=httpx.ByteStream(body), headers={"content-length": str(len(body))}
                )
            ),
            **options,
        ),
    )
    result = asyncio.run(download_approved_software(settings, "sample"))
    assert (settings.download_dir / "sample.bin").read_bytes() == body
    assert result["installed"] is False and result["executed"] is False
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(download_approved_software(settings, "sample"))
    assert (settings.download_dir / "sample.bin").read_bytes() == body


@pytest.mark.parametrize("failure", ["checksum", "size", "redirect"])
def test_device_download_rejects_untrusted_or_oversized_content(tmp_path, monkeypatch, failure):
    body = b"package"
    settings = DeviceServerSettings(
        _env_file=None,
        token=SecretStr("synthetic-device-service-token-0001"),
        download_dir=tmp_path / "downloads",
        max_download_bytes=1 if failure == "size" else 100,
        software={
            "sample": {
                "title": "Sample",
                "url": "https://example.com/software.bin",
                "filename": "sample.bin",
                "sha256": "0" * 64 if failure == "checksum" else hashlib.sha256(body).hexdigest(),
            }
        },
    )
    original_client = httpx.AsyncClient

    def response(request):
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
        return httpx.Response(
            200, stream=httpx.ByteStream(body), headers={"content-length": str(len(body))}
        )

    monkeypatch.setattr(
        "dayloom.device_server.httpx.AsyncClient",
        lambda **options: original_client(transport=httpx.MockTransport(response), **options),
    )
    with pytest.raises((ValueError, httpx.HTTPStatusError)):
        asyncio.run(download_approved_software(settings, "sample"))
    assert list(settings.download_dir.iterdir()) == []
    with pytest.raises(ValueError):
        open_approved_url(settings, "file:///etc/passwd")


@pytest.mark.parametrize("stage", ["headers", "body"])
def test_device_download_total_timeout_removes_temporary_files(tmp_path, monkeypatch, stage):
    settings = DeviceServerSettings(
        _env_file=None,
        token=SecretStr("synthetic-device-service-token-0001"),
        download_dir=tmp_path / "downloads",
        download_timeout_seconds=0.01,
        software={
            "sample": {
                "title": "Sample",
                "url": "https://example.com/software.bin",
                "filename": "sample.bin",
                "sha256": "0" * 64,
            }
        },
    )

    class StalledStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.Event().wait()
            yield b"unreachable"

    async def response(request):
        if stage == "headers":
            await asyncio.Event().wait()
        return httpx.Response(200, stream=StalledStream())

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "dayloom.device_server.httpx.AsyncClient",
        lambda **options: original_client(transport=httpx.MockTransport(response), **options),
    )
    with pytest.raises(TimeoutError):
        asyncio.run(download_approved_software(settings, "sample"))
    assert list(settings.download_dir.iterdir()) == []
