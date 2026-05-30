FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ARG ENV_TYPE=DEVELOPMENT
ENV ENV_TYPE=${ENV_TYPE}

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY src ./src

WORKDIR /app/src

ENTRYPOINT ["/app/.venv/bin/python", "app.py"]