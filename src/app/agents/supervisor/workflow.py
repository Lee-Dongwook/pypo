from __future__ import annotations

import logging
import re
import textwrap
import time
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from ...user.schemas import UserRead

if TYPE_CHECKING:
    from collections.abc import Callable

logging = logging.getLogger(__name__)

async def build_supervisor_graph(
    config: RunnableConfig | None = None, caller: UserRead | None = None
) -> CompiledStateGraph:

    configurable = config.get("configurable", {})
    start_time = time.perf_counter()

    # WIP
