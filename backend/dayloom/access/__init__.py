from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    workspace_id: str
    identity_id: str | None = None
    session_id: str | None = None
    name: str = "Local workspace"


PUBLIC_AUTH_PATHS = frozenset(
    {
        "/api/health",
        "/api/auth/config",
        "/api/auth/start",
        "/api/auth/callback",
        "/api/auth/refresh",
        "/api/auth/exchange",
    }
)
