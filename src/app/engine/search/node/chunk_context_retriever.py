from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from ..state import SearchSubgraphState
from .utils import normalize_search_results

_FAILED_MESSAGE = "검색 중 문제가 생겨 자료를 찾지 못했습니다."
_EMPTY_MESSAGE = "해당 검색어로는 자료를 찾지 못했습니다. 검색어를 다르게 입력하시기 바랍니다."


def _stop(message: str) -> Command[Literal["__end__"]]:
    return Command(
        goto=END,
        update={
            "messages": [AIMessage(content=message, name="search_subgraph")],
            "search_results": [],
            "structured_response": {"search_results": []},
        },
    )


async def chunk_context_retriever(
    state: SearchSubgraphState,
    config: RunnableConfig,
) -> Command[Literal["search_insight", "__end__"]]:
    """Normalize full-text hits and decide whether the insight node can run."""
    if state.get("retrieval_failed"):
        return _stop(_FAILED_MESSAGE)

    search_results: list[dict[str, Any]] = normalize_search_results(state.get("retrieval_results") or [])
    if not search_results:
        return _stop(_EMPTY_MESSAGE)

    return Command(
        goto="search_insight",
        update={"search_results": search_results},
    )


__all__ = ["chunk_context_retriever"]
