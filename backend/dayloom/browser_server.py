import asyncio
import hmac
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from dayloom.browser_policy import allowed_page


class BrowserSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DAYLOOM_BROWSER_", extra="ignore")
    shared_token: SecretStr = Field(min_length=32)
    allowed_origins: list[str]
    egress_proxy: str = Field(min_length=1)


class ReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    workspace_id: UUID
    url: HttpUrl


async def read_page(payload, settings):
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, chromium_sandbox=True, proxy={"server": settings.egress_proxy}
        )
        try:
            context = await browser.new_context(
                accept_downloads=False,
                service_workers="block",
                permissions=[],
                java_script_enabled=False,
            )

            async def restrict(route):
                if route.request.method not in {"GET", "HEAD"} or not allowed_page(
                    route.request.url, settings.allowed_origins
                ):
                    await route.abort()
                else:
                    await route.continue_()

            await context.route("**/*", restrict)
            page = await context.new_page()
            await page.goto(str(payload.url), wait_until="domcontentloaded", timeout=30000)
            if not allowed_page(page.url, settings.allowed_origins):
                raise ValueError("Destination changed")
            return {
                "title": (await page.title())[:200],
                "url": page.url,
                "text": (await page.locator("body").inner_text(timeout=5000))[:16000],
            }
        finally:
            await browser.close()


def create_app(settings=None, reader=read_page):
    settings = settings or BrowserSettings()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    capacity = asyncio.Semaphore(2)

    @app.get("/health")
    def health():
        return {"status": "ok", "capabilities": ["public_page_read"]}

    @app.post("/read")
    async def read(payload: ReadInput, request: Request):
        expected = f"Bearer {settings.shared_token.get_secret_value()}"
        if not hmac.compare_digest(request.headers.get("authorization", ""), expected):
            raise HTTPException(401, "Browser runner authentication required")
        if not allowed_page(payload.url, settings.allowed_origins):
            raise HTTPException(403, "Origin is not approved")
        try:
            async with asyncio.timeout(45), capacity:
                result = await reader(payload, settings)
            if not allowed_page(result["url"], settings.allowed_origins):
                raise HTTPException(403, "Result origin is not approved")
            return result
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(502, "Isolated browser could not read this page") from error

    return app
