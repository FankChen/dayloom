import asyncio
import hashlib
import os
import platform
import secrets
import tempfile
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import uvicorn
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.datastructures import Headers
from starlette.responses import JSONResponse


class ApprovedSoftware(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(max_length=2000)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$")
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

    @field_validator("url")
    @classmethod
    def https_source(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Approved software requires a direct HTTPS source without credentials")
        return value


class DeviceServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAYLOOM_DEVICE_", env_file=".env", extra="ignore")
    token: SecretStr = Field(min_length=32, max_length=4096)
    port: int = Field(default=19888, ge=1024, le=65535)
    allowed_origins: list[str] = []
    download_dir: Path = Path.home() / "Downloads" / "Dayloom"
    max_download_bytes: int = Field(default=200000000, ge=1, le=500000000)
    download_timeout_seconds: float = Field(default=45, gt=0, le=50)
    software: dict[str, ApprovedSoftware] = {}


class DeviceTokenAuth:
    def __init__(self, app, token):
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not secrets.compare_digest(
            Headers(scope=scope).get("authorization", "").encode("utf-8"), self.expected
        ):
            await JSONResponse({"error": "Device authorization required"}, status_code=401)(
                scope, receive, send
            )
            return
        await self.app(scope, receive, send)


def open_approved_url(settings, url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only approved HTTPS websites can be opened")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in settings.allowed_origins:
        raise ValueError("This website is not approved on this device")
    if not webbrowser.open(url, new=2, autoraise=True):
        raise RuntimeError("No browser accepted the request on this device")
    return {
        "status": "opened",
        "url": url,
        "device_os": platform.system(),
        "purchase_completed": False,
        "payment_completed": False,
    }


async def download_approved_software(settings, software_id):
    approved = settings.software.get(software_id)
    if not approved:
        raise ValueError("This software is not in the device's approved download catalog")
    directory = settings.download_dir.expanduser().resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = directory / approved.filename
    if target.exists() or target.is_symlink():
        raise ValueError(
            "The destination already exists. Review the existing file before downloading again."
        )
    descriptor, temporary = tempfile.mkstemp(prefix=".dayloom-", dir=directory)
    digest = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(descriptor, "wb") as output:
            async with (
                asyncio.timeout(settings.download_timeout_seconds),
                httpx.AsyncClient(
                    timeout=httpx.Timeout(10, connect=5),
                    follow_redirects=False,
                    verify=True,
                    headers={"Accept-Encoding": "identity"},
                ) as client,
            ):
                async with client.stream("GET", approved.url) as response:
                    response.raise_for_status()
                    if (
                        int(response.headers.get("content-length", "0"))
                        > settings.max_download_bytes
                    ):
                        raise ValueError("Software download exceeds the device size limit")
                    async for chunk in response.aiter_raw():
                        total += len(chunk)
                        if total > settings.max_download_bytes:
                            raise ValueError("Software download exceeded its size limit")
                        digest.update(chunk)
                        output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if not secrets.compare_digest(digest.hexdigest(), approved.sha256.lower()):
            raise ValueError("Software checksum mismatch. The file was discarded.")
        os.link(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {
        "status": "downloaded",
        "path": str(target),
        "sha256": digest.hexdigest(),
        "bytes": total,
        "installed": False,
        "executed": False,
        "device_os": platform.system(),
    }


def create_device_app(settings):
    server = FastMCP(
        "Dayloom device tools",
        instructions="Tools run on the computer hosting this service. Opening a website is a handoff, not a purchase. Downloads are curated, hash-checked and never installed or executed.",
        host="127.0.0.1",
        port=settings.port,
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[f"127.0.0.1:{settings.port}", f"localhost:{settings.port}"],
            allowed_origins=[
                f"http://127.0.0.1:{settings.port}",
                f"http://localhost:{settings.port}",
            ],
        ),
    )

    def action_reference(context):
        meta = context.request_context.meta
        value = meta.model_dump().get("io.dayloom/action_id") if meta else None
        if not value:
            raise ValueError("A Dayloom approved action reference is required")
        return str(UUID(value))

    @server.tool(
        description="Inspect this computer's operating system, permitted website origins and approved software download catalog. Does not operate applications."
    )
    def device_info() -> dict[str, Any]:
        return {
            "device_os": platform.system(),
            "allowed_origins": settings.allowed_origins,
            "software": [
                {"id": name, "title": item.title, "sha256": item.sha256}
                for name, item in settings.software.items()
            ],
            "capabilities": ["open_url", "download_software"],
            "automatic_purchase": False,
            "automatic_install": False,
        }

    @server.tool(
        description="Open an HTTPS URL only on a device-approved origin in this computer's browser. Login, booking, checkout and payment remain with the user."
    )
    def open_url(url: str, ctx: Context) -> dict[str, Any]:
        reference = action_reference(ctx)
        return {**open_approved_url(settings, url), "action_id": reference}

    @server.tool(
        description="Download one software_id from device_info's approved catalog to this computer, check its pinned SHA-256 and refuse redirects or overwriting. Never install or execute the file."
    )
    async def download_software(software_id: str, ctx: Context) -> dict[str, Any]:
        reference = action_reference(ctx)
        return {**await download_approved_software(settings, software_id), "action_id": reference}

    app = server.streamable_http_app()
    app.add_middleware(DeviceTokenAuth, token=settings.token.get_secret_value())
    return app


def main():
    settings = DeviceServerSettings()
    uvicorn.run(create_device_app(settings), host="127.0.0.1", port=settings.port, access_log=False)


if __name__ == "__main__":
    main()
