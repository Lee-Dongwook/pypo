from typing import Any

from langchain_core.messages import AIMessage, ChatMessage
from langchain_core.runnables import RunnableConfig

from ..state import SearchSubgraphState
from .utils import format_search_results

async def search_insight(state: SearchSubgraphState, config: RunnableConfig) -> dict[str, Any]:
        context_query = state.get("context_query", "")
        search_results = state.get("search_results") or []

        formatted_results = format_search_results(search_results)

        return {
        "messages": [
            ChatMessage(
                role="assistant",
                content=formatted_results,
                name="search_subgraph",
            ),
            AIMessage(
                content=context_query,
                additional_kwargs={"search_results": search_results},
                name="search_subgraph",
            ),
        ],
            "structured_response": {"search_results": search_results},
        }
