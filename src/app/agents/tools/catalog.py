"""hermes/감독자가 기본으로 쓰는 도구 카탈로그를 만든다.

전역 싱글턴 대신 호출부마다 새 레지스트리를 만들어 주입한다. 감독자는
caller(사용자)에 따라 서브에이전트 도구를 추가로 등록해야 하므로 요청 간
상태를 공유하지 않는다.
"""

from __future__ import annotations

from ..supervisor.tools.search import TOOL_DESCRIBE, TOOL_SEARCH, make_tool_describe, make_tool_search
from .builtin_tools import register_builtin_tools
from .registry import ToolRegistry


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    registry.register(
        TOOL_SEARCH,
        "이름·설명에서 도구를 BM25로 검색합니다. action_input: {\"query\": str, \"k\": int?}",
    )(make_tool_search(registry))
    registry.register(
        TOOL_DESCRIBE,
        "도구 하나의 상세 규격(JSON Schema)을 돌려줍니다. action_input: {\"name\": str}",
    )(make_tool_describe(registry))
    return registry
