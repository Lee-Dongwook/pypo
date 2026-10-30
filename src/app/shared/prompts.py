import logging
import os
import sys
import textwrap
from typing import Any, Literal

import tomli_w


if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from langchain_core.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
)

logger = logging.getLogger(__name__)

_prompts: dict[str, Any] = {}
prompts: dict[str, Any] = {}

def prompt_push(name: str, prompt: Any) -> bool:
    ret = True
    if name in _prompts:
        ret = False
    _prompts[name] = prompt

    return ret

def _prompt_load(inp: str | dict[str, Any], name: str | None = None) -> PromptTemplate | ChatPromptTemplate | str:
    prompts: dict[str, Any] = tomllib.loads(inp) if isinstance(inp, str) else inp

    if name and name in prompts:
        data = prompts[name]
    else:
        name = list(prompts.keys())[0]
        data = prompts[name]

    template_format = data.get("template_format", None)

    if "template" in data:
        kwargs: dict[str, Any] = {"template": data["template"]}
        if template_format:
            kwargs["template_format"] = template_format
        return PromptTemplate.from_template(**kwargs)
    elif "prompt" in data:
        text: str = data["prompt"]
        return text

    try:
        system = data["system"]
        messages = [("system", system)]
        user = data.get("user", None)
        if user:
            messages += [("human", user)]
        kwargs = {}
        if template_format:
            kwargs["template_format"] = template_format
        prompt = ChatPromptTemplate.from_messages(messages, **kwargs)
    except Exception as e:
        raise ValueError(f"Fail to load prompt {name}") from e

    return prompt

def prompt_pull(name: str) -> Any:
    if name in prompts:
        if isinstance(prompts[name], dict):
            logger.info(f"Load user defined prompt '{name}'...")
            try:
                prompt = _prompt_load(prompts, name)
            except Exception as e:
                logger.warning(f"Failed to load prompt {name}: {e}")
            else:
                prompts[name] = prompt
                return prompt
        else:
            return prompts[name]

    if name in _prompts:
        return _prompts[name]

    raise RuntimeError(f"No prompt found {name}")
