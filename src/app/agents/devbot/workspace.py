"""pypo가 일하는 격리된 작업 공간 (git worktree)과 검증."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_FILE_BLOCK = re.compile(r"^=== FILE: (\S+) ===\n(.*?)^=== END ===", re.S | re.M)
_EDIT_BLOCK = re.compile(r"^<<<<<<< SEARCH\n(.*?)^=======\n(.*?)^>>>>>>> REPLACE", re.S | re.M)
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


@dataclass(frozen=True)
class Edit:
    """파일 하나에 대한 찾아 바꾸기. `search`가 비어 있으면 파일 끝에 덧붙인다 (새 파일이면 새로 만든다)."""

    path: str
    search: str
    replace: str


class EditError(ValueError):
    pass


def parse_edits(text: str) -> list[Edit]:
    """모델 출력에서 `=== FILE ===` 안의 SEARCH/REPLACE 블록을 꺼낸다. 블록 밖 글은 무시한다."""
    return [
        Edit(path, search, replace)
        for path, body in _FILE_BLOCK.findall(text)
        for search, replace in _EDIT_BLOCK.findall(body)
    ]


def _replace_once(text: str, edit: Edit) -> str:
    if not edit.search.strip():
        return text + ("\n" if text and not text.endswith("\n") else "") + edit.replace
    if (count := text.count(edit.search)) == 1:
        return text.replace(edit.search, edit.replace, 1)
    if count > 1:
        raise EditError(f"{edit.path}: SEARCH가 {count}곳과 일치함. 앞뒤 줄을 더 넣어 한 곳만 가리키게 할 것")

    # 작은 모델은 줄 끝 공백을 자주 틀린다. 줄 끝 공백만 무시하고 한 번 더 찾는다.
    lines = text.splitlines(keepends=True)
    wanted = [line.rstrip() for line in edit.search.splitlines()]
    stripped = [line.rstrip() for line in lines]
    hits = [i for i in range(len(lines) - len(wanted) + 1) if stripped[i : i + len(wanted)] == wanted]
    if len(hits) != 1:
        first = wanted[0] if wanted else ""
        raise EditError(
            f"{edit.path}: SEARCH가 현재 파일과 일치하지 않음 (첫 줄: {first!r}). 현재 내용을 그대로 복사할 것"
        )
    i = hits[0]
    return "".join(lines[:i]) + edit.replace + "".join(lines[i + len(wanted) :])


def apply_edits(root: Path, edits: list[Edit]) -> dict[str, str]:
    """찾아 바꾸기를 순서대로 적용한 파일별 새 내용. 하나라도 안 맞으면 `EditError`."""
    contents: dict[str, str] = {}
    for edit in edits:
        if edit.path not in contents:
            file = root / edit.path
            contents[edit.path] = file.read_text(encoding="utf-8") if file.exists() else ""
        contents[edit.path] = _replace_once(contents[edit.path], edit)
    return contents


def reset(root: Path) -> None:
    """이전 시도의 수정을 모두 지운다. 모델은 항상 원본을 보고 SEARCH를 쓰기 때문이다."""
    _git(root, "reset", "--quiet", "--hard")
    _git(root, "clean", "-fdq")


def apply(root: Path, edits: dict[str, str]) -> None:
    reset(root)
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


def missing_tests(root: Path, names: list[str]) -> list[str]:
    """이슈가 이름으로 요구한 테스트 중 `tests/`에 없는 것."""
    source = "\n".join(file.read_text(encoding="utf-8") for file in (root / "tests").rglob("test_*.py"))
    return [name for name in names if not re.search(rf"^(?:async )?def {name}\b", source, re.M)]


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
