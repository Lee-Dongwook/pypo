import asyncio

import pytest

import src.app.shared.vectorstore as vectorstore


class _FakeEmbeddings:
    def __init__(self, size: int) -> None:
        self.size = size

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.size for _ in texts]


def test_module_imports_without_optional_backend() -> None:
    # Regression: the module used to import langchain_postgres at import time, which
    # is not installable with the current langchain-core/pgvector pins.
    assert vectorstore.vector_store is None


def test_initialize_vector_store_is_loud_about_the_missing_backend() -> None:
    with pytest.raises(NotImplementedError, match="langchain-postgres"):
        asyncio.run(vectorstore.initialize_vector_store("postgresql://localhost/pypo"))


def test_too_small_vectors_are_rejected() -> None:
    with pytest.raises(ValueError, match="vector size"):
        asyncio.run(vectorstore.init_vector_store(None, _FakeEmbeddings(3)))


def test_backend_is_not_wired_yet() -> None:
    with pytest.raises(NotImplementedError, match="langchain-postgres"):
        asyncio.run(vectorstore.init_vector_store(None, _FakeEmbeddings(768)))
