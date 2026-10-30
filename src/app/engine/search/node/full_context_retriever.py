import logging
import textwrap
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from neo4j.exceptions import Neo4jError

from ....shared.neo4j import get_context_neo4j_session
from ..state import SearchSubgraphState

logger = logging.getLogger(__name__)

_INDEX = (
    "CREATE FULLTEXT INDEX combindedIndex IF NOT EXISTS FOR (n:Link|Memo|File) "
    f"ON EACH [n.title, n.tags, n.description] OPTIONS {indexConfig: {repr(fulltext.analyzer): 'cjk'}}"
)

_indexed = False

async def full_context_retriever(
    state: SearchSubgraphState, config: RunnableConfig
) -> Command[Literal["chunk_context_retriever"]]:
    context_query = state.get("context_query") or ""
    user_uuid = state.get("user_uuid") or ""

    if not context_query:
        raise ValueError("state needs context_query")
    
    if not user_uuid: 
        raise ValueError("state needs user_uuid")
    
    query = textwrap.dedent("""
        CALL db.index.fulltext.queryNodes('combinedIndex', $kw) YIELD node, score
        WHERE node.user_uuid = $user_uuid
        RETURN elementId(node) AS node_id,
            node.title AS title,
            node.url AS url,
            node.description AS description,
            node.tags AS tags,
            node.created_at AS created_at,
            score
        ORDER BY score DESC
        LIMIT 5
    """)

    params = {"kw": context_query, "user_uuid": user_uuid}

    global _indexed
    if not _indexed:
        try:
            async with get_context_neo4j_session() as graph_db:
                await (await graph_db.run(_INDEX)).consume()
            _indexed = True
        except Neo4jError as err:
            _indexed = not err.is_retryable()
            logger.warning("Graph refused to create full-text index", exc_info=True)
        except Exception:
            logger.warning("Couldn't create full text index", exc_info=True)
    try:
        async with get_context_neo4j_session() as graph_db:
            result = await graph_db.run(query, params)
            results = [record.data() async for record in result]
    except Exception:
        logger.exception("Neo4j full-text search failed")
        return Command(goto="chunk_context_retriever", update={"retrieval_results": [], "retrieval_failed": True})
    
    return Command(
        goto="chunk_context_retriever",
        update={
            "retrieval_results": results,
            "retrieval_failed": False,
        }
    )
