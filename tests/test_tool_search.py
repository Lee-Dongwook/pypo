import json

from src.app.agents.supervisor.tools.search import TOOL_DESCRIBE, TOOL_SEARCH, make_tool_describe, make_tool_search
from src.app.agents.tools.registry import ToolRegistry


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def search_cards(query: str) -> str:
        return query

    def book_meeting(title: str, attendees: int = 1) -> str:
        return title * attendees

    registry.register("search_cards", "카드 상품 설명서를 검색합니다.")(search_cards)
    registry.register("book_meeting", "회의실을 예약합니다.")(book_meeting)
    return registry


def test_tool_search_finds_relevant_tool_by_description() -> None:
    result = json.loads(make_tool_search(_make_registry())("회의실 예약"))

    assert [hit["name"] for hit in result] == ["book_meeting"]


def test_tool_search_returns_empty_message_when_nothing_matches() -> None:
    assert "찾지 못했습니다" in make_tool_search(_make_registry())("zzzzzz")


def test_tool_search_rejects_blank_query() -> None:
    assert "비어 있습니다" in make_tool_search(_make_registry())("   ")


def test_tool_search_clamps_k() -> None:
    result = json.loads(make_tool_search(_make_registry())("검색", k=0))

    assert len(result) == 1


def test_tool_describe_returns_json_schema() -> None:
    result = json.loads(make_tool_describe(_make_registry())("book_meeting"))

    assert result["name"] == "book_meeting"
    assert result["parameters"]["required"] == ["title"]


def test_tool_describe_unknown_tool_returns_korean_error() -> None:
    assert "알 수 없는 도구" in make_tool_describe(_make_registry())("nope")


def test_meta_tool_constants_match_registry_names() -> None:
    assert TOOL_SEARCH == "tool_search"
    assert TOOL_DESCRIBE == "tool_describe"
