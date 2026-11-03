"""감독자 LangGraph를 조립한다.

노드는 `agent`(LLM이 다음 tool call을 JSON 한 조각으로 응답)와 `tools`(레지스트리에서
실행) 둘뿐이다. 도구가 늘어나도 프롬프트에는 메타 도구(`tool_search`·`tool_describe`,
그리고 설정된 경우 `agent_call`)만 싣고, 모델이 필요할 때 검색해서 호출한다
(docs/ARCHITECTURE.md의 Tool Registry 검색 패턴).
"""

from __future__ import annotations

import inspect
import json
import logging
import uuid
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ...engine.models import get_search_model
from ...user.schemas import UserRead
from ..protocols import SubAgentResolver
from ..react import FINISH_ACTION, REACT_INSTRUCTIONS, parse_action
from ..tools.catalog import build_default_registry
from ..tools.registry import ToolRegistry, error_message, validate_kwargs
from .agent_call import AGENT_CALL, SubAgentInvoker, make_agent_call_tool
from .state import SupervisorAgentState
from .tools.search import TOOL_DESCRIBE, TOOL_SEARCH

logger = logging.getLogger(__name__)

_META_TOOLS = (TOOL_SEARCH, TOOL_DESCRIBE, AGENT_CALL)


def _render_messages(messages: list[BaseMessage]) -> str:
    labels = {
        HumanMessage: "사용자",
        AIMessage: "어시스턴트",
        ToolMessage: "도구 관찰",
        SystemMessage: "시스템",
    }
    lines = []
    for message in messages:
        content = message.content if isinstance(message.content, str) else str(message.content)
        lines.append(f"{labels.get(type(message), type(message).__name__)}: {content}")
    return "\n".join(lines)


def _system_prompt(registry: ToolRegistry, state: SupervisorAgentState, caller: UserRead | None) -> str:
    del caller  # 권한 판정은 resolver가 한다. 프롬프트에는 노출하지 않는다.
    meta_specs = [spec.schema for spec in registry.specs() if spec.name in _META_TOOLS]
    tools_desc = json.dumps(meta_specs, ensure_ascii=False, indent=2)
    language = state.get("language") or "한국어"
    agent_call_note = (
        "서브에이전트가 필요하면 action=\"agent_call\"로 호출하라.\n"
        if AGENT_CALL in registry
        else ""
    )
    return (
        "너는 pypo의 자율 에이전트 감독자다. 주어진 대화를 읽고 필요한 도구를 골라 사용해라.\n"
        "아래에 보이는 도구는 메타 도구뿐이다. 다른 도구가 필요하면 action=\"tool_search\"로 검색하고,\n"
        "action=\"tool_describe\"로 규격을 확인한 뒤 그 도구를 호출하라.\n"
        f"{agent_call_note}"
        f"Available Meta Tools:\n{tools_desc}\n\n"
        f"{REACT_INSTRUCTIONS}\n"
        f"사용자에게 보이는 답변은 {language}(으)로 작성해라."
    )


def _observation(result: Any) -> str:
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)


async def build_supervisor_graph(
    config: RunnableConfig | None = None,
    caller: UserRead | None = None,
    *,
    sub_agents: SubAgentResolver | None = None,
    sub_agent_invoker: SubAgentInvoker | None = None,
    tools: ToolRegistry | None = None,
) -> CompiledStateGraph:
    """감독자 그래프를 컴파일한다.

    `config`는 런타임 설정(예: `configurable.search_model`), `caller`는 도구·에이전트
    노출을 제한하는 인증된 사용자. `sub_agents` resolver를 주면 `agent_call` 도구가
    등록된다. `tools`를 주면 기본 카탈로그를 쓰지 않고 그 레지스트리를 그대로 쓴다.
    """
    registry = tools if tools is not None else build_default_registry()
    # UserRead는 아직 필드가 없다. uuid가 생기면 권한 판정에 그대로 전달된다.
    caller_uuid = getattr(caller, "uuid", None) if caller is not None else None
    if sub_agents is not None and AGENT_CALL not in registry:
        registry.register(
            AGENT_CALL,
            "slug로 서브에이전트를 찾아 실행합니다. action_input: {\"slug\": str, \"task\": str}",
        )(make_agent_call_tool(sub_agents, caller_uuid=caller_uuid, invoker=sub_agent_invoker))

    model = get_search_model(config if config is not None else RunnableConfig())

    async def agent_node(state: SupervisorAgentState) -> dict[str, Any]:
        prompt = (
            f"{_system_prompt(registry, state, caller)}\n\n"
            f"# 대화\n{_render_messages(state['messages'])}\n\n"
            "Response:"
        )
        reply = await model.ainvoke(prompt)
        text = str(reply.content).strip()

        action = parse_action(text)
        if action is None:
            logger.warning("감독자 응답을 JSON으로 파싱할 수 없음: %s", text)
            feedback = HumanMessage(
                content="이전 응답을 JSON으로 파싱할 수 없습니다. 설명 없이 JSON 객체 하나만 응답하세요."
            )
            return {"messages": [AIMessage(content=text), feedback], "pending_action": None}

        if action.action == FINISH_ACTION:
            answer = action.action_input.get("answer") or text
            return {
                "messages": [AIMessage(content=text)],
                "pending_action": None,
                "structured_response": {"answer": answer},
            }

        pending = {"thought": action.thought, "action": action.action, "action_input": action.action_input}
        return {"messages": [AIMessage(content=text)], "pending_action": pending}

    async def tools_node(state: SupervisorAgentState) -> dict[str, Any]:
        pending = state.get("pending_action")
        if not pending:
            return {}

        name, kwargs = pending["action"], pending["action_input"]
        spec = registry.get(name)
        if spec is None:
            observation = f"알 수 없는 도구입니다: '{name}'"
        elif (message := validate_kwargs(spec, kwargs)) is not None:
            observation = message
        else:
            try:
                result = spec.func(**kwargs)
                if inspect.isawaitable(result):
                    result = await result
                observation = _observation(result)
            except Exception as exc:
                logger.warning("도구 '%s' 실행 실패: %s", name, exc)
                observation = error_message(name, exc)

        logger.info("tool %s -> %s", name, observation)
        return {
            "messages": [ToolMessage(content=str(observation), tool_call_id=f"call_{uuid.uuid4().hex[:12]}", name=name)],
            "pending_action": None,
        }

    def route_after_agent(state: SupervisorAgentState) -> Literal["tools", "agent", "__end__"]:
        remaining = state.get("remaining_steps")
        if remaining is not None and remaining <= 1:
            logger.warning("remaining_steps 소진으로 종료합니다.")
            return END
        if state.get("pending_action"):
            return "tools"
        last = state["messages"][-1] if state.get("messages") else None
        if isinstance(last, HumanMessage):
            # 파싱 실패 피드백을 받은 경우 모델에 한 번 더 기회를 준다.
            return "agent"
        return END

    builder = StateGraph(SupervisorAgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "agent": "agent", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile()
