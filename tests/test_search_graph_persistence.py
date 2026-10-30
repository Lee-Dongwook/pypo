from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from src.app.engine.search.graph import KnowledgeGraph
from src.app.engine.search.items import LinkItem, MemoItem


class FakeResult:
    def __init__(
        self,
        *,
        record: dict[str, Any] | None = None,
        rows: list[dict[str, Any]] | None = None,
        nodes_deleted: int = 0,
    ) -> None:
        self.record = record
        self.rows = iter(rows or [])
        self.nodes_deleted = nodes_deleted

    async def single(self) -> dict[str, Any] | None:
        return self.record

    async def consume(self) -> SimpleNamespace:
        return SimpleNamespace(counters=SimpleNamespace(nodes_deleted=self.nodes_deleted))

    def __aiter__(self) -> FakeResult:
        return self

    async def __anext__(self) -> dict[str, Any]:
        try:
            return next(self.rows)
        except StopIteration as err:
            raise StopAsyncIteration from err


class FakeSessions:
    def __init__(self, result: FakeResult) -> None:
        self.result = result
        self.log: list[tuple[str, dict[str, Any]]] = []

    async def run(self, query: str, params: dict[str, Any]) -> FakeResult:
        self.log.append((query, params))
        return self.result

    @asynccontextmanager
    async def session(self):
        yield self


def _graph(result: FakeResult) -> tuple[KnowledgeGraph, FakeSessions]:
    sessions = FakeSessions(result)
    return KnowledgeGraph(sessions.session), sessions


def test_upsert_writes_label_props_owner_and_tags() -> None:
    item = LinkItem(user_uuid="u1", url="https://example.com/a", tags=["AI", "Career"])
    graph, sessions = _graph(FakeResult(record={"uuid": item.uuid}))

    assert asyncio.run(graph.upsert(item)) == item.uuid

    query, params = sessions.log[0]
    assert "MERGE (n:Link {uuid: $uuid})" in query
    assert "WHERE n.user_uuid = $user_uuid OR n.user_uuid IS NULL" in query
    assert "MERGE (owner)-[:OWNS]->(n)" in query
    assert "MERGE (n)-[:TAGGED]->(tag)" in query
    assert params["uuid"] == item.uuid
    assert params["user_uuid"] == "u1"
    assert params["props"]["kind"] == "Link"
    assert params["props"]["tags"] == ["AI", "Career"]
    assert params["props"]["updated_at"] >= item.created_at
    assert params["tags"] == ["AI", "Career"]


def test_upsert_refuses_a_uuid_owned_by_another_user() -> None:
    graph, _ = _graph(FakeResult(record=None))
    item = MemoItem(user_uuid="u1", content="hello")

    with pytest.raises(PermissionError):
        asyncio.run(graph.upsert(item))


def test_attach_memo_is_scoped_to_user_and_target_labels() -> None:
    graph, sessions = _graph(FakeResult(record={"uuid": "target"}))

    assert asyncio.run(graph.attach_memo("memo", "target", user_uuid="u1")) == "target"

    query, params = sessions.log[0]
    assert "MATCH (memo:Memo {uuid: $memo_uuid, user_uuid: $user_uuid})" in query
    assert "WHERE target:Link OR target:File" in query
    assert params == {"memo_uuid": "memo", "target_uuid": "target", "user_uuid": "u1"}


def test_attach_memo_reports_a_missing_endpoint() -> None:
    graph, _ = _graph(FakeResult(record=None))

    with pytest.raises(LookupError):
        asyncio.run(graph.attach_memo("memo", "missing", user_uuid="u1"))


def test_delete_item_returns_deleted_node_count() -> None:
    graph, sessions = _graph(FakeResult(nodes_deleted=1))

    assert asyncio.run(graph.delete_item("n1", user_uuid="u1")) == 1

    query, params = sessions.log[0]
    assert "DETACH DELETE n" in query
    assert params == {"uuid": "n1", "user_uuid": "u1"}


def test_get_item_merges_properties_and_tag_names() -> None:
    graph, _ = _graph(
        FakeResult(
            record={
                "labels": ["Link"],
                "props": {"uuid": "n1", "user_uuid": "u1", "title": "A", "tags": ["stale"]},
                "tags": ["AI", "Career"],
            }
        )
    )

    item = asyncio.run(graph.get_item("n1", user_uuid="u1"))

    assert item is not None
    assert item["labels"] == ["Link"]
    assert item["title"] == "A"
    assert item["tags"] == ["AI", "Career"]


def test_list_items_returns_newest_first_rows() -> None:
    graph, _ = _graph(
        FakeResult(
            rows=[
                {"labels": ["Link"], "props": {"uuid": "n1", "title": "first"}},
                {"labels": ["Memo"], "props": {"uuid": "n2", "title": "second"}},
            ]
        )
    )

    items = asyncio.run(graph.list_items(user_uuid="u1"))

    assert [item["uuid"] for item in items] == ["n1", "n2"]
    assert items[1]["labels"] == ["Memo"]


def test_list_items_rejects_non_positive_limit() -> None:
    graph, _ = _graph(FakeResult())

    with pytest.raises(ValueError):
        asyncio.run(graph.list_items(user_uuid="u1", limit=0))
