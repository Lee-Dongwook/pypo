from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .node import (
    chunk_context_retriever,
    full_context_extractor,
    full_context_retriever,
    search_insight,
)
from .state import SearchInput, SearchSubgraphOutput, SearchSubgraphState

SearchSubgraph = CompiledStateGraph[SearchSubgraphState, None, SearchInput, SearchSubgraphOutput]


def create_search_subgraph() -> SearchSubgraph:
    """Compile the full-text search subgraph.

    Routing is done with ``Command`` from each node, so only the entry point and
    the terminal edge are declared statically. Retrieval failures and empty
    result sets short-circuit to ``END`` from ``chunk_context_retriever``.
    """
    subgraph = StateGraph(
        SearchSubgraphState,
        input_schema=SearchInput,
        output_schema=SearchSubgraphOutput,
    )

    subgraph.add_node("full_context_extractor", full_context_extractor)
    subgraph.add_node("full_context_retriever", full_context_retriever)
    subgraph.add_node("chunk_context_retriever", chunk_context_retriever)
    subgraph.add_node("search_insight", search_insight)

    subgraph.add_edge(START, "full_context_extractor")
    subgraph.add_edge("search_insight", END)

    return subgraph.compile(name="search_subgraph")


search_subgraph = create_search_subgraph()

__all__ = ["SearchSubgraph", "create_search_subgraph", "search_subgraph"]
