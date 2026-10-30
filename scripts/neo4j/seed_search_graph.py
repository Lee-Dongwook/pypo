#!/usr/bin/env python
"""Seed a demo Link/Memo/File graph for the search subgraph.

Run `make neo4j-init` first so the full-text index and constraints exist, then:

    uv run python -m scripts.neo4j.seed_search_graph --user-uuid demo-user

The script is idempotent: it removes the user's previous demo graph before
writing the new one.
"""

from __future__ import annotations

import argparse
import asyncio
import time

from src.app.engine.search.graph import KnowledgeGraph
from src.app.engine.search.items import FileItem, LinkItem, MemoItem
from src.app.shared.neo4j import close_async_driver

DEFAULT_USER_UUID = "demo-user"


async def seed(user_uuid: str, *, reset: bool) -> None:
    graph = KnowledgeGraph()
    created_at = time.time_ns() // 1_000_000

    if reset:
        deleted = await graph.delete_user_graph(user_uuid)
        print(f"removed {deleted} existing node(s) for {user_uuid}")

    transition_link = LinkItem(
        user_uuid=user_uuid,
        title="AI 시대 커리어 전환 가이드",
        url="https://example.com/career/ai-transition",
        description="직무별 AI 노출도와 전환에 필요한 스킬을 정리한 가이드",
        tags=["커리어", "AI", "전환"],
        created_at=created_at,
    )
    trend_link = LinkItem(
        user_uuid=user_uuid,
        title="2026 직무 트렌드 리포트",
        url="https://example.com/career/2026-trends",
        description="국내외 채용 시장과 직무 변화를 요약한 연간 리포트",
        tags=["커리어", "트렌드"],
        created_at=created_at + 1,
    )
    checklist = FileItem(
        user_uuid=user_uuid,
        title="커리어 전환 체크리스트",
        url="file:///demo/career-checklist.pdf",
        mime_type="application/pdf",
        size_bytes=248_000,
        description="전환 준비 상태를 점검하는 8주 체크리스트",
        tags=["커리어", "체크리스트"],
        created_at=created_at + 2,
    )
    transition_memo = MemoItem(
        user_uuid=user_uuid,
        content=(
            "AI 전환은 도구 학습보다 과업 재구성이 먼저다.\n"
            "현재 업무를 자동화 가능/판단 필요/관계 중심으로 나누고, "
            "판단과 관계 업무를 포트폴리오로 증명하자."
        ),
        tags=["AI", "전환", "메모"],
        created_at=created_at + 3,
    )
    portfolio_memo = MemoItem(
        user_uuid=user_uuid,
        content="포트폴리오에는 자동화 경험을 시간 절감과 오류 감소 수치로 남긴다.",
        tags=["포트폴리오", "메모"],
        created_at=created_at + 4,
    )

    for item in (transition_link, trend_link, checklist, transition_memo, portfolio_memo):
        await graph.upsert(item)
        print(f"upserted {item.kind:4} {item.uuid}  {item.title}")

    await graph.attach_memo(transition_memo.uuid, transition_link.uuid, user_uuid=user_uuid)
    await graph.attach_memo(transition_memo.uuid, checklist.uuid, user_uuid=user_uuid)
    await graph.attach_memo(portfolio_memo.uuid, trend_link.uuid, user_uuid=user_uuid)
    await graph.reference_file(transition_link.uuid, checklist.uuid, user_uuid=user_uuid)

    print("linked memos to links/files and the transition link to the checklist")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-uuid", default=DEFAULT_USER_UUID, help="owner scope to seed")
    parser.add_argument("--no-reset", action="store_true", help="keep existing nodes for this user")
    args = parser.parse_args()

    try:
        await seed(args.user_uuid, reset=not args.no_reset)
    finally:
        await close_async_driver()


if __name__ == "__main__":
    asyncio.run(main())
