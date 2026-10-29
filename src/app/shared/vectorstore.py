import logging

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

vector_store: VectorStore | None = None

_NOT_IMPLEMENTED = (
    "Vector store backend is not wired yet. langchain-postgres 0.0.x requires "
    "langchain-core<0.4 and pgvector<0.4, which conflicts with the current pins; "
    "choose the backend before implementing."
)


async def init_vector_store(
    async_engine: AsyncEngine,
    embeddings: Embeddings,
) -> VectorStore:
    vector = await embeddings.aembed_documents(["a"])
    vector_size = len(vector[0]) if vector and vector[0] else 0
    logger.info(f"VECTOR SIZE is {vector_size}")

    if vector_size == 0:
        raise RuntimeError("Failed to compute embedding vector.")

    if vector_size < 768:
        raise ValueError("vector size isn't enough")

    # NOTE: needs an AsyncEngine and the pgvector extension. The PGEngine binding
    # is intentionally left out until the backend dependency conflict is resolved.
    raise NotImplementedError(_NOT_IMPLEMENTED)


async def initialize_vector_store(db_uri: str, engine: AsyncEngine | None = None) -> VectorStore:
    global vector_store

    if vector_store is not None:
        return vector_store

    raise NotImplementedError(_NOT_IMPLEMENTED)
