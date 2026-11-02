import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from authlib.integrations.httpx_client import AsyncOAuth2Client
from dayloom.access.oidc import token_hash
from dayloom.db import AccountIdentity, AccountSession, LoginFlow, Workspace
from dayloom.registry import routers
from dayloom.secrets import SecretVault
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class RefreshInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str | None = Field(default=None, max_length=1024)


class ExchangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket: str = Field(min_length=30, max_length=200)
    verifier: str = Field(min_length=43, max_length=128)


def challenge(verifier):
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )


@routers.register
class AccountRoutes:
    def __init__(self, settings, engine):
        self.settings = settings
        self.engine = engine
        self.metadata = None

    def require_oidc(self):
        if self.settings.auth_backend != "OidcAccess":
            raise HTTPException(409, "Account login is not enabled on this server")

    def vault(self):
        return SecretVault(self.settings)

    def validate_url(self, url):
        parsed = urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username:
            return
        if (
            self.settings.oidc_allow_http
            and parsed.scheme == "http"
            and parsed.hostname in {"localhost", "127.0.0.1", "keycloak"}
        ):
            return
        raise HTTPException(503, "OIDC endpoints require HTTPS")

    async def discovery(self):
        self.require_oidc()
        if self.metadata is not None:
            return self.metadata
        issuer = self.settings.oidc_issuer.rstrip("/")
        self.validate_url(issuer)
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.get(f"{issuer}/.well-known/openid-configuration")
            response.raise_for_status()
            metadata = response.json()
        if metadata.get("issuer") != issuer:
            raise HTTPException(503, "Identity provider issuer mismatch")
        for field in ["authorization_endpoint", "token_endpoint", "jwks_uri"]:
            self.validate_url(metadata[field])
        self.metadata = metadata
        return metadata

    def new_session(self, session, identity_id, device):
        access_token, refresh_token = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
        now = time.time()
        session.add(
            AccountSession(
                identity_id=identity_id,
                access_hash=token_hash(access_token),
                refresh_hash=token_hash(refresh_token),
                access_expires_at=now + self.settings.session_seconds,
                expires_at=now + self.settings.refresh_seconds,
                device=device[:200],
            )
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.settings.session_seconds,
        }

    def set_cookies(self, response, tokens):
        secure = self.settings.public_url.startswith("https://")
        response.set_cookie(
            "dayloom_access",
            tokens["access_token"],
            httponly=True,
            secure=secure,
            samesite="lax",
            max_age=self.settings.session_seconds,
            path="/",
        )
        response.set_cookie(
            "dayloom_refresh",
            tokens["refresh_token"],
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=self.settings.refresh_seconds,
            path="/api/auth",
        )

    def install(self, app):
        router = APIRouter(prefix="/api/auth", tags=["accounts"])

        @router.get("/config")
        def configuration():
            return {
                "mode": app.state.access.mode,
                "login_url": f"{self.settings.public_url.rstrip('/')}/api/auth/start",
            }

        @router.get("/start")
        async def start(request: Request, native_challenge: str | None = None):
            metadata = await self.discovery()
            if native_challenge is not None and (
                len(native_challenge) != 43
                or not all(
                    character.isalnum() or character in "-_" for character in native_challenge
                )
            ):
                raise HTTPException(422, "Invalid native login challenge")
            state, nonce, verifier = (
                secrets.token_urlsafe(32),
                secrets.token_urlsafe(32),
                secrets.token_urlsafe(48),
            )
            with Session(self.engine) as session:
                session.execute(delete(LoginFlow).where(LoginFlow.expires_at < time.time()))
                if session.scalar(select(func.count()).select_from(LoginFlow)) > 1000:
                    raise HTTPException(429, "Too many pending login requests")
                session.add(
                    LoginFlow(
                        id=token_hash(state),
                        payload=self.vault().seal(
                            {
                                "nonce": nonce,
                                "verifier": verifier,
                                "native_challenge": native_challenge,
                            },
                            "oidc-flow",
                        ),
                        expires_at=time.time() + 600,
                    )
                )
                session.commit()
            client = AsyncOAuth2Client(
                self.settings.oidc_client_id,
                redirect_uri=f"{self.settings.public_url.rstrip('/')}/api/auth/callback",
                scope="openid profile email",
                code_challenge_method="S256",
            )
            url, _state = client.create_authorization_url(
                metadata["authorization_endpoint"], state=state, nonce=nonce, code_verifier=verifier
            )
            await client.aclose()
            response = RedirectResponse(url, status_code=302)
            response.set_cookie(
                "dayloom_login",
                state,
                httponly=True,
                secure=self.settings.public_url.startswith("https://"),
                samesite="lax",
                max_age=600,
                path="/api/auth",
            )
            return response

        @router.get("/callback")
        async def callback(request: Request, state: str = "", code: str = ""):
            self.require_oidc()
            cookie = request.cookies.get("dayloom_login", "")
            if not state or not cookie or not hmac.compare_digest(state, cookie) or not code:
                raise HTTPException(400, "Login state is missing or invalid")
            with Session(self.engine) as session:
                flow = session.get(LoginFlow, token_hash(state))
                if not flow or flow.expires_at <= time.time():
                    raise HTTPException(400, "Login request expired")
                payload = self.vault().open(flow.payload, "oidc-flow")
                removed = session.execute(delete(LoginFlow).where(LoginFlow.id == flow.id))
                session.commit()
                if removed.rowcount != 1:
                    raise HTTPException(409, "Login request was already consumed")
            try:
                metadata = await self.discovery()
                secret = self.settings.oidc_client_secret.get_secret_value()
                async with AsyncOAuth2Client(
                    self.settings.oidc_client_id,
                    client_secret=secret or None,
                    token_endpoint_auth_method="client_secret_post" if secret else "none",
                    timeout=15,
                    follow_redirects=False,
                ) as client:
                    tokens = await client.fetch_token(
                        metadata["token_endpoint"],
                        code=code,
                        grant_type="authorization_code",
                        code_verifier=payload["verifier"],
                        redirect_uri=f"{self.settings.public_url.rstrip('/')}/api/auth/callback",
                    )
                async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                    key_response = await client.get(metadata["jwks_uri"])
                    key_response.raise_for_status()
                    keys = key_response.json()["keys"]
                header = jwt.get_unverified_header(tokens["id_token"])
                if header.get("alg") not in {"RS256", "ES256"}:
                    raise ValueError("Unsupported signing algorithm")
                key = next(
                    value
                    for value in keys
                    if value.get("kid") == header.get("kid") and value.get("use", "sig") == "sig"
                )
                claims = jwt.decode(
                    tokens["id_token"],
                    jwt.PyJWK.from_dict(key).key,
                    algorithms=[header["alg"]],
                    issuer=metadata["issuer"],
                    audience=self.settings.oidc_client_id,
                    options={"require": ["exp", "iat", "sub", "iss", "aud"]},
                    leeway=30,
                )
                if not hmac.compare_digest(str(claims.get("nonce", "")), payload["nonce"]):
                    raise ValueError("Nonce mismatch")
                if claims.get("azp", self.settings.oidc_client_id) != self.settings.oidc_client_id:
                    raise ValueError("Authorized party mismatch")
                if (
                    isinstance(claims["aud"], list)
                    and len(claims["aud"]) > 1
                    and claims.get("azp") != self.settings.oidc_client_id
                ):
                    raise ValueError("Authorized party mismatch")
            except Exception as error:
                raise HTTPException(
                    401, "Identity verification failed; please sign in again"
                ) from error
            with Session(self.engine) as session:
                identity = session.scalar(
                    select(AccountIdentity).where(
                        AccountIdentity.issuer == claims["iss"],
                        AccountIdentity.subject == claims["sub"],
                    )
                )
                if identity is None:
                    workspace = Workspace(
                        name=str(claims.get("name") or "Personal workspace")[:200]
                    )
                    session.add(workspace)
                    session.flush()
                    identity = AccountIdentity(
                        issuer=claims["iss"],
                        subject=claims["sub"],
                        workspace_id=workspace.id,
                        name=workspace.name,
                    )
                    session.add(identity)
                    try:
                        session.flush()
                    except IntegrityError:
                        session.rollback()
                        identity = session.scalar(
                            select(AccountIdentity).where(
                                AccountIdentity.issuer == claims["iss"],
                                AccountIdentity.subject == claims["sub"],
                            )
                        )
                if payload["native_challenge"]:
                    ticket = secrets.token_urlsafe(48)
                    session.add(
                        LoginFlow(
                            id=token_hash(ticket),
                            payload=self.vault().seal(
                                {
                                    "identity_id": identity.id,
                                    "challenge": payload["native_challenge"],
                                },
                                "native-handoff",
                            ),
                            expires_at=time.time() + 60,
                        )
                    )
                    response = RedirectResponse(
                        f"{self.settings.native_callback_url}?{urlencode({'ticket': ticket})}",
                        status_code=302,
                    )
                else:
                    issued = self.new_session(
                        session, identity.id, request.headers.get("user-agent", "Browser")
                    )
                    response = RedirectResponse(
                        f"{self.settings.public_url.rstrip('/')}/today", status_code=302
                    )
                    self.set_cookies(response, issued)
                session.commit()
            response.delete_cookie("dayloom_login", path="/api/auth")
            return response

        @router.post("/exchange")
        def exchange(payload: ExchangeInput, request: Request):
            self.require_oidc()
            with Session(self.engine) as session:
                flow = session.get(LoginFlow, token_hash(payload.ticket))
                if not flow or flow.expires_at <= time.time():
                    raise HTTPException(401, "Native login ticket expired")
                data = self.vault().open(flow.payload, "native-handoff")
                if not hmac.compare_digest(challenge(payload.verifier), data["challenge"]):
                    raise HTTPException(401, "Native login verification failed")
                removed = session.execute(delete(LoginFlow).where(LoginFlow.id == flow.id))
                if removed.rowcount != 1:
                    raise HTTPException(409, "Native login ticket was already consumed")
                issued = self.new_session(
                    session, data["identity_id"], request.headers.get("user-agent", "Mobile device")
                )
                session.commit()
                return issued

        @router.post("/refresh")
        def refresh(payload: RefreshInput, request: Request):
            self.require_oidc()
            native = payload.refresh_token is not None
            if not native and request.headers.get("x-dayloom-csrf") != "1":
                raise HTTPException(403, "CSRF header is required")
            token = payload.refresh_token or request.cookies.get("dayloom_refresh", "")
            with Session(self.engine) as session:
                stored = session.scalar(
                    select(AccountSession).where(
                        AccountSession.refresh_hash == token_hash(token),
                        AccountSession.expires_at > time.time(),
                    )
                )
                if not stored:
                    raise HTTPException(401, "Sign in again")
                access_token, refresh_token = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
                changed = session.execute(
                    update(AccountSession)
                    .where(
                        AccountSession.id == stored.id,
                        AccountSession.refresh_hash == token_hash(token),
                    )
                    .values(
                        access_hash=token_hash(access_token),
                        refresh_hash=token_hash(refresh_token),
                        access_expires_at=time.time() + self.settings.session_seconds,
                    )
                )
                if changed.rowcount != 1:
                    raise HTTPException(401, "Refresh token was already used")
                session.commit()
            issued = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": self.settings.session_seconds,
            }
            response = JSONResponse(issued if native else {"refreshed": True})
            if not native:
                self.set_cookies(response, issued)
            return response

        @router.get("/me")
        def current_account(request: Request):
            principal = request.state.principal
            return {
                "mode": app.state.access.mode,
                "name": principal.name,
                "workspace_id": principal.workspace_id,
                "session_id": principal.session_id,
            }

        @router.get("/sessions")
        def sessions(request: Request):
            self.require_oidc()
            with Session(self.engine) as session:
                return [
                    {
                        "id": stored.id,
                        "device": stored.device,
                        "created_at": stored.created_at,
                        "expires_at": stored.expires_at,
                        "current": stored.id == request.state.principal.session_id,
                    }
                    for stored in session.scalars(
                        select(AccountSession).where(
                            AccountSession.identity_id == request.state.principal.identity_id,
                            AccountSession.expires_at > time.time(),
                        )
                    )
                ]

        @router.delete("/sessions/{session_id}", status_code=204)
        def revoke(session_id: str, request: Request):
            self.require_oidc()
            with Session(self.engine) as session:
                session.execute(
                    delete(AccountSession).where(
                        AccountSession.id == session_id,
                        AccountSession.identity_id == request.state.principal.identity_id,
                    )
                )
                session.commit()

        @router.post("/logout")
        def logout(request: Request):
            with Session(self.engine) as session:
                session.execute(
                    delete(AccountSession).where(
                        AccountSession.id == request.state.principal.session_id
                    )
                )
                session.commit()
            response = JSONResponse({"signed_out": True})
            response.delete_cookie("dayloom_access", path="/")
            response.delete_cookie("dayloom_refresh", path="/api/auth")
            return response

        app.include_router(router)
