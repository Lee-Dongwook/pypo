"""pypo가 일하는 격리된 작업 공간 (git worktree)과 검증."""

from __future__ import annotations

import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .guards import BRANCH_PREFIX, normalize

_FILE_BLOCK = re.compile(r"^=== FILE: (\S+) ===\n(.*?)^=== END ===", re.S | re.M)
_DELETE_LINE = re.compile(r"^DELETE (\w+)[ \t]*\n?", re.M)
_MOVE_LINE = re.compile(r"^MOVE (\w+) TO (\S+)[ \t]*\n?", re.M)
_EDIT_BLOCK = re.compile(r"^<<<<<<< SEARCH\n(.*?)^=======\n(.*?)^>>>>>>> REPLACE", re.S | re.M)
_OUTPUT_TAIL = 3000
MAX_FILE_CHARS = 8000
"""이 값보다 긴 파일만 이슈가 필요로 한 정의를 발췌해 LLM 입력에 쓴다. 작은 파일은 통째로 보낸다."""


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


def file_content(root: Path, path: str, hint: str) -> str:
    """수정 대상 파일 내용. 파일이 크면 이슈가 필요로 한 부분만 발췌해 돌려준다.

    LLM 입력을 줄이는 게 목적이고, 검증이 정확성을 정하므로 발췌할 게 없으면 원본을 돌려준다.
    """
    file = root / path
    if not file.exists():
        return "(아직 없는 새 파일)\n"
    return excerpt(file.read_text(encoding="utf-8"), hint)


def excerpt(source: str, hint: str) -> str:
    """큰 파일은 이슈가 필요로 한 정의만 발췌해 반환한다. 작거나 발췌할 게 없으면 원본을 돌려준다."""
    if len(source) <= MAX_FILE_CHARS:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    defs = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }
    chosen = {name for name in defs if name in set(re.findall(r"\w+", hint))}
    for name in list(chosen):
        chosen |= {
            other
            for other in defs
            if other not in chosen and re.search(rf"\b{other}\b", ast.get_source_segment(source, defs[name]) or "")
        }
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and node.name in chosen
    ]
    parts = [ast.get_source_segment(source, node) or "" for node in selected]
    text = "\n\n".join(parts)
    if not parts or len(text) >= len(source):
        return source
    imports = "\n".join(
        ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.Import | ast.ImportFrom)
    ).rstrip("\n")
    return f"{imports}\n\n{text}\n" if imports else text + "\n"


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
    """파일 하나에 대한 찾아 바꾸기. `search`가 비어 있으면 파일 끝에 덧붙인다 (새 파일이면 새로 만든다).

    `delete`가 있으면 그 이름의 최상위 함수·클래스를 통째로 지운다. `move_to`도 있으면 지운 정의를 그 파일 끝에
    붙이고, 원래 파일에는 새 위치에서 가져오는 import를 남긴다.
    """

    path: str
    search: str
    replace: str
    delete: str = ""
    move_to: str = ""


class EditError(ValueError):
    pass


def parse_edits(text: str) -> list[Edit]:
    """모델 출력에서 `=== FILE ===` 블록을 꺼낸다. 블록 밖 글은 무시한다.

    SEARCH/REPLACE 표시가 있으면 찾아 바꾸기, 없으면 블록 안 코드 전체를 덧붙이기(새 파일이면 만들기)로 본다.
    `DELETE 이름` 줄은 정의 지우기, `MOVE 이름 TO 경로` 줄은 정의 옮기기다. 7B 모델은 큰 정의를 그대로 베끼지 못해서
    이름만 받고 코드는 pypo가 옮긴다.
    7B 모델은 덧붙일 코드를 ```로 감싸서 내는 쪽을 훨씬 잘 지킨다. 모델이 쓴 줄 끝 공백은 지운다.
    """
    edits: list[Edit] = []
    for path, body in _FILE_BLOCK.findall(text):
        edits += [Edit(path, "", "", name, normalize(target)) for name, target in _MOVE_LINE.findall(body)]
        edits += [Edit(path, "", "", name) for name in _DELETE_LINE.findall(body)]
        body = _DELETE_LINE.sub("", _MOVE_LINE.sub("", body))
        if blocks := _EDIT_BLOCK.findall(body):
            edits += [Edit(path, search, _strip_trailing(replace)) for search, replace in blocks]
        elif code := _unfence(body).strip("\n"):
            edits.append(Edit(path, "", _strip_trailing(code) + "\n"))
    return _deletes_retyped_elsewhere_are_moves(edits)


