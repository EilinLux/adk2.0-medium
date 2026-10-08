# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation at build time and place .venv/bin on PATH
# so container startup invokes python/uvicorn directly with zero `uv run` cold-start overhead.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080 \
    SERVICE_ROLE=runner

# 1. Install dependencies first for optimal Docker layer caching
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. Copy application packages and entrypoint script
COPY adk_agent_app ./adk_agent_app
COPY adk_agent_app_suggeritore ./adk_agent_app_suggeritore
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# Install the local packages into the virtual environment
RUN uv sync --frozen --no-dev && chmod +x ./docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["./docker-entrypoint.sh"]
