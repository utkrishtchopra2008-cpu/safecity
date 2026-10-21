"""SQLAlchemy declarative base for future database models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models introduced with schema implementation."""
