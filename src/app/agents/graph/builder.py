from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..model import Agent
from ..protocols import MCPResolver, SubAgentResolver
from ..schemas import AgentResponse, AgentWorkflow
from .utils import _bakes_an_identity, _build_copy

if TYPE_CHECKING:
    from ...user.schemas import UserRead

logger = logging.getLogger(__name__)


class GraphBuilder:
    def __init__(
        self,
        agent_model: Agent | AgentResponse,
        resolver: SubAgentResolver | None = None,
        mcp_resolver: MCPResolver | None = None,
        ambient_mcp: bool = True,
        caller: UserRead | None = None,
    ) -> None:
        self.ambient_mcp = ambient_mcp
        self.caller = caller
        self.workflow = None if _bakes_an_identity(agent_model) else AgentWorkflow.model_validate(agent_model.workflow)
        self.agent_model = _build_copy(agent_model)