def _deletes_retyped_elsewhere_are_moves(edits: list[Edit]) -> list[Edit]:
    """한 파일에서 DELETE하고 다른 파일에 같은 이름을 다시 쳐 붙이면 옮기기로 본다.

    7B 모델은 옮기기를 늘 이렇게 하고, 다시 친 코드에 없던 검증을 지어 넣기도 한다 (#3).
    그래서 다시 친 정의는 버리고 원본을 MOVE로 옮긴다. 다시 친 블록에 함께 쓴 import도 버린다 (순환 import를 만들곤 한다).
    """
    deleted = {edit.delete: edit.path for edit in edits if edit.delete and not edit.move_to}
    targets: dict[str, str] = {}
    result: list[Edit] = []
    for edit in edits:
        if edit.search or edit.delete:
            result.append(edit)
            continue
        retyped = {name for name in _top_level_names(edit.replace) if deleted.get(name, edit.path) != edit.path}
        if not retyped:
            result.append(edit)
            continue
        targets.update(dict.fromkeys(retyped, edit.path))
        rest = edit.replace
        for name in retyped:
            rest = _cut(rest, Edit(edit.path, "", "", name))[0]
        if _top_level_names(rest) or any(
            not isinstance(node, ast.Import | ast.ImportFrom) for node in ast.parse(rest).body
        ):
            result.append(Edit(edit.path, "", rest))
    return [Edit(e.path, "", "", e.delete, targets[e.delete]) if e.delete in targets and not e.move_to else e
            for e in result]


def _strip_trailing(code: str) -> str:
    return re.sub(r"[ \t]+$", "", code, flags=re.M)


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


def _cut(text: str, edit: Edit) -> tuple[str, str]:
    """이름이 `edit.delete`인 최상위 함수·클래스를 잘라 (남은 내용, 잘라 낸 코드)로 돌려준다."""
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise EditError(f"{edit.path}: 문법 오류가 있어 {edit.delete}를 지울 수 없음 ({error.msg})") from error
    kinds = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    nodes = [node for node in tree.body if isinstance(node, kinds) and node.name == edit.delete]
    if len(nodes) != 1:
        raise EditError(f"{edit.path}: 지울 최상위 함수·클래스 {edit.delete}가 {len(nodes)}개 있음. 정확한 이름을 쓸 것")
    node = nodes[0]
    start = min([node.lineno, *(d.lineno for d in node.decorator_list)]) - 1
    lines = text.splitlines(keepends=True)
    rest = re.sub(r"\n{4,}", "\n\n\n", "".join(lines[:start] + lines[node.end_lineno :]))
    return rest, "".join(lines[start : node.end_lineno])


def _import_line(source: str, target: str, name: str) -> str:
    """`source` 파일에서 `target` 파일의 `name`을 가져오는 import. 같은 폴더면 상대 import."""
    source_path, target_path = Path(source), Path(target)
    if source_path.parent == target_path.parent:
        return f"from .{target_path.stem} import {name}\n"
    return f"from {'.'.join(target_path.with_suffix('').parts)} import {name}\n"


def _replace_once(text: str, edit: Edit) -> str:
    if edit.delete:
        return _cut(text, edit)[0]
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


def _top_level_names(code: str) -> set[str]:
    try:
        body = ast.parse(code).body
    except SyntaxError:
        return set()
    return {node.name for node in body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)}


def rewritten_definitions(root: Path, edits: list[Edit]) -> list[str]:
    """덧붙이기 블록이 파일에 이미 있는 함수·클래스를 다시 쓴 경우. 7B는 옮기기를 파일 통째로 다시 쓰기로 착각한다."""
    problems = []
    for edit in edits:
        file = root / edit.path
        if edit.search or edit.delete or not file.exists():
            continue
        if again := sorted(_top_level_names(edit.replace) & _top_level_names(file.read_text(encoding="utf-8"))):
            problems.append(
                f"{edit.path}: 이미 있는 {', '.join(again)}를 다시 씀. 덧붙이기에는 새 코드만 쓴다. "
                "정의를 다른 파일로 옮길 때는 원래 파일 블록에 `MOVE 이름 TO <새 경로>` 한 줄만 쓴다"
            )
    return problems


def apply_edits(root: Path, edits: list[Edit]) -> dict[str, str]:
    """찾아 바꾸기를 순서대로 적용한 파일별 새 내용. 하나라도 안 맞으면 `EditError`."""
    contents: dict[str, str] = {}
    for edit in edits:
        for path in (edit.path, edit.move_to):
            if path and path not in contents:
                file = root / path
                contents[path] = file.read_text(encoding="utf-8") if file.exists() else ""
        if edit.move_to:
            rest, code = _cut(contents[edit.path], edit)
            contents[edit.move_to] = _append(contents[edit.move_to], code)
            contents[edit.path] = _append(rest, _import_line(edit.path, edit.move_to, edit.delete))
        else:
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


