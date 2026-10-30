"""pypo가 넘을 수 없는 선. 프롬프트가 아니라 여기서 강제한다 (docs/DEVBOT.md 7절).

pypo는 이 파일을 수정할 수 없다.
"""

from __future__ import annotations

import re
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


def removed_tests(before: str, after: str) -> list[str]:
    """수정 후 사라진 테스트 함수. 테스트를 지우면 pytest는 실패하지 않으므로 따로 막는다."""
    pattern = re.compile(r"^(?:async )?def (test_\w+)", re.M)
    return sorted(set(pattern.findall(before)) - set(pattern.findall(after)))


def normalize(path: str) -> str:
    return path.strip().strip("`").removeprefix("./")


def path_violations(paths: Iterable[str], targets: Iterable[str], root: Path) -> list[str]:
    """수정하려는 경로 중 허용되지 않는 것과 그 이유. 비어 있으면 통과.

    허용: 이슈에 지정된 파일, 아직 없는 `tests/test_*.py` 새 파일.
    """
    allowed = {normalize(target) for target in targets}
    problems: list[str] = []
    for raw in paths:
        path = normalize(raw)
        pure = PurePosixPath(path)
        if not path or pure.is_absolute() or ".." in pure.parts:
            problems.append(f"{raw}: 저장소 밖 경로")
        elif any(path == rule or path.startswith(rule) for rule in FORBIDDEN):
            problems.append(f"{path}: 수정 금지 경로")
        elif path not in allowed and not (fnmatch(path, NEW_TEST_PATTERN) and not (root / path).exists()):
            problems.append(f"{path}: 이슈에 지정되지 않은 파일")
    return problems
