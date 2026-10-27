from __future__ import annotations

import asyncio
import contextvars
import copy
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from langchain_core.messages import ChatMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import StreamWriter

from .utils import _bakes_an_identity, _build_copy
from ..model import Agent
from ..schemas import AgentResponse, AgentWorkflow
from ..protocols import SubAgentResolver, MCPResolver

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
