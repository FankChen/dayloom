FROM node:24-bookworm-slim AS web
WORKDIR /build
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.10.8 /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONPATH=/app/backend UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ backend/
COPY --from=web /build/dist apps/web/dist
RUN useradd --uid 10001 --create-home dayloom && mkdir -p /app/data && chown -R dayloom:dayloom /app
USER dayloom
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "dayloom.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]