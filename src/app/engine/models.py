from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from src.app.shared.settings import settings

# `init_chat_model` expects the package name, while the graph config exposes
# user-facing provider names.
_PROVIDER_ALIASES = {
    "gemini": "google_genai",
    "google": "google_genai",
}

_DEFAULT_MODEL_BY_PROVIDER = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-5",
    "google_genai": "gemini-2.5-flash",
}


def _model_reference(config: RunnableConfig) -> str:
    configurable = config.get("configurable") or {}
    return str(configurable.get("search_model") or settings.search_model)


def resolve_chat_model(reference: str, **kwargs: object) -> BaseChatModel:
    """Build a chat model from ``"provider:model"``.

    A bare provider name uses that provider's default model. The provider
    integration package (for example ``langchain-openai``) must be installed.
    Extra keyword arguments go to the provider's chat model class.
    """
    reference = reference.strip()
    provider, separator, model = reference.partition(":")
    provider = _PROVIDER_ALIASES.get(provider.strip(), provider.strip())

    if not separator or not model:
        model = _DEFAULT_MODEL_BY_PROVIDER.get(provider, "")

    if not provider or not model:
        raise ValueError(
            f"cannot resolve chat model {reference!r}; use 'provider:model' or one of the supported providers"
        )

    return init_chat_model(model, model_provider=provider, temperature=0, **kwargs)


def get_search_model(config: RunnableConfig) -> BaseChatModel:
    """Build the chat model configured for the search subgraph.

    Resolution order is ``config["configurable"]["search_model"]`` and then
    ``settings.search_model``.
    """
    return resolve_chat_model(_model_reference(config))


__all__ = ["get_search_model", "resolve_chat_model"]
