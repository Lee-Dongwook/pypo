import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.app.agents.agent_loop import AgentLoop
from src.app.agents.tools.registry import ToolRegistry


def _finish(answer: str = "done") -> str:
    return f'{{"thought": "t", "action": "finish", "action_input": {{"answer": "{answer}"}}}}'


def _tool_call(name: str, kwargs: str) -> str:
    return f'{{"thought": "t", "action": "{name}", "action_input": {kwargs}}}'


def _registry_with_recorder() -> tuple[ToolRegistry, list[dict]]:
    calls: list[dict] = []
    registry = ToolRegistry()

    def record(query: str) -> str:
        calls.append({"query": query})
        return "관찰 결과"

    registry.register("record", "query를 기록합니다.")(record)
    return registry, calls


def test_run_returns_true_when_model_finishes() -> None:
    model = FakeListChatModel(responses=[_finish()])
    loop = AgentLoop(model=model, registry=ToolRegistry())

    assert loop.run("테스트 태스크") is True


def test_run_executes_tool_and_feeds_observation_back() -> None:
    registry, calls = _registry_with_recorder()
    model = FakeListChatModel(responses=[_tool_call("record", '{"query": "안녕"}'), _finish()])
    loop = AgentLoop(model=model, registry=registry)

    assert loop.run("테스트 태스크") is True
    assert calls == [{"query": "안녕"}]


def test_run_recovers_from_invalid_json_and_finishes() -> None:
    model = FakeListChatModel(responses=["이건 JSON이 아닙니다", _finish()])
    loop = AgentLoop(model=model, registry=ToolRegistry())

    assert loop.run("테스트 태스크") is True


def test_run_returns_false_when_steps_are_exhausted() -> None:
    model = FakeListChatModel(responses=["not json", "still not json"])
    loop = AgentLoop(max_steps=2, model=model, registry=ToolRegistry())

    assert loop.run("테스트 태스크") is False


def test_run_rejects_blank_task() -> None:
    loop = AgentLoop(model=FakeListChatModel(responses=[_finish()]), registry=ToolRegistry())

    with pytest.raises(ValueError, match="비어 있습니다"):
        loop.run("   ")


def test_max_steps_must_be_positive() -> None:
    with pytest.raises(ValueError, match="1 이상"):
        AgentLoop(max_steps=0, model=FakeListChatModel(responses=[]), registry=ToolRegistry())
