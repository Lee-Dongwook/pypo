"""pypo가 일하는 격리된 작업 공간 (git worktree)과 검증."""

from __future__ import annotations

import ast
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


def reference_snippets(root: Path, targets: tuple[str, ...], hint: str) -> str:
    """참고 모듈에서 필요한 정의만 발췌한다.

    이슈(`hint`)에 이름이 나온 최상위 함수·클래스와, 그 정의가 직접 쓰는 다른 정의까지 넣는다.
    모듈을 통째로 넣으면 입력이 길어져 작은 모델이 느려지고 흐려진다.
    """
    defs: dict[str, tuple[str, str]] = {}
    for path in references(root, targets):
        source = (root / path).read_text(encoding="utf-8")
        for node in ast.parse(source).body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                defs[node.name] = (path, ast.get_source_segment(source, node) or "")

    words = set(re.findall(r"\w+", hint))
    chosen = {name for name in defs if name in words}
    for name in list(chosen):
        chosen |= {other for other in defs if other != name and re.search(rf"\b{other}\b", defs[name][1])}

    by_path: dict[str, list[str]] = {}
    for name in defs:
        if name in chosen:
            path, code = defs[name]
            by_path.setdefault(path, []).append(code)
    return "\n\n".join(f"--- {path} (발췌) ---\n" + "\n\n\n".join(codes) for path, codes in by_path.items())


@dataclass(frozen=True)
class Edit:
    """파일 하나에 대한 찾아 바꾸기. `search`가 비어 있으면 파일 끝에 덧붙인다 (새 파일이면 새로 만든다)."""

    path: str
    search: str
    replace: str


class EditError(ValueError):
    pass


def parse_edits(text: str) -> list[Edit]:
    """모델 출력에서 `=== FILE ===` 블록을 꺼낸다. 블록 밖 글은 무시한다.

    SEARCH/REPLACE 표시가 있으면 찾아 바꾸기, 없으면 블록 안 코드 전체를 덧붙이기(새 파일이면 만들기)로 본다.
    7B 모델은 덧붙일 코드를 ```로 감싸서 내는 쪽을 훨씬 잘 지킨다.
    """
    edits: list[Edit] = []
    for path, body in _FILE_BLOCK.findall(text):
        if blocks := _EDIT_BLOCK.findall(body):
            edits += [Edit(path, search, replace) for search, replace in blocks]
        elif code := _unfence(body).strip("\n"):
            edits.append(Edit(path, "", code + "\n"))
    return edits


def _unfence(body: str) -> str:
    return "\n".join(line for line in body.splitlines() if not re.fullmatch(r"\s*```[\w-]*\s*", line))


def _append(text: str, addition: str) -> str:
    """파일 끝에 덧붙인다. 덧붙일 코드 맨 위의 import 줄은 파일의 import 영역 바로 뒤로 옮긴다."""
    lines = addition.splitlines(keepends=True)
    imports: list[str] = []
    while lines and (lines[0].startswith(("import ", "from ")) or not lines[0].strip()):
        line = lines.pop(0)
        if line.strip():
            imports.append(line)
    body = "".join(lines).lstrip("\n")
    if not text.strip():
        return "".join(imports) + ("\n\n" if imports and body else "") + body

    if imports:
        try:
            tops = [node for node in ast.parse(text).body if isinstance(node, ast.Import | ast.ImportFrom)]
        except SyntaxError:
            tops = []
        head = text.splitlines(keepends=True)
        at = tops[-1].end_lineno if tops else 0
        text = "".join(head[:at]) + "".join(imports) + "".join(head[at:])
    return text.rstrip("\n") + ("\n\n\n" + body if body.strip() else "\n")


def _replace_once(text: str, edit: Edit) -> str:
    if not edit.search.strip():
        return _append(text, edit.replace)
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
    """원본으로 되돌린 뒤 이번 수정을 쓰고, 기계적으로 고칠 수 있는 것은 ruff가 고친다.

    import 정렬·병합, 쓰지 않는 import 같은 것은 모델에게 다시 시키면 시간만 들고 같은 답이 나온다.
    ruff가 안전하다고 표시한 수정만 쓰고, 고친 파일에만 적용한다.
    """
    reset(root)
    for path, content in edits.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
    if python := [path for path in edits if path.endswith(".py")]:
        _run([sys.executable, "-m", "ruff", "check", "--fix", "--quiet", *python], root)


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
