"""Database engine, session factory, and declarative base.

SQLAlchemy 2.0 style: a typed DeclarativeBase that all models inherit from.
The engine uses psycopg 3 (the `postgresql+psycopg://` URL in config). We use a
synchronous engine for the MVP — simpler to reason about, and fine at ~20
operators; can move to async later without touching the models.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
