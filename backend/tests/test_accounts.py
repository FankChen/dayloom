import time
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from dayloom.api import create_app
from dayloom.db import AccountIdentity, AccountSession, LoginFlow, Workspace
from dayloom.http.auth import AccountRoutes, challenge
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def account_client(settings, engine):
    settings.auth_backend = "OidcAccess"
    settings.oidc_issuer = "https://identity.example/realms/dayloom"
    settings.credential_key = Fernet.generate_key().decode()
    settings.public_url = "https://testserver"
    return TestClient(create_app(settings), base_url="https://testserver")


def issue_account(engine, settings, subject):
    with Session(engine) as session:
        workspace = Workspace(name=subject)
        session.add(workspace)
        session.flush()
        identity = AccountIdentity(
            issuer=settings.oidc_issuer, subject=subject, workspace_id=workspace.id, name=subject
        )
        session.add(identity)
        session.flush()
        tokens = AccountRoutes(settings, engine).new_session(session, identity.id, "Test device")
        session.commit()
        return tokens


def test_accounts_cannot_read_edit_delete_or_export_another_workspace(settings, engine):
    with account_client(settings, engine) as client:
        assert client.get("/api/tasks").status_code == 401
        assert client.get("/api/auth/config").json()["mode"] == "oidc"
        first = issue_account(engine, settings, "first")
        second = issue_account(engine, settings, "second")
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        task = client.post(
            "/api/tasks", headers=first_headers, json={"title": "Private task"}
        ).json()
        assert client.get("/api/tasks", headers=second_headers).json() == []
        assert (
            client.put(
                f"/api/tasks/{task['id']}",
                headers=second_headers,
                json={"title": "Overwrite", "version": task["version"]},
            ).status_code
            == 409
        )
        assert client.delete(f"/api/tasks/{task['id']}", headers=second_headers).status_code == 404
        assert client.get("/api/data", headers=second_headers).json()["tasks"] == []
        assert (
            client.delete(
                "/api/data", headers={**second_headers, "X-Dayloom-Confirm": "DELETE MY DATA"}
            ).status_code
            == 204
        )
        assert len(client.get("/api/tasks", headers=first_headers).json()) == 1


def test_refresh_rotates_credentials_and_revocation_is_immediate(settings, engine):
    with account_client(settings, engine) as client:
        tokens = issue_account(engine, settings, "owner")
        refreshed = client.post(
            "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refreshed.status_code == 200
        assert (
            client.post(
                "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/api/tasks", headers={"Authorization": f"Bearer {tokens['access_token']}"}
            ).status_code
            == 401
        )
        headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
        sessions = client.get("/api/auth/sessions", headers=headers).json()
        assert len(sessions) == 1
        assert "access_hash" not in sessions[0]
        assert (
            client.delete(f"/api/auth/sessions/{sessions[0]['id']}", headers=headers).status_code
            == 204
        )
        assert client.get("/api/tasks", headers=headers).status_code == 401


def test_cookie_sessions_require_csrf_header(settings, engine):
    with account_client(settings, engine) as client:
        tokens = issue_account(engine, settings, "cookie-owner")
        client.cookies.set("dayloom_access", tokens["access_token"])
        assert client.get("/api/tasks").status_code == 200
        assert client.post("/api/tasks", json={"title": "Blocked"}).status_code == 403
        assert (
            client.post(
                "/api/tasks", headers={"X-Dayloom-CSRF": "1"}, json={"title": "Allowed"}
            ).status_code
            == 201
        )
        assert client.get("/api/auth/callback?state=bad&code=bad").status_code == 400


def test_native_login_ticket_requires_verifier_and_is_single_use(settings, engine):
    from dayloom.access.oidc import token_hash

    with account_client(settings, engine) as client:
        issue_account(engine, settings, "native-owner")
        verifier, ticket = "a" * 43, "b" * 48
        routes = AccountRoutes(settings, engine)
        with Session(engine) as session:
            identity = session.scalar(select(AccountIdentity))
            session.add(
                LoginFlow(
                    id=token_hash(ticket),
                    payload=routes.vault().seal(
                        {"identity_id": identity.id, "challenge": challenge(verifier)},
                        "native-handoff",
                    ),
                    expires_at=time.time() + 60,
                )
            )
            session.commit()
        assert (
            client.post(
                "/api/auth/exchange", json={"ticket": ticket, "verifier": "x" * 43}
            ).status_code
            == 401
        )
        result = client.post("/api/auth/exchange", json={"ticket": ticket, "verifier": verifier})
        assert result.status_code == 200
        assert (
            client.post(
                "/api/auth/exchange", json={"ticket": ticket, "verifier": verifier}
            ).status_code
            == 401
        )
        with Session(engine) as session:
            hashes = session.scalars(select(AccountSession.access_hash)).all()
            assert result.json()["access_token"] not in hashes


@pytest.mark.parametrize("valid_nonce", [True, False])
def test_oidc_authorization_code_flow_checks_signed_identity(
    settings, engine, monkeypatch, valid_nonce
):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_key.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
    protocol = {}
    original_init = httpx.AsyncClient.__init__

    def provider(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": settings.oidc_issuer,
                    "authorization_endpoint": "https://identity.example/authorize",
                    "token_endpoint": "https://identity.example/token",
                    "jwks_uri": "https://identity.example/jwks",
                },
            )
        if request.url.path == "/jwks":
            return httpx.Response(200, json={"keys": [public_key]})
        assert request.url.path == "/token"
        form = parse_qs(request.content.decode())
        assert challenge(form["code_verifier"][0]) == protocol["code_challenge"]
        token = jwt.encode(
            {
                "sub": "signed-subject",
                "iss": settings.oidc_issuer,
                "aud": settings.oidc_client_id,
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
                "nonce": protocol["nonce"] if valid_nonce else "wrong-nonce",
                "name": "Signed identity",
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        return httpx.Response(
            200,
            json={
                "access_token": "unused-provider-access",
                "token_type": "Bearer",
                "id_token": token,
            },
        )

    transport = httpx.MockTransport(provider)

    def initialize_client(instance, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(instance, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", initialize_client)
    with account_client(settings, engine) as client:
        start = client.get("/api/auth/start", follow_redirects=False)
        assert start.status_code == 302
        protocol.update(
            {
                key: values[0]
                for key, values in parse_qs(urlsplit(start.headers["location"]).query).items()
            }
        )
        assert protocol["code_challenge_method"] == "S256"
        callback = client.get(
            "/api/auth/callback",
            params={"state": protocol["state"], "code": "authorized-code"},
            follow_redirects=False,
        )
        assert callback.status_code == (302 if valid_nonce else 401)
        if valid_nonce:
            account = client.get("/api/auth/me").json()
            assert account["name"] == "Signed identity"
            assert account["workspace_id"] != "00000000-0000-0000-0000-000000000000"
            assert client.get("/api/settings").json()["provider"]["configured"] is False
            assert (
                client.post(
                    "/api/chat",
                    headers={"X-Dayloom-CSRF": "1"},
                    json={"content": "Hello", "allow_external": True},
                ).status_code
                == 409
            )
        else:
            with Session(engine) as session:
                assert session.scalars(select(AccountIdentity)).all() == []


def test_production_settings_reject_legacy_access():
    from dayloom.config import Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Production requires OIDC"):
        Settings(production=True, _env_file=None)
