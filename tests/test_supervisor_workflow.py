import asyncio
import json

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage, ToolMessage

import src.app.agents.supervisor.workflow as workflow
from src.app.agents.tools.catalog import build_default_registry


def _initial_state() -> dict:
    return {
        "messages": [HumanMessage(content="회의실 예약 도구가 뭔지 알려줘")],
        "user_uuid": "user-1",
        "user_question": "회의실 예약 도구가 뭔지 알려줘",
        "language": "한국어",
        "structured_response": {},
        "values": {},
        "skill_ids": None,
    }


def test_supervisor_finishes_with_answer(monkeypatch) -> None:
    model = FakeListChatModel(
        responses=['{"thought": "t", "action": "finish", "action_input": {"answer": "예약 도구는 book_meeting입니다."}}']
    )
    monkeypatch.setattr(workflow, "get_search_model", lambda config: model)

    graph = asyncio.run(workflow.build_supervisor_graph())
    state = asyncio.run(graph.ainvoke(_initial_state()))

    assert state["structured_response"]["answer"] == "예약 도구는 book_meeting입니다."


def test_supervisor_calls_tool_and_observes_result(monkeypatch) -> None:
    model = FakeListChatModel(
        responses=[
            '{"thought": "t", "action": "tool_describe", "action_input": {"name": "run_python_test"}}',
            '{"thought": "t", "action": "finish", "action_input": {"answer": "run_python_test입니다."}}',
        ]
    )
    monkeypatch.setattr(workflow, "get_search_model", lambda config: model)

    registry = build_default_registry()
    graph = asyncio.run(workflow.build_supervisor_graph(tools=registry))
    state = asyncio.run(graph.ainvoke(_initial_state()))

    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].name == "tool_describe"
    assert json.loads(tool_messages[0].content)["name"] == "run_python_test"
    assert state["structured_response"]["answer"] == "run_python_test입니다."


def test_supervisor_recovers_from_invalid_json_then_finishes(monkeypatch) -> None:
    model = FakeListChatModel(
        responses=[
            "JSON이 아닌 응답",
            '{"thought": "t", "action": "finish", "action_input": {"answer": "다시 답함"}}',
        ]
    )
    monkeypatch.setattr(workflow, "get_search_model", lambda config: model)

    graph = asyncio.run(workflow.build_supervisor_graph())
    state = asyncio.run(graph.ainvoke(_initial_state()))

    assert state["structured_response"]["answer"] == "다시 답함"
