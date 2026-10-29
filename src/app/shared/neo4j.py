from contextlib import contextmanager
from typing import Iterator

from neo4j import Driver, GraphDatabase, Session

from .settings import settings

_driver: Driver | None = None

def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_uri, settings.neo4j_password),
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

def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        
