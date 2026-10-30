"""pypo가 일하는 격리된 작업 공간 (git worktree)과 검증."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_FILE_BLOCK = re.compile(r"^=== FILE: (\S+) ===\n(.*?)\n?^=== END ===", re.S | re.M)
_FENCE = re.compile(r"\A```[\w-]*\n(.*?)\n?```\s*\Z", re.S)
_OUTPUT_TAIL = 3000


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    output: str


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def create(repo: Path, base: str) -> Path:
    if base.startswith("origin/"):
        _git(repo, "fetch", "--quiet", "origin")
    path = Path(tempfile.mkdtemp(prefix="pypo-"))
    _git(repo, "worktree", "add", "--detach", "--force", str(path), base)
    return path


def remove(repo: Path, path: Path) -> None:
    _git(repo, "worktree", "remove", "--force", str(path))


def read(root: Path, path: str) -> str:
    file = root / path
    return file.read_text(encoding="utf-8") if file.exists() else "(아직 없는 새 파일)\n"


def references(root: Path, targets: tuple[str, ...]) -> list[str]:
    """수정할 파일이 import하는 `src` 모듈. 모델이 읽기만 하는 참고 자료다."""
    found: set[str] = set()
    for target in targets:
        file = root / target
        if file.suffix != ".py" or not file.exists():
            continue
        for module in re.findall(r"^from (src\.[\w.]+) import", file.read_text(encoding="utf-8"), re.M):
            candidate = module.replace(".", "/") + ".py"
            if (root / candidate).exists():
                found.add(candidate)
    return sorted(found - set(targets))


def parse_file_blocks(text: str) -> dict[str, str]:
    """모델 출력에서 `=== FILE: path === ... === END ===` 블록을 꺼낸다."""
    edits: dict[str, str] = {}
    for path, body in _FILE_BLOCK.findall(text):
        fenced = _FENCE.match(body.strip())
        content = fenced.group(1) if fenced else body
        edits[path] = content.rstrip("\n") + "\n"
    return edits


def apply(root: Path, edits: dict[str, str]) -> None:
    """이전 시도를 지우고 이번 수정만 적용한다."""
    _git(root, "reset", "--quiet", "--hard")
    _git(root, "clean", "-fdq")
    for path, content in edits.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")


def diff_lines(root: Path) -> int:
    _git(root, "add", "-A")
    total = 0
    for line in _git(root, "diff", "--cached", "--numstat").splitlines():
        added, removed, _ = line.split("\t", 2)
        total += int(added) + int(removed) if added != "-" else 0
    return total


def diff(root: Path) -> str:
    _git(root, "add", "-A")
    return _git(root, "diff", "--cached")


def run_checks(root: Path) -> list[Check]:
    """ruff와 pytest. 의존성을 다시 설치하지 않도록 지금 실행 중인 가상환경을 쓴다."""
    # ponytail: 웹(apps/, packages/)을 건드리는 이슈는 worktree에 node_modules가 없어 typecheck를 못 돌린다. M2 전에 해결.
    checks = []
    for name, args in [
        ("ruff", [sys.executable, "-m", "ruff", "check", "."]),
        ("pytest", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
    ]:
        result = _run(args, root)
        checks.append(Check(name, result.returncode == 0, (result.stdout + result.stderr)[-_OUTPUT_TAIL:]))
    return checks
