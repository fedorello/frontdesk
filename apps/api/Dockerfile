# Frontdesk API (and worker / migrations) — one image, three commands.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Dependencies first (cached until they change), then the project.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uvicorn", "frontdesk.interface.app:create_production_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
