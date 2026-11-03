"""기본으로 제공되는 도구들."""

from __future__ import annotations

from typing import Any

from ..validators.ast_gate import ASTGatekeeper
from .registry import ToolRegistry

_gate = ASTGatekeeper()


def run_python_test(code_string: str) -> str:
    is_valid, message = _gate.validate_code(code_string)
    if not is_valid:
        return f"AST 검증 실패: {message}"

    namespace: dict[str, Any] = {}
    try:
        exec(code_string, {}, namespace)  # noqa: S102 - AST 관문을 통과한 코드만 실행한다.
        return "실행 성공: 코드가 오류 없이 실행되었습니다."
    except Exception as exc:
        return f"실행 실패 ({type(exc).__name__}): {exc}"


def register_builtin_tools(registry: ToolRegistry) -> ToolRegistry:
    registry.register(
        "run_python_test",
        "파이썬 코드를 받아 AST 관문으로 검증한 뒤 격리된 네임스페이스에서 실행하고 결과를 반환합니다.",
    )(run_python_test)
    return registry
