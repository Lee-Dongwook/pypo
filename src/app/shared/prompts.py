from __future__ import annotations

import logging
import sys
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

logger = logging.getLogger(__name__)

# Built-in prompts registered by the modules that use them.
_prompts: dict[str, Any] = {}
# Prompts supplied by configuration/deployment, keyed by name.
prompts: dict[str, Any] = {}


def prompt_push(name: str, prompt: Any) -> bool:
    """Register a built-in prompt. Returns ``False`` when the name already exists."""
    added = name not in _prompts
    _prompts[name] = prompt
    return added


def _prompt_load(inp: str | dict[str, Any], name: str | None = None) -> PromptTemplate | ChatPromptTemplate | str:
    """Build a LangChain prompt object from a TOML payload or its parsed form."""
    data_by_name: dict[str, Any] = tomllib.loads(inp) if isinstance(inp, str) else inp

    if name and name in data_by_name:
        data = data_by_name[name]
    else:
        name = next(iter(data_by_name))
        data = data_by_name[name]

    template_format = data.get("template_format")

    if "template" in data:
        kwargs: dict[str, Any] = {"template": data["template"]}
        if template_format:
            kwargs["template_format"] = template_format
        return PromptTemplate.from_template(**kwargs)

    if "prompt" in data:
        text: str = data["prompt"]
        return text

    try:
        system = data["system"]
        messages = [("system", system)]
        user = data.get("user")
        if user:
            messages.append(("human", user))
        kwargs = {}
        if template_format:
            kwargs["template_format"] = template_format
        prompt = ChatPromptTemplate.from_messages(messages, **kwargs)
    except Exception as e:
        raise ValueError(f"Fail to load prompt {name}") from e

    return prompt


def prompt_pull(name: str) -> Any:
    """Return the configured prompt for ``name``, falling back to the built-in one."""
    if name in prompts:
        if isinstance(prompts[name], dict):
            logger.info("Load user defined prompt '%s'...", name)
            try:
                prompt = _prompt_load(prompts, name)
            except Exception as e:
                logger.warning("Failed to load prompt %s: %s", name, e)
            else:
                prompts[name] = prompt
                return prompt
        else:
            return prompts[name]

    if name in _prompts:
        return _prompts[name]

    raise RuntimeError(f"No prompt found {name}")


__all__ = ["prompt_pull", "prompt_push", "prompts"]
