from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from src.app.engine.search.node import chunk_context_retriever, full_context_retriever, search_insight, full_context_extractor
from src.app.engine.state import GraphConfig

from .state import SearchSubgraphState, SearchInput, SearchSubgraphOutput


def create_search_subgraph() -> CompiledStateGraph[Any, Any]:
    subgraph = StateGraph(
        SearchSubgraphState,
        GraphConfig,
        input_schema=SearchInput,
        output_schema=SearchSubgraphOutput,
    )

    subgraph.add_edge(START, "full_context_extractor")
    subgraph.add_node("full_context_extractor", full_context_extractor)
    subgraph.add_node("full_context_retriever", full_context_retriever)
    subgraph.add_node("chunk_context_retriever", chunk_context_retriever)
    subgraph.add_node("search_insight", search_insight)

    subgraph.add_edge("search_insight", END)

    return subgraph.complie(name="search_subgraph")

search_subgraph = create_search_subgraph()
