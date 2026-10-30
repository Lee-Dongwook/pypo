"""Neo4j persistence for the personal knowledge graph.

The labels and properties here are the contract consumed by
`src/app/engine/search/queries.py`: every Link, Memo, and File node carries
`user_uuid`, `title`, `description`, `tags`, and `created_at`, so the same
full-text index can search all three types.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from src.app.shared.neo4j import get_async_session

from .items import KnowledgeItem, now_ms

SessionFactory = Callable[[], AbstractAsyncContextManager[Any]]

_LABEL_BY_KIND = {
    "Link": "Link",
    "Memo": "Memo",
    "File": "File",
}

_UPSERT_TEMPLATE = """
MERGE (n:__LABEL__ {uuid: $uuid})
ON CREATE SET n.created_at = $created_at
WITH n
WHERE n.user_uuid = $user_uuid OR n.user_uuid IS NULL
SET n += $props
WITH n
MERGE (owner:User {uuid: $user_uuid})
MERGE (owner)-[:OWNS]->(n)
WITH n
OPTIONAL MATCH (n)-[old:TAGGED]->(:Tag)
DELETE old
WITH DISTINCT n
FOREACH (tag_name IN $tags |
    MERGE (tag:Tag {user_uuid: $user_uuid, name: tag_name})
    MERGE (n)-[:TAGGED]->(tag)
)
RETURN n.uuid AS uuid
"""

_ATTACH_MEMO = """
MATCH (memo:Memo {uuid: $memo_uuid, user_uuid: $user_uuid})
MATCH (target {uuid: $target_uuid, user_uuid: $user_uuid})
WHERE target:Link OR target:File
MERGE (memo)-[:ATTACHED_TO]->(target)
RETURN target.uuid AS uuid
"""

_REFERENCE_FILE = """
MATCH (link:Link {uuid: $link_uuid, user_uuid: $user_uuid})
MATCH (file:File {uuid: $file_uuid, user_uuid: $user_uuid})
MERGE (link)-[:REFERENCES]->(file)
RETURN file.uuid AS uuid
"""

_DELETE_ITEM = """
MATCH (n)
WHERE n.uuid = $uuid
  AND n.user_uuid = $user_uuid
  AND (n:Link OR n:Memo OR n:File)
DETACH DELETE n
"""

_DELETE_USER_GRAPH = """
MATCH (n)
WHERE n.user_uuid = $user_uuid
   OR (n:User AND n.uuid = $user_uuid)
DETACH DELETE n
"""

_GET_ITEM = """
MATCH (n {uuid: $uuid, user_uuid: $user_uuid})
WHERE n:Link OR n:Memo OR n:File
OPTIONAL MATCH (n)-[:TAGGED]->(tag:Tag)
RETURN labels(n) AS labels, properties(n) AS props, collect(DISTINCT tag.name) AS tags
"""

_LIST_ITEMS = """
MATCH (n)
WHERE n.user_uuid = $user_uuid
  AND (n:Link OR n:Memo OR n:File)
RETURN labels(n) AS labels, properties(n) AS props
ORDER BY n.created_at DESC
LIMIT $limit
"""


class KnowledgeGraph:
    """Write and read Link/Memo/File nodes for one user at a time."""

    def __init__(self, session_factory: SessionFactory | None = None) -> None:
        self._session_factory = session_factory or get_async_session

    async def upsert(self, item: KnowledgeItem) -> str:
        """Create or update a node, its owner edge, and its tag edges.

        Raises ``PermissionError`` when the uuid already belongs to another user.
        Re-upserting preserves the original ``created_at``.
        """
        label = _LABEL_BY_KIND[item.kind]
        props = {**item.properties(), "updated_at": now_ms()}
        params = {
            "uuid": item.uuid,
            "user_uuid": item.user_uuid,
            "created_at": item.created_at,
            "props": props,
            "tags": item.tags,
        }

        async with self._session_factory() as session:
            record = await (await session.run(_UPSERT_TEMPLATE.replace("__LABEL__", label), params)).single()

        if record is None:
            raise PermissionError(f"item {item.uuid} belongs to another user")
        return str(record["uuid"])

    async def attach_memo(self, memo_uuid: str, target_uuid: str, *, user_uuid: str) -> str:
        """Attach a memo to a Link or File owned by ``user_uuid``."""
        params = {"memo_uuid": memo_uuid, "target_uuid": target_uuid, "user_uuid": user_uuid}
        async with self._session_factory() as session:
            record = await (await session.run(_ATTACH_MEMO, params)).single()

        if record is None:
            raise LookupError("memo or target not found for this user")
        return str(record["uuid"])

    async def reference_file(self, link_uuid: str, file_uuid: str, *, user_uuid: str) -> str:
        """Record that a Link refers to a File owned by ``user_uuid``."""
        params = {"link_uuid": link_uuid, "file_uuid": file_uuid, "user_uuid": user_uuid}
        async with self._session_factory() as session:
            record = await (await session.run(_REFERENCE_FILE, params)).single()

        if record is None:
            raise LookupError("link or file not found for this user")
        return str(record["uuid"])

    async def delete_item(self, uuid: str, *, user_uuid: str) -> int:
        """Delete one node and its relationships. Returns the deleted node count."""
        params = {"uuid": uuid, "user_uuid": user_uuid}
        async with self._session_factory() as session:
            summary = await (await session.run(_DELETE_ITEM, params)).consume()
        return int(summary.counters.nodes_deleted)

    async def delete_user_graph(self, user_uuid: str) -> int:
        """Delete every knowledge node, tag, and the owner node for a user."""
        params = {"user_uuid": user_uuid}
        async with self._session_factory() as session:
            summary = await (await session.run(_DELETE_USER_GRAPH, params)).consume()
        return int(summary.counters.nodes_deleted)

    async def get_item(self, uuid: str, *, user_uuid: str) -> dict[str, Any] | None:
        """Return one item with its labels and tag names."""
        params = {"uuid": uuid, "user_uuid": user_uuid}
        async with self._session_factory() as session:
            record = await (await session.run(_GET_ITEM, params)).single()

        if record is None:
            return None

        data = dict(record["props"])
        data["labels"] = list(record["labels"])
        data["tags"] = sorted(record["tags"])
        return data

    async def list_items(self, *, user_uuid: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return a user's items, newest first."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        params = {"user_uuid": user_uuid, "limit": limit}
        async with self._session_factory() as session:
            result = await session.run(_LIST_ITEMS, params)
            records = [record async for record in result]

        items = []
        for record in records:
            data = dict(record["props"])
            data["labels"] = list(record["labels"])
            items.append(data)
        return items


__all__ = ["KnowledgeGraph", "SessionFactory"]
