# Стадия 1: зависимости и проект через uv в .venv
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY src ./src
# README и LICENSE объявлены в pyproject — их требует uv_build
COPY README.md LICENSE ./
# --no-editable: пакет кладётся в venv целиком, а не ссылкой на src/
# (в рантайм-стадию копируется только .venv), заодно работает
# console-script `zheka`
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Стадия 2: рантайм без uv и кешей
FROM python:3.14-slim
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
COPY --from=builder /app/.venv ./.venv
# /app/infra — точка монтирования промптов (persona.txt и др.);
# .env в образ не попадает: переменные приходят из compose env_file
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --no-create-home appuser \
    && mkdir -p /app/logs /app/infra \
    && chown -R appuser:appuser /app
USER appuser
CMD ["zheka"]
