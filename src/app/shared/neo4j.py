from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Iterator

from neo4j import Driver, GraphDatabase, Session

from .settings import settings

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


@contextmanager
def get_session() -> Iterator[Session]:
    driver = get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()

@asynccontextmanager
async def get_context_neo4j_session() -> AsyncGenerator[AsyncTransaction]:
    if graph_driver is None:
        initialize_neo4j()
    
    driver = cast("AsyncDriver", graph_driver)
    async with driver.session(database=graph_database) as session:
        tx = await session.begin_transaction()

        try:
            yield tx
            await tx.commit()
        except Exception:
            await tx.rollback()
            raise
        finally:
            await tx.close()


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
