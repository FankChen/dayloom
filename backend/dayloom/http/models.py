from dayloom.db import ModelConnection, identifier, record, timestamp
from dayloom.dependencies import get_session
from dayloom.models import (
    model_connection,
    model_status,
    reserve_model_request,
    resolve_model,
    validate_model_endpoint,
)
from dayloom.registry import providers, routers
from dayloom.secrets import SecretVault
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import delete, update


class ModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: str = Field(default="OpenAIProvider", max_length=80)
    base_url: str = Field(default="https://api.openai.com/v1", max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr = Field(min_length=1, max_length=4096)
    max_tokens: int = Field(default=2400, ge=128, le=8192)
    daily_limit: int = Field(default=100, ge=1, le=1000)
    version: int = Field(default=0, ge=0)


@routers.register
class ModelRoutes:
    def __init__(self, settings):
        self.settings = settings

    def install(self, app):
        router = APIRouter(prefix="/api/models", tags=["models"])

        @router.get("")
        def configuration(session=Depends(get_session)):
            return {
                "connection": model_status(session, self.settings),
                "allowed_origins": self.settings.model_allowed_origins,
                "providers": [
                    {"name": name, "label": providers.classes[name].label}
                    for name in self.settings.model_user_providers
                    if name in providers.classes
                ],
            }

        @router.put("")
        def configure(payload: ModelInput, session=Depends(get_session)):
            if (
                payload.provider not in self.settings.model_user_providers
                or payload.provider not in providers.classes
                or not providers.classes[payload.provider].external
            ):
                raise HTTPException(422, "This model provider is not available")
            base_url = validate_model_endpoint(payload.base_url, self.settings)
            stored = model_connection(session)
            connection_id = stored.id if stored else identifier()
            purpose = f"model:{session.workspace_id}:{connection_id}:{payload.provider}:{base_url}"
            values = {
                "provider": payload.provider,
                "base_url": base_url,
                "model": payload.model,
                "max_tokens": payload.max_tokens,
                "daily_limit": payload.daily_limit,
                "secret": SecretVault(self.settings).seal(
                    {"api_key": payload.api_key.get_secret_value()}, purpose
                ),
                "updated_at": timestamp(),
            }
            if stored:
                changed = session.execute(
                    update(ModelConnection)
                    .where(
                        ModelConnection.id == stored.id, ModelConnection.version == payload.version
                    )
                    .values(**values, version=ModelConnection.version + 1)
                )
                if changed.rowcount != 1:
                    raise HTTPException(409, "Model configuration changed; refresh before saving")
            else:
                if payload.version != 0:
                    raise HTTPException(
                        409, "Model configuration was removed; refresh before saving"
                    )
                session.add(ModelConnection(id=connection_id, **values))
            record(
                session,
                "model.configured",
                connection_id,
                provider=payload.provider,
                model=payload.model,
            )
            session.commit()
            session.expire_all()
            return model_status(session, self.settings)

        @router.delete("", status_code=204)
        def disconnect(session=Depends(get_session)):
            session.execute(delete(ModelConnection))
            record(session, "model.disconnected", "workspace")
            session.commit()

        @router.post("/test")
        async def test_connection(session=Depends(get_session)):
            if not model_connection(session):
                raise HTTPException(409, "Save a model connection first")
            configured = resolve_model(session, self.settings)
            reserve_model_request(session)
            try:
                reply = await providers.build(configured.model_provider, settings=configured).reply(
                    "Reply with a short connection confirmation and no proposed actions.",
                    {"connection_test": True},
                )
            except Exception as error:
                raise HTTPException(
                    502, "Provider connection or structured-response test failed"
                ) from error
            return {
                "connected": True,
                "model": configured.model_name,
                "message": reply.message,
                "proposals_executed": 0,
            }

        app.include_router(router)
