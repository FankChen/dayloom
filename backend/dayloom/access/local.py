import hmac

from fastapi import HTTPException

from dayloom.access import Principal
from dayloom.db import LEGACY_WORKSPACE_ID
from dayloom.registry import access


@access.register
class LocalAccess:
    mode = "local"

    def __init__(self, settings):
        self.settings = settings

    async def authenticate(self, request):
        token = self.settings.access_token.get_secret_value()
        if token:
            if not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {token}"):
                raise HTTPException(401, "An access token is required")
        elif not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            raise HTTPException(401, "Configure an access token for remote access")
        return Principal(LEGACY_WORKSPACE_ID)
