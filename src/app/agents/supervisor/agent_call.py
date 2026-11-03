"""서브에이전트 호출 도구.

감독자가 slug로 서브에이전트를 찾아(subscriptions·권한은 `SubAgentResolver`가 판단)
실행시키는 도구다. 실행 엔진(`SubAgentInvoker`)은 주입받는다. 감독자 그래프가
아직 workflow DSL 실행기를 갖지 못했으므로, 주입하지 않으면 조회까지만 하고
명확한 안내 메시지를 돌려준다.

각 호출에는 tool_call_id가 붙어 로그와 invoker로 전달된다.
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol

from ..model import Agent
from ..protocols import SubAgentResolver

logger = logging.getLogger(__name__)

AGENT_CALL = "agent_call"


class SubAgentInvoker(Protocol):
    async def __call__(self, agent: Agent, task: str, *, tool_call_id: str, caller_uuid: str | None) -> str: ...


def make_agent_call_tool(
    resolver: SubAgentResolver,
    *,
    caller_uuid: str | None = None,
    invoker: SubAgentInvoker | None = None,
):
    async def agent_call(slug: str, task: str) -> str:
        tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
        slug = slug.strip()
        task = task.strip()
        if not slug:
            return "서브에이전트 slug가 비어 있습니다."
        if not task:
            return "서브에이전트에게 시킬 작업(task)이 비어 있습니다."

        try:
            resolved = await resolver.resolve({slug}, user_uuid=caller_uuid)
        except Exception as exc:
            logger.warning("[%s] 서브에이전트 조회 실패: %s", tool_call_id, exc)
            return f"서브에이전트 조회에 실패했습니다 ({type(exc).__name__})."

        agent = resolved.get(slug)
        if agent is None:
            return f"서브에이전트를 찾을 수 없습니다: '{slug}'"

        if invoker is None:
            return f"서브에이전트 '{agent.name}'을(를) 찾았지만 실행 엔진이 설정되지 않았습니다."

        try:
            return await invoker(agent, task, tool_call_id=tool_call_id, caller_uuid=caller_uuid)
        except Exception as exc:
            logger.warning("[%s] 서브에이전트 '%s' 실행 실패: %s", tool_call_id, agent.slug, exc)
            return f"서브에이전트 '{agent.name}' 실행에 실패했습니다 ({type(exc).__name__})."

    return agent_call
