"""hermes 자율 에이전트의 독립 실행 루프.

docs/ARCHITECTURE.md의 Agent Runtime(도구 레지스트리 + ReAct 루프)과 같은 구성 요소로
돌아가는 최소 루프다. 감독자 LangGraph(`supervisor/workflow.py`)와 ReAct 프로토콜
(`react.py`)과 기본 도구 카탈로그(`tools/catalog.py`)를 공유한다.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.engine.models import resolve_chat_model
from src.app.shared.settings import settings

from .react import FINISH_ACTION, build_prompt, parse_action
from .tools.catalog import build_default_registry
from .tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Ollama 기본 문맥(4k)은 짧고, 16k는 16GB Mac에서 스왑을 일으킨다 (devbot과 같은 이유).
_OLLAMA_KWARGS = {"num_ctx": 12288, "num_predict": 1024}


def _default_model() -> Any:
    reference = settings.hermes_model
    extra = _OLLAMA_KWARGS if reference.startswith("ollama") else {}
    return resolve_chat_model(reference, **extra)


class AgentLoop:
    def __init__(self, max_steps: int = 5, model: Any | None = None, registry: ToolRegistry | None = None) -> None:
        if max_steps < 1:
            raise ValueError("max_steps는 1 이상이어야 합니다.")
        self.max_steps = max_steps
        self.model = model if model is not None else _default_model()
        self.registry = registry if registry is not None else build_default_registry()

    def run(self, task_description: str) -> bool:
        task_description = task_description.strip()
        if not task_description:
            raise ValueError("task_description이 비어 있습니다.")

        logger.info("hermes 태스크 시작: %s", task_description)
        history: list[str] = []

        for step in range(1, self.max_steps + 1):
            logger.info("--- Step %d / %d ---", step, self.max_steps)

            prompt = build_prompt(task_description, history, self.registry.schemas)
            raw_response = str(self.model.invoke(prompt).content).strip()

            action = parse_action(raw_response)
            if action is None:
                logger.warning("JSON 파싱 실패 (step %d): %s", step, raw_response)
                history.append(f"Step {step} Error: 응답을 JSON으로 파싱할 수 없습니다. {FINISH_ACTION}이 아니면 올바른 JSON 객체 하나만 응답하세요.")
                continue

            logger.info("Thought: %s\nAction: %s | Input: %s", action.thought, action.action, action.action_input)

            if action.action == FINISH_ACTION:
                answer = action.action_input.get("answer")
                logger.info("에이전트가 태스크 완료를 선언했습니다. answer=%s", answer)
                return True

            observation = self.registry.execute(action.action, action.action_input)
            logger.info("Observation: %s", observation)
            history.append(
                f"Step {step} - Thought: {action.thought}\n"
                f"Action: {action.action}({action.action_input})\n"
                f"Observation: {observation}\n"
            )

        logger.warning("최대 스텝(%d) 초과로 에이전트 루프가 종료되었습니다.", self.max_steps)
        return False
