import logging

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_postgres import PGEngine
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

vector_store: VectorStore | None = None

async def init_vector_store(
    async_engine: AsyncEngine,
    embeddings: Embeddings,
) -> VectorStore:
    vector = await embeddings.aembed_documents(["a"])
    logger.info(f"VECTOR SIZE is {len(vector[0])}")

    if vector and len(vector[0]) > 0:
        vector_size = len(vector[0])
    else:
        raise RuntimeError("Failed to compute embedding vector.")
    
    if vector_size < 768:
        raise ValueError(
            "vector size isn't enough"
        )
    
    pg_engine = PGEngine.from_engine(engine=async_engine)
    # WIP

async def initialize_vector_store(db_uri: str, engine: AsyncEngine | None = None) -> VectorStore:
    global vector_store

    if vector_store is not None:
        return vector_store
    
    if engine is not None:
        async_engine = engine
    else:
        ASYNC_DB_URI = db_uri.replace("postgresql://", "postgresql+psycopg_async://")
        
    
