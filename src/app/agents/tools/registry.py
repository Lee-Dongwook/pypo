"""에이전트 도구 레지스트리.

도구는 `register` 데코레이터로 이름·설명과 함께 등록한다. 레지스트리가 타입
힌트에서 JSON Schema를 만들어 LLM에 보여 줄 명세(`schemas`)를 만든다. 실행
결과와 오류는 모두 LLM이 읽는 관찰(observation) 문자열로 바뀐다.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

logger = logging.getLogger(__name__)

_JSON_TYPES: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _json_type(annotation: Any) -> str | None:
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        # Optional[X]처럼 Union이면 None이 아닌 첫 번째 타입을 따른다.
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            if (resolved := _json_type(arg)) is not None:
                return resolved
        return None
    return _JSON_TYPES.get(origin or annotation)


def _parameters_schema(func: Any) -> dict[str, Any]:
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in inspect.signature(func).parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        json_type = _json_type(hints.get(name, param.annotation))
        properties[name] = {"type": json_type} if json_type else {}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Any

    @property
    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


def validate_kwargs(spec: ToolSpec, kwargs: Any) -> str | None:
    """인자가 dict이고 시그니처에 맞으면 None, 아니면 LLM에 돌려줄 한국어 오류 메시지."""
    if not isinstance(kwargs, dict):
        return f"도구 '{spec.name}'의 action_input은 객체여야 합니다."
    try:
        inspect.signature(spec.func).bind(**kwargs)
    except TypeError as exc:
        return f"도구 '{spec.name}' 인자가 올바르지 않습니다: {exc}"
    return None


def error_message(name: str, exc: Exception) -> str:
    return f"도구 '{name}' 실행 중 {type(exc).__name__} 오류가 발생했습니다: {exc}"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, description: str):
        name = name.strip()
        description = description.strip()
        if not name:
            raise ValueError("도구 이름이 비어 있습니다.")
        if not description:
            raise ValueError(f"도구 '{name}'의 설명이 비어 있습니다.")

        def decorator(func: Any) -> Any:
            if name in self._tools:
                raise ValueError(f"이미 등록된 도구입니다: '{name}'")
            self._tools[name] = ToolSpec(name=name, description=description, parameters=_parameters_schema(func), func=func)
            return func

        return decorator

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [spec.schema for spec in self._tools.values()]

    def specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def execute(self, name: str, kwargs: Any) -> Any:
        spec = self._tools.get(name)
        if spec is None:
            return f"알 수 없는 도구입니다: '{name}'"
        if (message := validate_kwargs(spec, kwargs)) is not None:
            return message
        try:
            return spec.func(**kwargs)
        except Exception as exc:
            logger.warning("도구 '%s' 실행 실패: %s", name, exc)
            return error_message(name, exc)
