import hashlib
import time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from dayloom.access import Principal
from dayloom.db import AccountIdentity, AccountSession
from dayloom.registry import access


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@access.register
class OidcAccess:
    mode = "oidc"

    def __init__(self, settings, engine):
        if not settings.oidc_issuer or not settings.credential_key.get_secret_value():
            raise ValueError("OIDC issuer and credential encryption key are required")
        self.engine = engine

    async def authenticate(self, request):
        supplied = request.headers.get("authorization", "")
        token = supplied.removeprefix("Bearer ") if supplied.startswith("Bearer ") else ""
        if not token:
            token = request.cookies.get("dayloom_access", "")
            if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
                if request.headers.get("x-dayloom-csrf") != "1":
                    raise HTTPException(403, "CSRF header is required")
        if not token or len(token) > 1024:
            raise HTTPException(401, "Sign in to your account")
        with Session(self.engine) as session:
            stored = session.scalar(
                select(AccountSession).where(
                    AccountSession.access_hash == token_hash(token),
                    AccountSession.access_expires_at > time.time(),
                    AccountSession.expires_at > time.time(),
                )
            )
            if not stored:
                raise HTTPException(401, "Your session has expired")
            identity = session.get(AccountIdentity, stored.identity_id)
            return Principal(identity.workspace_id, identity.id, stored.id, identity.name)
