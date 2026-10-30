from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import pytest
from neo4j import AsyncGraphDatabase

from src.app.engine.search.graph import KnowledgeGraph
from src.app.engine.search.items import FileItem, LinkItem, MemoItem
from src.app.engine.search.queries import CREATE_FULLTEXT_INDEX, FULLTEXT_SEARCH

pytestmark = pytest.mark.integration

NEO4J_URI = os.environ.get("NEO4J_TEST_URI")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


@pytest.mark.skipif(not NEO4J_URI, reason="set NEO4J_TEST_URI to run Neo4j integration tests")
def test_search_graph_round_trip() -> None:
    asyncio.run(_round_trip())


async def _round_trip() -> None:
    assert NEO4J_URI
    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password")),
    )
    await driver.verify_connectivity()

    @asynccontextmanager
    async def session_factory():
        async with driver.session(database=NEO4J_DATABASE) as session:
            yield session

    graph = KnowledgeGraph(session_factory)
    user_uuid = f"it-{uuid.uuid4().hex[:8]}"

    try:
        link = LinkItem(
            user_uuid=user_uuid,
            title="AI 커리어 전환",
            url="https://example.com/ai-career",
            description="커리어 전환 가이드",
            tags=["커리어", "AI"],
        )
        file = FileItem(
            user_uuid=user_uuid,
            title="체크리스트",
            url="file:///demo/checklist.pdf",
            description="전환 체크리스트",
            tags=["커리어"],
        )
        memo = MemoItem(
            user_uuid=user_uuid,
            content="과업 재구성 메모",
            tags=["AI"],
        )

        for item in (link, file, memo):
            assert await graph.upsert(item) == item.uuid

        assert await graph.attach_memo(memo.uuid, link.uuid, user_uuid=user_uuid) == link.uuid
        assert await graph.reference_file(link.uuid, file.uuid, user_uuid=user_uuid) == file.uuid

        async with session_factory() as session:
            await (await session.run(CREATE_FULLTEXT_INDEX)).consume()
            await (await session.run("CALL db.awaitIndexes(60)")).consume()
            result = await session.run(
                FULLTEXT_SEARCH,
                {"kw": "커리어", "user_uuid": user_uuid, "limit": 10},
            )
            rows = [record.data() async for record in result]

        assert {row["title"] for row in rows} >= {"AI 커리어 전환", "체크리스트"}

        fetched = await graph.get_item(link.uuid, user_uuid=user_uuid)
        assert fetched is not None
        assert fetched["labels"] == ["Link"]
        assert fetched["tags"] == ["AI", "커리어"]

        updated = link.model_copy(update={"title": "AI 커리어 전환 v2", "tags": ["AI", "전환"]})
        await graph.upsert(updated)
        fetched = await graph.get_item(link.uuid, user_uuid=user_uuid)
        assert fetched is not None
        assert fetched["title"] == "AI 커리어 전환 v2"
        assert fetched["tags"] == ["AI", "전환"]
        assert fetched["created_at"] == link.created_at

        foreign = link.model_copy(update={"user_uuid": f"other-{user_uuid}"})
        with pytest.raises(PermissionError):
            await graph.upsert(foreign)

        items = await graph.list_items(user_uuid=user_uuid)
        assert {item["uuid"] for item in items} == {link.uuid, file.uuid, memo.uuid}
    finally:
        await graph.delete_user_graph(user_uuid)
        await driver.close()
