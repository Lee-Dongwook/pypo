from __future__ import annotations

from typing import TypedDict


class GraphConfig(TypedDict, total=False):
    """Values the engine graphs read from ``RunnableConfig["configurable"]``.

    ``search_model`` accepts either a provider name (``"openai"``) or a
    ``"provider:model"`` reference (``"openai:gpt-4.1-mini"``). The provider
    alone is resolved to the default model for that provider.
    """

    search_model: str