def diff(root: Path) -> str:
    _git(root, "add", "-A")
    return _git(root, "diff", "--cached")


def push(root: Path, branch: str, message: str) -> None:
    """검증을 통과한 변경을 pypo 이름으로 커밋하고 `pypo/*` 브랜치로 푸시한다. 이미 있는 브랜치는 덮어쓰지 않는다."""
    if not branch.startswith(BRANCH_PREFIX):
        raise ValueError(f"{branch}: pypo는 {BRANCH_PREFIX}* 브랜치에만 푸시합니다")
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=pypo-agent", "-c", "user.email=pypo-agent@noreply.localhost", "commit", "-qm", message)
    _git(root, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")


def missing_tests(root: Path, names: list[str]) -> list[str]:
    """이슈가 이름으로 요구한 테스트 중 `tests/`에 없는 것."""
    source = "\n".join(file.read_text(encoding="utf-8") for file in (root / "tests").rglob("test_*.py"))
    return [name for name in names if not re.search(rf"^(?:async )?def {name}\b", source, re.M)]


# 검증용 이미지. torch는 코드 어디서도 쓰지 않는데 리눅스에서는 CUDA 패키지(수 GB)를 끌고 와서 뺀다.
_SANDBOX_DOCKERFILE = """\
FROM ghcr.io/astral-sh/uv:0.12.23-python3.13-trixie-slim
ENV UV_PROJECT_ENVIRONMENT=/venv UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project $(grep -oE '^name = "(torch|triton|nvidia-[^"]*|cuda-[^"]*)"' uv.lock \
    | cut -d'"' -f2 | sed 's/^/--no-install-package /')
# devbot 자신의 테스트가 git worktree를 쓴다.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
"""
_CHECK_TIMEOUT_SECONDS = 300


def sandbox_image(repo: Path) -> str:
    """의존성을 미리 깐 검증용 이미지 태그. `uv.lock`이 바뀔 때만 새로 빌드한다. Docker가 없으면 `RuntimeError`."""
    lock = (repo / "uv.lock").read_bytes()
    tag = f"pypo-sandbox:{hashlib.sha256(lock + _SANDBOX_DOCKERFILE.encode()).hexdigest()[:12]}"
    if _run(["docker", "info"], repo).returncode != 0:
        raise RuntimeError("Docker가 실행 중이 아닙니다. 검증은 샌드박스에서만 돌립니다.")
    if _run(["docker", "image", "inspect", tag], repo).returncode == 0:
        return tag
    with tempfile.TemporaryDirectory() as context:
        for name in ("pyproject.toml", "uv.lock"):
            shutil.copy(repo / name, context)
        (Path(context) / "Dockerfile").write_text(_SANDBOX_DOCKERFILE, encoding="utf-8")
        result = _run(["docker", "build", "-q", "-t", tag, context], repo)
    if result.returncode != 0:
        raise RuntimeError(f"샌드박스 이미지를 만들지 못했습니다.\n{result.stderr[-_OUTPUT_TAIL:]}")
    return tag


def sandboxed_python(image: str, root: Path) -> list[str]:
    """worktree만 보이고 네트워크가 없는 컨테이너에서 Python을 실행하는 명령.

    모델이 쓴 테스트는 pytest가 그대로 실행한다. 홈 디렉터리의 토큰이나 `.env`를 읽거나 밖으로 보내지 못하게 막는다.
    """
    return [
        "docker", "run", "--rm",
        "--network", "none",
        "--memory", "2g", "--cpus", "2", "--pids-limit", "256",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
        "-v", f"{root.resolve()}:/workspace", "-w", "/workspace",
        image,
        # 컨테이너 안에서 시간을 재야 멈춘 테스트가 컨테이너째 끝난다.
        "timeout", str(_CHECK_TIMEOUT_SECONDS), "/venv/bin/python",
    ]


def run_checks(root: Path, python: list[str]) -> list[Check]:
    """ruff와 pytest. `python`은 Python을 실행하는 명령이다 (보통 `sandboxed_python`)."""
    # ponytail: 웹(apps/, packages/)을 건드리는 이슈는 worktree에 node_modules가 없어 typecheck를 못 돌린다. M2 전에 해결.
    checks = []
    for name, args in [
        ("ruff", ["-m", "ruff", "check", "."]),
        ("pytest", ["-m", "pytest", "-q", "-p", "no:cacheprovider"]),
    ]:
        result = _run([*python, *args], root)
        checks.append(Check(name, result.returncode == 0, (result.stdout + result.stderr)[-_OUTPUT_TAIL:]))
    return checks
