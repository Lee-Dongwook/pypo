from __future__ import annotations

import asyncio
import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from neo4j.exceptions import Neo4jError

from src.app.shared.neo4j import get_async_session

from ..queries import CREATE_FULLTEXT_INDEX, DEFAULT_RESULT_LIMIT, FULLTEXT_SEARCH
from ..state import SearchSubgraphState

logger = logging.getLogger(__name__)

_index_lock = asyncio.Lock()
_index_ready = False


async def _ensure_fulltext_index() -> None:
    """Create the full-text index once per process.

    The index is normally created by `make neo4j-init`; this keeps a fresh
    environment working without a manual step. The lock prevents two concurrent
    searches from both issuing DDL.
    """
    global _index_ready
    if _index_ready:
        return

    async with _index_lock:
        if _index_ready:
            return
        try:
            async with get_async_session() as session:
                await (await session.run(CREATE_FULLTEXT_INDEX)).consume()
        except Neo4jError as err:
            # A permanent failure (bad syntax, missing privilege) will not fix
            # itself; keep logging it on the first search, then stop retrying.
            _index_ready = not err.is_retryable()
            logger.warning("Neo4j refused to create the full-text index", exc_info=True)
            return
        except Exception:
            logger.warning("Could not create the full-text index", exc_info=True)
            return
        _index_ready = True


async def full_context_retriever(
    state: SearchSubgraphState,
    config: RunnableConfig,
) -> Command[Literal["chunk_context_retriever"]]:
    context_query = (state.get("context_query") or "").strip()
    user_uuid = state.get("user_uuid") or ""

    if not context_query:
        raise ValueError("state needs context_query")
    if not user_uuid:
        raise ValueError("state needs user_uuid")

    await _ensure_fulltext_index()

    params = {
        "kw": context_query,
        "user_uuid": user_uuid,
        "limit": DEFAULT_RESULT_LIMIT,
    }

    try:
        async with get_async_session() as session:
            result = await session.run(FULLTEXT_SEARCH, params)
            results = [record.data() async for record in result]
    except Exception:
        logger.exception("Neo4j full-text search failed")
        return Command(
            goto="chunk_context_retriever",
            update={"retrieval_results": [], "retrieval_failed": True},
        )

    return Command(
        goto="chunk_context_retriever",
        update={"retrieval_results": results, "retrieval_failed": False},
    )


__all__ = ["full_context_retriever"]
