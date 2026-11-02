from dayloom.registry import routers
from dayloom.tools.read_web_page import ReadWebPage
from fastapi import APIRouter


@routers.register
class BrowserRoutes:
    def __init__(self, settings):
        self.settings = settings

    def install(self, app):
        router = APIRouter(prefix="/api/browser", tags=["browser"])

        @router.get("/config")
        def configuration():
            return {
                "enabled": ReadWebPage.available(self.settings),
                "allowed_origins": self.settings.browser_allowed_origins,
                "capabilities": ["public_page_read"],
            }

        app.include_router(router)
