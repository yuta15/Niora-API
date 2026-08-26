# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.9.22-python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


FROM python:3.14-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src /app/src

USER app

EXPOSE 8000

CMD ["fastapi", "run", "src/api/main.py", "--host", "0.0.0.0", "--port", "8000"]
