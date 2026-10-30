from typing import Any, Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from ..state import SearchSubgraphState

async def chunk_context_retriever(
    state: SearchSubgraphState, config: RunnableConfig,
) -> Command[Literal["search)_insight", END]]:
    if state.get("retrieval_failed"):
        return Command(
            goto=END,
            update={"messages": [AIMessage(content="검색 중 문제가 생겨 자료를 찾지 못했습니다.")]},
        )
    
    retrieval_results: list[dict[str, Any]] = state.get("retrieval_results") or []
    if not retrieval_results:
        return Command(
            goto=END,
            update={
                "messages": [AIMessage(content="해당 검색어로는 자료를 찾지 못했습니다. 검색어를 다르게 입력하시기 바랍니다.")]
            },
        )
    
    search_results = []
    seen_node_ids = set()
    for record in retrieval_results:
        node_id = record.get("node_id")
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        search_results.append(
            {
                "url": record.get("url"),
                "title": record.get("title", "No Title"),
                "description": record.get("description", ""),
                "score": record.get("score"),
                "tags": record.get("tags"),
                "created_at": record.get("created_at"),
            }
        )

        return Command(
            goto="search_insight", update={"context_query": "관련된 자료를 찾았습니다.", "search_results": search_results}
        )
