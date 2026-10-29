from __future__ import annotations

import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from ...user.schemas import UserRead

logger = logging.getLogger(__name__)


async def build_supervisor_graph(
    config: RunnableConfig | None = None, caller: UserRead | None = None
) -> CompiledStateGraph:
    """Compile the supervisor graph.

    WIP: the node set and the tool loop are not defined yet, so this raises instead
    of returning a half-built graph. `config` carries runtime settings and `caller`
    is the authenticated user that limits tool/agent visibility.
    """
    raise NotImplementedError("supervisor graph is not built yet")
