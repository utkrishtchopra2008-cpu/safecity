FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml ./
COPY alembic.ini ./
COPY migrations/ ./migrations/

RUN pip install --no-cache-dir uv==0.12.17 \
    && uv sync --no-dev --no-install-project

COPY app/ ./app/
RUN useradd --create-home --uid 10001 safecity \
    && chown -R safecity:safecity /app
USER safecity

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
