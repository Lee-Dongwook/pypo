from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .state import SearchSubgraphState, SearchInput, SearchSubgraphOutput


def create_search_subgraph() -> CompiledStateGraph[Any, Any]:
    pass
