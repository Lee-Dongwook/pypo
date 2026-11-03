"""도구 검색·설명 도구 (tool registry의 tool retrieval).

도구가 늘어나도 프롬프트에 전부 싣지 않고, 이 두 도구로 필요할 때만 조회하게 한다.
BM25 색인(`.index.Bm25Index`)으로 이름과 설명을 검색하고, 설명 도구는 JSON Schema를 돌려준다.
"""

from __future__ import annotations

import json

from ...tools.registry import ToolRegistry
from .index import Bm25Index

TOOL_SEARCH = "tool_search"
TOOL_DESCRIBE = "tool_describe"

_MAX_RESULTS = 10


def make_tool_search(registry: ToolRegistry):
    def tool_search(query: str, k: int = 5) -> str:
        specs = registry.specs()
        if not specs:
            return "등록된 도구가 없습니다."

        query = query.strip()
        if not query:
            return "검색어가 비어 있습니다."

        try:
            k = max(1, min(int(k), _MAX_RESULTS))
        except (TypeError, ValueError):
            k = 5

        documents = [f"{spec.name} {spec.description}" for spec in specs]
        hits = Bm25Index.from_names(documents).search(query, k)
        by_document = dict(zip(documents, specs, strict=True))
        results = [
            {"name": spec.name, "description": spec.description}
            for document in hits
            if (spec := by_document.get(document)) is not None
        ]
        if not results:
            return f"'{query}'와(과) 관련된 도구를 찾지 못했습니다."
        return json.dumps(results, ensure_ascii=False, indent=2)

    return tool_search


def make_tool_describe(registry: ToolRegistry):
    def tool_describe(name: str) -> str:
        spec = registry.get(name.strip())
        if spec is None:
            return f"알 수 없는 도구입니다: '{name}'"
        return json.dumps(spec.schema, ensure_ascii=False, indent=2)

    return tool_describe
