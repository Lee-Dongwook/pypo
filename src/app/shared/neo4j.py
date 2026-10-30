from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession, Driver, GraphDatabase, Session

from .settings import settings

_driver: Driver | None = None
_async_driver: AsyncDriver | None = None


def _auth() -> tuple[str, str]:
    return (settings.neo4j_user, settings.neo4j_password)


def get_driver() -> Driver:
    """Return the shared synchronous driver used by the projection code."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(settings.neo4j_uri, auth=_auth())
    return _driver


def get_async_driver() -> AsyncDriver:
    """Return the shared asynchronous driver used by the agent runtime."""
    global _async_driver
    if _async_driver is None:
        _async_driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=_auth())
    return _async_driver


@contextmanager
def get_session() -> Iterator[Session]:
    driver = get_driver()
    session = driver.session(database=settings.neo4j_database)
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    driver = get_async_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        yield session


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


async def close_async_driver() -> None:
    global _async_driver
    if _async_driver is not None:
        await _async_driver.close()
        _async_driver = None


__all__ = [
    "close_async_driver",
    "close_driver",
    "get_async_driver",
    "get_async_session",
    "get_driver",
    "get_session",
]
