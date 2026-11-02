from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from dayloom.db import LEGACY_WORKSPACE_ID, ModelConnection, ModelUsage
from dayloom.registry import providers
from dayloom.secrets import SecretVault


def validate_model_endpoint(url, settings):
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            422, "Use an HTTPS provider endpoint without credentials or query parameters"
        )
    if origin not in settings.model_allowed_origins:
        raise HTTPException(422, "This provider origin is not approved by the server administrator")
    return url.rstrip("/")


def model_connection(session):
    return session.scalar(select(ModelConnection))


def model_status(session, settings):
    stored = model_connection(session)
    if stored:
        day = datetime.now(UTC).date().isoformat()
        usage = session.get(ModelUsage, day)
        return {
            "name": stored.provider,
            "label": providers.classes[stored.provider].label,
            "external": True,
            "model": stored.model,
            "configured": True,
            "managed": "workspace",
            "base_url": stored.base_url,
            "max_tokens": stored.max_tokens,
            "daily_limit": stored.daily_limit,
            "used_today": usage.requests if usage else 0,
            "version": stored.version,
        }
    if session.workspace_id != LEGACY_WORKSPACE_ID:
        return {
            "name": None,
            "label": "Connect a model",
            "external": True,
            "model": None,
            "configured": False,
            "managed": "workspace",
        }
    provider = providers.classes[settings.model_provider]
    return {
        "name": settings.model_provider,
        "label": provider.label,
        "external": provider.external,
        "model": settings.model_name if provider.external else None,
        "configured": not provider.external or bool(settings.model_api_key.get_secret_value()),
        "managed": "server",
    }


def resolve_model(session, settings):
    stored = model_connection(session)
    if not stored:
        if session.workspace_id != LEGACY_WORKSPACE_ID:
            raise HTTPException(
                409, "Connect your model API in Settings before starting a conversation"
            )
        if (
            providers.classes[settings.model_provider].external
            and not settings.model_api_key.get_secret_value()
        ):
            raise HTTPException(
                409, "Connect your model API in Settings before starting a conversation"
            )
        return settings
    validate_model_endpoint(stored.base_url, settings)
    purpose = f"model:{stored.workspace_id}:{stored.id}:{stored.provider}:{stored.base_url}"
    key = SecretVault(settings).open(stored.secret, purpose)["api_key"]
    return settings.model_copy(
        update={
            "model_provider": stored.provider,
            "model_base_url": stored.base_url,
            "model_name": stored.model,
            "model_api_key": SecretStr(key),
            "model_max_tokens": stored.max_tokens,
        }
    )


def reserve_model_request(session):
    stored = model_connection(session)
    if not stored:
        return
    daily_limit = stored.daily_limit
    day = datetime.now(UTC).date().isoformat()
    if session.get(ModelUsage, day) is None:
        session.add(ModelUsage(day=day, requests=0))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
    changed = session.execute(
        update(ModelUsage)
        .where(ModelUsage.day == day, ModelUsage.requests < daily_limit)
        .values(requests=ModelUsage.requests + 1)
    )
    session.commit()
    if changed.rowcount != 1:
        raise HTTPException(429, "Daily model request limit reached")
