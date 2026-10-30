from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from src.app.engine.search.agent import create_search_subgraph, search_subgraph
from src.app.engine.search.node import chunk_context_retriever, search_insight
from src.app.engine.search.node.full_context_extractor import full_context_extractor
from src.app.engine.search.node.utils import normalize_search_results
from src.app.engine.search.queries import CREATE_FULLTEXT_INDEX, escape_lucene


def test_subgraph_compiles_with_expected_nodes() -> None:
    graph = create_search_subgraph().get_graph()

    assert {
        "full_context_extractor",
        "full_context_retriever",
        "chunk_context_retriever",
        "search_insight",
    } <= set(graph.nodes)

    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert ("__start__", "full_context_extractor") in edges
    assert ("search_insight", "__end__") in edges


def test_extractor_uses_self_contained_question_without_a_model() -> None:
    command = asyncio.run(
        full_context_extractor({"user_question": "Supply risk: A/B?"}, {})
    )

    assert command.goto == "full_context_retriever"
    assert command.update == {"context_query": "supply risk\\: a\\/b\\?"}


def test_extractor_requires_a_question_or_human_message() -> None:
    with pytest.raises(ValueError, match="user_question"):
        asyncio.run(full_context_extractor({"messages": []}, {}))


def test_normalize_dedupes_by_node_id_and_fills_defaults() -> None:
    results = normalize_search_results(
        [
            {"node_id": "4:1", "title": "first", "score": 0.9},
            {"node_id": "4:1", "title": "duplicate", "score": 0.5},
            {"node_id": "4:2", "title": None, "tags": None},
        ]
    )

    assert [result["node_id"] for result in results] == ["4:1", "4:2"]
    assert results[0]["title"] == "first"
    assert results[1]["title"] == "No Title"
    assert results[1]["tags"] == []


def test_chunk_retriever_short_circuits_on_empty_results() -> None:
    command = asyncio.run(chunk_context_retriever({"retrieval_results": []}, {}))

    assert command.goto == "__end__"
    assert command.update["structured_response"] == {"search_results": []}


def test_search_insight_exposes_structured_results() -> None:
    command = asyncio.run(search_insight({"search_results": [{"title": "A"}]}, {}))

    assert command["structured_response"] == {"search_results": [{"title": "A"}]}
    assert command["messages"][-1].name == "search_subgraph"


def test_index_ddl_matches_query_index_name() -> None:
    assert "combinedIndex" in CREATE_FULLTEXT_INDEX
    assert "combindedIndex" not in CREATE_FULLTEXT_INDEX
    assert "`fulltext.analyzer`" in CREATE_FULLTEXT_INDEX


def test_escape_lucene_neutralizes_operators() -> None:
    assert escape_lucene('risk: "a" AND (b|~c)') == r'risk\: \"a\" AND \(b\|\~c\)'


class _Record:
    def __init__(self, data: dict) -> None:
        self._data = data

    def data(self) -> dict:
        return self._data


class _Result:
    def __init__(self, rows: list[_Record]) -> None:
        self._rows = iter(rows)

    def __aiter__(self) -> _Result:
        return self

    async def __anext__(self) -> _Record:
        try:
            return next(self._rows)
        except StopIteration as err:
            raise StopAsyncIteration from err


class _Session:
    async def run(self, query: str, params: dict | None = None) -> _Result:
        return _Result([_Record({"node_id": "n1", "title": "Doc", "url": "https://example.test", "score": 1.0})])


@asynccontextmanager
async def _fake_session():
    yield _Session()


async def _fake_index() -> None:
    return None


def test_subgraph_end_to_end_with_fake_neo4j() -> None:
    with (
        patch("src.app.engine.search.node.full_context_retriever.get_async_session", _fake_session),
        patch("src.app.engine.search.node.full_context_retriever._ensure_fulltext_index", _fake_index),
    ):
        output = asyncio.run(
            search_subgraph.ainvoke({"user_question": "supply", "user_uuid": "u1"}, {"configurable": {}})
        )

    assert set(output) == {"messages", "search_results", "structured_response"}
    assert output["search_results"][0]["title"] == "Doc"
    assert output["structured_response"] == {"search_results": output["search_results"]}
