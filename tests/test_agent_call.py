import asyncio
from datetime import datetime, timezone
from typing import Any

from src.app.agents.model import Agent
from src.app.agents.protocols import SubAgentResolver
from src.app.agents.supervisor.agent_call import make_agent_call_tool


def _agent(slug: str = "risk-analyst") -> Agent:
    now = datetime.now(timezone.utc)
    return Agent(
        uuid="01a18700-0000-7000-8000-000000000000",
        tenant_uuid="01a18700-0000-7000-8000-000000000001",
        name="risk analyst",
        slug=slug,
        type="assistant",
        description="answers supplier risk questions",
        workflow={},
        etag="v1",
        created_at=now,
        updated_at=now,
    )


class FakeResolver:
    def __init__(self, agents: dict[str, Agent] | None = None, error: Exception | None = None) -> None:
        self.agents = agents or {}
        self.error = error
        self.calls: list[tuple[set[str], str | None]] = []

    async def resolve(self, slugs: set[str], user_uuid: str | None = None) -> dict[str, Agent]:
        self.calls.append((slugs, user_uuid))
        if self.error is not None:
            raise self.error
        return {slug: agent for slug, agent in self.agents.items() if slug in slugs}

    async def resolve_available(self, user_uuid: str | None = None) -> dict[str, Agent]:
        return self.agents


def _run(coro) -> Any:
    return asyncio.run(coro)


def test_agent_call_invokes_sub_agent_with_task_and_ids() -> None:
    calls: list[dict[str, Any]] = []

    async def invoker(agent, task, *, tool_call_id, caller_uuid):
        calls.append({"agent": agent, "task": task, "tool_call_id": tool_call_id, "caller_uuid": caller_uuid})
        return "서브에이전트 완료"

    resolver: SubAgentResolver = FakeResolver({"risk-analyst": _agent()})
    tool = make_agent_call_tool(resolver, caller_uuid="user-1", invoker=invoker)

    assert _run(tool(slug="risk-analyst", task="이 공급사의 리스크를 분석해줘")) == "서브에이전트 완료"
    assert calls[0]["agent"].slug == "risk-analyst"
    assert calls[0]["task"] == "이 공급사의 리스크를 분석해줘"
    assert calls[0]["tool_call_id"].startswith("call_")
    assert calls[0]["caller_uuid"] == "user-1"
    assert resolver.calls == [({"risk-analyst"}, "user-1")]


def test_agent_call_unknown_slug_returns_korean_error() -> None:
    tool = make_agent_call_tool(FakeResolver({}), invoker=None)

    assert "찾을 수 없습니다" in _run(tool(slug="missing", task="작업"))


def test_agent_call_resolver_failure_is_mapped() -> None:
    tool = make_agent_call_tool(FakeResolver(error=RuntimeError("db down")), invoker=None)

    assert "조회에 실패했습니다 (RuntimeError)" in _run(tool(slug="risk-analyst", task="작업"))


def test_agent_call_without_invoker_reports_missing_engine() -> None:
    tool = make_agent_call_tool(FakeResolver({"risk-analyst": _agent()}))

    assert "실행 엔진이 설정되지 않았습니다" in _run(tool(slug="risk-analyst", task="작업"))


def test_agent_call_invoker_failure_is_mapped() -> None:
    async def invoker(agent, task, *, tool_call_id, caller_uuid):
        raise RuntimeError("boom")

    tool = make_agent_call_tool(FakeResolver({"risk-analyst": _agent()}), invoker=invoker)

    assert "실행에 실패했습니다 (RuntimeError)" in _run(tool(slug="risk-analyst", task="작업"))


def test_agent_call_rejects_blank_slug() -> None:
    tool = make_agent_call_tool(FakeResolver({}))

    assert "slug가 비어 있습니다" in _run(tool(slug="  ", task="작업"))


def test_agent_call_rejects_blank_task() -> None:
    tool = make_agent_call_tool(FakeResolver({}))

    assert "task)이 비어 있습니다" in _run(tool(slug="risk-analyst", task="  "))
