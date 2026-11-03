"""hermes가 공통으로 쓰는 ReAct(생각→행동→관찰) 프로토콜.

소형 로컬 모델도 안정적으로 따를 수 있게 도구 호출을 JSON 한 조각으로만 받는다.
독립 실행 루프(`agent_loop.py`)와 감독자 LangGraph(`supervisor/workflow.py`)가
같은 형식과 파서를 공유한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

FINISH_ACTION = "finish"

REACT_INSTRUCTIONS = (
    "반드시 다음 JSON 형식으로만 응답하라:\n"
    "{\n"
    '  "thought": "현재 상황 분석과 다음 행동 계획",\n'
    '  "action": "도구 이름 또는 finish",\n'
    '  "action_input": { "인자 이름": "값" }\n'
    "}\n"
    '작업이 끝나면 action을 "finish"로 하고, action_input에 {"answer": "사용자에게 보여 줄 최종 답변"}를 담아라.'
)

@dataclass(frozen=True)
class ReactAction:
    thought: str
    action: str
    action_input: dict[str, Any]


def _coerce_action(obj: Any) -> ReactAction | None:
    if not isinstance(obj, dict):
        return None
    action = obj.get("action")
    if not isinstance(action, str) or not action.strip():
        return None
    action_input = obj.get("action_input", {})
    if not isinstance(action_input, dict):
        return None
    thought = obj.get("thought", "")
    return ReactAction(
        thought=str(thought).strip(),
        action=action.strip(),
        action_input=action_input,
    )


def parse_action(raw: str) -> ReactAction | None:
    """모델 응답에서 첫 번째로 파싱되는 JSON 객체를 ReactAction으로 바꾼다.

    코드 펜스나 설명 문장이 섞여 있어도 된다. `{` 위치마다 디코딩을 시도해
    가장 먼저 올바른 형식(action이 비어 있지 않은 문자열, action_input이 객체)
    으로 파싱되는 조각을 돌려준다. 없으면 None.
    """
    text = raw.strip()
    if not text:
        return None

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if (action := _coerce_action(obj)) is not None:
            return action
    return None


def render_tool_specs(specs: list[dict[str, Any]]) -> str:
    return json.dumps(specs, ensure_ascii=False, indent=2)


def build_prompt(task: str, history: list[str], tool_specs: list[dict[str, Any]]) -> str:
    tools_desc = render_tool_specs(tool_specs)
    history_text = "\n".join(history) if history else "(없음)"
    return (
        "너는 pypo의 자율 에이전트이다. 주어진 목표를 달성하기 위해 아래 도구들을 활용해라.\n"
        f"Available Tools:\n{tools_desc}\n\n"
        f"{REACT_INSTRUCTIONS}\n\n"
        f"Task: {task}\n\n"
        f"History:\n{history_text}\n\n"
        "Response:"
    )
