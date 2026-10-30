from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


def normalize_search_results(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn raw Neo4j records into the public search result shape.

    Full-text hits can repeat a node when several indexed properties match, so
    results are deduplicated by ``node_id`` while keeping the highest-scored
    (first) occurrence.
    """
    results: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    for record in records:
        node_id = record.get("node_id")
        if node_id is not None:
            if node_id in seen_node_ids:
                continue
            seen_node_ids.add(node_id)

        results.append(
            {
                "node_id": node_id,
                "url": record.get("url"),
                "title": record.get("title") or "No Title",
                "description": record.get("description") or "",
                "score": record.get("score"),
                "tags": record.get("tags") or [],
                "created_at": record.get("created_at"),
            }
        )

    return results


def format_search_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "Result not found."

    lines = []
    for index, result in enumerate(results, start=1):
        title = result.get("title", "-")
        url = result.get("url", "-")
        description = result.get("description", "-")
        tags = result.get("tags", [])
        score = result.get("score") or 0.0
        created_at = result.get("created_at")

        created_string = "null"
        if created_at is not None:
            try:
                created_string = datetime.fromtimestamp(created_at / 1000, tz=ZoneInfo("Asia/Seoul")).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except (TypeError, ValueError):
                pass

        tags_string = ", ".join(tags) if tags else "-"

        lines.append(
            textwrap.dedent(f"""
            **{index}. {title}** (Score: {score:.2f})
            {description}
            Tags: {tags_string}
            Created: {created_string}
            {url}
            """)
        )

    header = f"Found {len(results)} related results: \n\n"
    return header + "\n\n".join(lines)


__all__ = ["format_search_results", "normalize_search_results"]
