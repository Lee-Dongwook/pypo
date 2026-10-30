from __future__ import annotations

from src.app.engine.search.items import FileItem, LinkItem, MemoItem


def test_link_derives_title_from_url() -> None:
    item = LinkItem(user_uuid="u1", url="https://example.com/career/guide")

    assert item.title == "example.com"
    assert item.kind == "Link"


def test_memo_derives_title_and_description_from_content() -> None:
    item = MemoItem(
        user_uuid="u1",
        content="첫 줄 제목\n둘째 줄은 본문입니다.",
    )

    assert item.title == "첫 줄 제목"
    assert item.description == "첫 줄 제목\n둘째 줄은 본문입니다."


def test_empty_memo_gets_fallback_title() -> None:
    assert MemoItem(user_uuid="u1").title == "Untitled memo"


def test_file_derives_title_from_last_path_segment() -> None:
    item = FileItem(user_uuid="u1", url="file:///demo/portfolio.pdf")

    assert item.title == "portfolio.pdf"


def test_tags_are_trimmed_and_case_insensitively_deduplicated() -> None:
    item = LinkItem(
        user_uuid="u1",
        url="https://example.com",
        tags=[" AI ", "ai", "Career", "", "career"],
    )

    assert item.tags == ["AI", "Career"]


def test_properties_leave_server_managed_timestamps_out() -> None:
    item = MemoItem(user_uuid="u1", content="hello", tags=["memo"])

    properties = item.properties()

    assert properties["kind"] == "Memo"
    assert properties["user_uuid"] == "u1"
    assert properties["tags"] == ["memo"]
    assert "uuid" not in properties
    assert "created_at" not in properties
    assert "updated_at" not in properties
