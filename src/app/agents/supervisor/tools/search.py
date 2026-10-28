from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Annotated, Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.errors import GraphBubbleUp
from pydantic import BeforeValidator

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

TOOL_SEARCH = "tool_search"
TOOL_DESCRIBE = "tool_describe"
