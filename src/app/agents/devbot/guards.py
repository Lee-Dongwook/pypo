"""pypo가 넘을 수 없는 선. 프롬프트가 아니라 여기서 강제한다 (docs/DEVBOT.md 7절).

pypo는 이 파일을 수정할 수 없다.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

FORBIDDEN = (
    "migrations/",
    ".github/",
    ".env",
    "uv.lock",
    "pnpm-lock.yaml",
    "agent/persona.md",
    "agent/evals/",
    "src/app/agents/devbot/guards.py",
)
NEW_TEST_PATTERN = "tests/test_*.py"
MAX_ATTEMPTS = 3
MAX_DIFF_LINES = 400

def extract_test_functions(code_content: str) -> set[str]:
    """AST를 사용하여 최상위 및 클래스 내 테스트 함수 정확히 추출"""
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return set()
    
    test_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_funcs.add(node.name)
    return test_funcs

def removed_tests(before: str, after: str) -> list[str]:
    """수정 후 사라진 테스트 함수. 테스트를 지우면 pytest는 실패하지 않으므로 따로 막는다."""
    before_tests = extract_test_functions(before)
    after_tests = extract_test_functions(after)
    return sorted(before_tests - after_tests)


def normalize_and_validate_path(raw_path: str, root: Path) -> Path | None:
    try:
        cleaned = raw_path.strip().strip("`").removeprefix("./")
        resolved = (root / cleaned).resolve()

        if not resolved.is_relative_to(root.resolve()):
            return None
        return resolved
    except (ValueError, RuntimeError):
        return None


def path_violations(paths: Iterable[str], targets: Iterable[str], root: Path) -> list[str]:
    """수정하려는 경로 중 허용되지 않는 것과 그 이유 검증."""
    allowed = {normalize_and_validate_path(t, root) for t in targets}
    allowed = {p for p in allowed if p is not None}

    problems: list[str] = []
    for raw in paths:
        resolved_path = normalize_and_validate_path(raw, root)
        if resolved_path is None:
            problems.append(f"{raw}: 저장소 밖 경로 또는 잘못된 경로")
            continue
        
        rel_path = resolved_path.relative_to(root.resolve()).as_posix()

        if any(rel_path == rule or rel_path.startswith(rule) for rule in FORBIDDEN):
            problems.append(f"{rel_path}: 수정 금지 경로")
        elif resolved_path not in allowed and not (fnmatch(rel_path, NEW_TEST_PATTERN) and not resolved_path.exists()):
            problems.append(f"{rel_path}: 이슈에 지정되지 않은 파일")

    return problems

def diff_line_violations(diff_text: str) -> list[str]:
    """변경 사항의 총 라인 수가 MAX_DIFF_LINES를 초과하는지 검사."""
    added_lines = 0
    deleted_lines = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted_lines += 1
            
    total_changed = added_lines + deleted_lines
    if total_changed > MAX_DIFF_LINES:
        return [f"변경 밀도 초과: 총 {total_changed}줄 변경됨 (허용 최대: {MAX_DIFF_LINES}줄)"]
    return []
