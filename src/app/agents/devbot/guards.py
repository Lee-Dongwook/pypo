"""pypo가 넘을 수 없는 선. 프롬프트가 아니라 여기서 강제한다 (docs/DEVBOT.md 7절).

pypo는 이 파일을 수정할 수 없다.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path

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
MAX_OPEN_PRS = 3
BRANCH_PREFIX = "pypo/"


def branch_name(number: int, title: str) -> str:
    """`pypo/<이슈번호>-<slug>`. pypo는 이 이름으로만 푸시한다."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.removeprefix("[pypo]").lower()).strip("-")[:40].strip("-")
    return f"{BRANCH_PREFIX}{number}-{slug or 'task'}"


def _test_functions(source: str) -> set[str]:
    """클래스 안 메서드까지 포함한 `test_` 함수 이름. 문법 오류면 `SyntaxError`."""
    return {
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_")
    }


def removed_tests(before: str, after: str) -> list[str]:
    """수정 후 사라진 테스트 함수. 테스트를 지우면 pytest는 실패하지 않으므로 따로 막는다.

    수정 후 코드가 문법 오류면 판단하지 않는다. pytest가 오류를 그대로 보여 주는 편이 모델에게 낫다.
    """
    try:
        return sorted(_test_functions(before) - _test_functions(after))
    except SyntaxError:
        return []


def normalize(path: str) -> str:
    return path.strip().strip("`").removeprefix("./")


def _resolve(raw: str, root: Path) -> Path | None:
    """저장소 안의 실제 경로. `..`, 절대 경로, 밖을 가리키는 심볼릭 링크는 None."""
    resolved = (root / normalize(raw)).resolve()
    return resolved if resolved.is_relative_to(root.resolve()) else None


def path_violations(paths: Iterable[str], targets: Iterable[str], root: Path) -> list[str]:
    """수정하려는 경로 중 허용되지 않는 것과 그 이유. 비어 있으면 통과.

    허용: 이슈에 지정된 파일, 아직 없는 `tests/test_*.py` 새 파일.
    """
    allowed = {_resolve(target, root) for target in targets} - {None}
    problems: list[str] = []
    for raw in paths:
        resolved = _resolve(raw, root)
        if resolved is None or resolved == root.resolve():
            problems.append(f"{raw}: 저장소 밖 경로")
            continue
        path = resolved.relative_to(root.resolve()).as_posix()
        if any(path == rule or path.startswith(rule) for rule in FORBIDDEN):
            problems.append(f"{path}: 수정 금지 경로")
        elif resolved not in allowed and not (fnmatch(path, NEW_TEST_PATTERN) and not resolved.exists()):
            problems.append(f"{path}: 이슈에 지정되지 않은 파일")
    return problems


def diff_line_violations(diff_text: str) -> list[str]:
    """`git diff`의 추가·삭제 줄 수가 상한을 넘으면 그 이유."""
    changed = sum(
        1
        for line in diff_text.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )
    if changed > MAX_DIFF_LINES:
        return [f"변경이 {changed}줄로 상한 {MAX_DIFF_LINES}줄을 넘습니다. 필요한 부분만 바꾸세요."]
    return []
