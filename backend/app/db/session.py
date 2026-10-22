"""Request-scoped SQLAlchemy sessions."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)


def get_db() -> Generator[OrmSession, None, None]:
    """Provide one short-lived database session per HTTP request."""
    try:
        engine = get_engine()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Database is not configured") from exc
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
