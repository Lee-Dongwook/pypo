"""Node models for the personal knowledge graph searched by the subgraph.

All timestamps are epoch milliseconds because `format_search_results` converts
`created_at / 1000` to a KST datetime.
"""

from __future__ import annotations

import time
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from src.app.shared.registry import new_uuid

ItemKind = Literal["Link", "Memo", "File"]

_MAX_TITLE = 300
_MAX_DESCRIPTION = 1_000


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def _first_line(text: str, limit: int = _MAX_TITLE) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:limit]
    return ""


class KnowledgeItem(BaseModel):
    """Properties shared by every searchable knowledge node."""

    kind: ItemKind
    uuid: str = Field(default_factory=new_uuid)
    user_uuid: str = Field(min_length=1)
    title: str = Field(default="", max_length=_MAX_TITLE)
    description: str = Field(default="", max_length=_MAX_DESCRIPTION)
    tags: list[str] = Field(default_factory=list)
    created_at: int = Field(default_factory=now_ms)
    updated_at: int = Field(default_factory=now_ms)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, tags: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            name = tag.strip()
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                cleaned.append(name)
        return cleaned

    def properties(self) -> dict[str, Any]:
        """Neo4j properties for the upsert.

        ``created_at`` is written only when the node is first created, and
        ``updated_at`` is overwritten by the service on every write.
        """
        return self.model_dump(exclude={"uuid", "created_at", "updated_at"}, exclude_none=True)


class LinkItem(KnowledgeItem):
    """A saved URL."""

    kind: Literal["Link"] = "Link"
    url: str = Field(min_length=1)

    @model_validator(mode="after")
    def _fill_title(self) -> LinkItem:
        if not self.title:
            self.title = (urlparse(self.url).netloc or self.url)[:_MAX_TITLE]
        return self


class MemoItem(KnowledgeItem):
    """A free-form note, optionally attached to a Link or File."""

    kind: Literal["Memo"] = "Memo"
    content: str = ""

    @model_validator(mode="after")
    def _fill_searchable_text(self) -> MemoItem:
        if not self.title:
            self.title = _first_line(self.content) or "Untitled memo"
        if not self.description:
            self.description = self.content.strip()[:_MAX_DESCRIPTION]
        return self


class FileItem(KnowledgeItem):
    """An uploaded or referenced file."""

    kind: Literal["File"] = "File"
    url: str = Field(min_length=1)
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _fill_title(self) -> FileItem:
        if not self.title:
            name = self.url.rstrip("/").rsplit("/", 1)[-1]
            self.title = (name or self.url)[:_MAX_TITLE]
        return self


__all__ = ["FileItem", "ItemKind", "KnowledgeItem", "LinkItem", "MemoItem", "now_ms"]
