from typing import Any, Literal
import typing_extensions

class _TaskModels(typing_extensions.TypedDict, total=False):
    search_model: Literal["openai", "gemini", "anthropic"] | str    

class GraphConfig(_TaskModels, total=False):
    configurable: dict[str, Any]
    thread_id: str
