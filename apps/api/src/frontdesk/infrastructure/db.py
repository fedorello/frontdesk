"""Async SQLAlchemy engine and session factory for the Postgres adapters."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for the ORM models."""


def create_engine(database_url: str) -> AsyncEngine:
    """An async engine for ``postgresql+asyncpg://…`` URLs."""
    return create_async_engine(database_url, pool_pre_ping=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """A session factory that keeps attributes usable after commit."""
    return async_sessionmaker(engine, expire_on_commit=False)
