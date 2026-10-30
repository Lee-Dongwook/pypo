from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, ChatMessage
from langchain_core.runnables import RunnableConfig

from ..state import SearchSubgraphState
from .utils import format_search_results


async def search_insight(
    state: SearchSubgraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Emit the search results as messages and as a structured response."""
    search_results = state.get("search_results") or []
    formatted_results = format_search_results(search_results)
    summary = f"관련된 자료 {len(search_results)}건을 찾았습니다."

    return {
        "messages": [
            ChatMessage(
                role="assistant",
                content=formatted_results,
                name="search_subgraph",
            ),
            AIMessage(
                content=summary,
                additional_kwargs={"search_results": search_results},
                name="search_subgraph",
            ),
        ],
        "structured_response": {"search_results": search_results},
    }


__all__ = ["search_insight"]
