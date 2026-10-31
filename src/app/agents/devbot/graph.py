"""pypo의 작업 흐름 (docs/DEVBOT.md 4절).

작업 고르기 → 구현 → 검증 → (실패했다가 통과했으면) 회고. LLM은 구현과 회고에만 쓰고, 나머지는 코드가 판정한다.
계획 단계는 7B 모델에서 판단이 틀리고 느려서 뺐다 (구현 단계가 QUESTION도 맡는다).
"""

from __future__ import annotations

import logging
import operator
import re
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from string import Template
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from . import github, memory, workspace
from .guards import MAX_ATTEMPTS, diff_line_violations, path_violations, removed_tests
from .issue import Task, parse_task

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```[\w-]*\n|\n?```\s*$", re.M)

Outcome = Literal["passed", "question", "failed", "no_task"]
IssueSource = Callable[[int | None], list[dict[str, Any]]]
PythonCommand = Callable[[Path], list[str]]


class DevbotState(TypedDict, total=False):
    issue: int | None
    task: Task
    worktree: str
    context: dict[str, str]
    attempts: int
    feedback: str
    checks: list[workspace.Check]
    outcome: Outcome
    message: str
    history: Annotated[list[str], operator.add]
    calls: Annotated[int, operator.add]
    remembered: bool


def _prompt(repo: Path, name: str, **values: str) -> str:
    """공통 문맥(context.md) 뒤에 단계별 지시를 붙인다.

    모든 호출의 앞부분이 글자 하나 다르지 않아야 Ollama가 이미 읽은 부분을 캐시로 재사용한다.
    """
    prompts = repo / "agent" / "prompts"
    parts = [(prompts / "context.md").read_text(encoding="utf-8"), (prompts / f"{name}.md").read_text(encoding="utf-8")]
    return "\n".join(Template(part).substitute(values) for part in parts)


LOG_DIR = Path(tempfile.gettempdir()) / "pypo-logs"


def _ask(model: BaseChatModel, prompt: str, step: str) -> str:
    """모델 호출. 디버깅을 위해 프롬프트와 응답 원문을 LOG_DIR에 남긴다."""
    started = time.monotonic()
    reply = model.invoke(prompt)
    LOG_DIR.mkdir(exist_ok=True)
    (LOG_DIR / f"{step}.prompt.md").write_text(prompt, encoding="utf-8")
    (LOG_DIR / f"{step}.reply.md").write_text(str(reply.content), encoding="utf-8")
    meta = reply.response_metadata or {}
    logger.info(
        "llm %s: 입력 %s토큰(읽는 데 %.0fs) 출력 %s토큰, 총 %.0fs → %s",
        step,
        meta.get("prompt_eval_count", "?"),
        meta.get("prompt_eval_duration", 0) / 1e9,
        meta.get("eval_count", "?"),
        time.monotonic() - started,
        LOG_DIR / f"{step}.reply.md",
    )
    return str(reply.content)


def build_graph(
    model: BaseChatModel,
    repo: Path,
    python: PythonCommand,
    base: str = "origin/main",
    issues: IssueSource = github.candidate_issues,
) -> CompiledStateGraph:
    """`repo`는 pypo 자신의 규칙과 프롬프트를 읽는 곳, `base`는 작업을 시작할 커밋이다.

    `python`은 worktree에서 검증(ruff, pytest)을 돌릴 Python 명령을 만든다. 실제 실행에서는 샌드박스다.
    """

    def pick(state: DevbotState) -> DevbotState:
        skipped = []
        for raw in issues(state.get("issue")):
            task = parse_task(raw["number"], raw["title"], raw["body"])
            if missing := task.missing():
                skipped.append(f"#{task.number}({', '.join(missing)})")
                continue
            root = workspace.create(repo, base)
            if problems := path_violations(task.files, task.files, root):
                workspace.remove(repo, root)
                skipped.append(f"#{task.number}({'; '.join(problems)})")
                continue
            context = {
                "agents": (repo / "AGENTS.md").read_text(encoding="utf-8"),
                "number": str(task.number),
                "title": task.title,
                "body": task.body,
                "references": workspace.reference_snippets(root, task.files, task.body) or "(없음)",
                "files": "\n\n".join(f"--- {p} ---\n{workspace.read(root, p)}" for p in task.files),
                "memory": memory.read(root),
            }
            return {"task": task, "worktree": str(root), "context": context, "attempts": 0, "feedback": ""}
        reason = f" 건너뜀: {', '.join(skipped)}" if skipped else ""
        return {"outcome": "no_task", "message": f"가져갈 수 있는 이슈가 없습니다.{reason}"}

    def implement(state: DevbotState) -> DevbotState:
        return {**_implement(state), "calls": 1}

    def _implement(state: DevbotState) -> DevbotState:
        root = Path(state["worktree"])
        prompt = _prompt(repo, "implement", feedback=state["feedback"], **state["context"])
        text = _ask(model, prompt, f"issue{state['task'].number}-try{state['attempts'] + 1}")
        edits = workspace.parse_edits(text)
        # 짧은 질문만 질문으로 받는다. 작은 모델은 계획이나 코드 앞에도 QUESTION을 붙이곤 하는데, 그건 형식 오류다.
        question = _FENCE.sub("", text).strip()
        if not edits and question.startswith("QUESTION:") and len(question.splitlines()) <= 4 and len(question) <= 400:
            return {"outcome": "question", "message": question.removeprefix("QUESTION:").strip()}

        edit_paths = {e.path for e in edits}
        problems = path_violations(edit_paths, state["task"].files, root) if edits else [
            "출력 형식에 맞는 SEARCH/REPLACE 블록이 없음. 설명 없이 첫 줄부터 `=== FILE: <경로> ===`로 시작할 것"
        ]

        contents: dict[str, str] = {}
        if not problems:
            workspace.reset(root)
            try:
                contents = workspace.apply_edits(root, edits)
            except workspace.EditError as error:
                problems.append(str(error))

        for path, content in contents.items():
            target_file = root / path
            if target_file.exists():
                before_text = target_file.read_text(encoding="utf-8")
                if gone := removed_tests(before_text, content):
                    problems.append(f"{path}: 기존 테스트를 지움 ({', '.join(gone)}). 바꿀 부분만 SEARCH/REPLACE로 쓸 것")

        if problems:
            return _retry(state, "출력이 규칙을 어겼습니다:\n- " + "\n- ".join(problems))

        workspace.apply(root, contents)
        return {"feedback": ""}

    def verify(state: DevbotState) -> DevbotState:
        root = Path(state["worktree"])
        checks = workspace.run_checks(root, python(root))
        failed = [check for check in checks if not check.ok]
        if failed:
            details = "\n\n".join(f"## {check.name}\n{check.output}" for check in failed)
            return {**_retry(state, f"검증에 실패했습니다.\n\n{details}"), "checks": checks}

        if too_big := diff_line_violations(workspace.diff(root)):
            return {**_retry(state, "\n".join(too_big)), "checks": checks}
        if missing := workspace.missing_tests(root, re.findall(r"test_\w+", state["task"].tests)):
            return {**_retry(state, f"이슈가 요구한 테스트가 없습니다: {', '.join(missing)}. 이 이름으로 테스트를 만드세요."),
                    "checks": checks}

        return {"outcome": "passed", "checks": checks, "message": f"{state['attempts'] + 1}번째 시도에서 통과"}

    def retrospect(state: DevbotState) -> DevbotState:
        """실패했다가 통과한 작업에서 배운 것을 기억에 남긴다. 형식이 틀리면 다시 묻지 않고 건너뛴다."""
        root, task = Path(state["worktree"]), state["task"]
        failure = state["history"][-1].split(": ", 1)[-1][-1500:]
        prompt = _prompt(repo, "retrospect", failure=failure, diff=workspace.diff(root)[-3000:], **state["context"])
        lesson = memory.parse_lesson(_ask(model, prompt, f"issue{task.number}-retrospect"))
        if lesson is None:
            return {"calls": 1, "history": ["회고: 형식이 맞지 않아 기억에 남기지 않음"]}
        if not memory.remember(root, task.number, lesson):
            return {"calls": 1, "history": ["회고: 이미 있는 내용이라 덧붙이지 않음"]}
        return {"calls": 1, "remembered": True, "history": [f"회고: {memory.MISTAKES}에 추가 ({lesson[2]})"]}

    def _retry(state: DevbotState, feedback: str) -> DevbotState:
        attempts = state["attempts"] + 1
        log = [f"{attempts}번째 시도 실패: {feedback}"]
        if attempts >= MAX_ATTEMPTS:
            return {"attempts": attempts, "outcome": "failed", "message": feedback, "feedback": feedback, "history": log}
        return {
            "attempts": attempts,
            "feedback": f"\n# 이전 시도 실패 ({attempts}/{MAX_ATTEMPTS})\n\n{feedback}\n",
            "history": log,
        }

    def after_implement(state: DevbotState) -> str:
        if state.get("outcome"):
            return END
        return "implement" if state["feedback"] else "verify"

    def after_verify(state: DevbotState) -> str:
        if state.get("outcome") == "passed" and state["attempts"] > 0:
            return "retrospect"
        return END if state.get("outcome") else "implement"

    graph = StateGraph(DevbotState)
    graph.add_node("pick", pick)
    graph.add_node("implement", implement)
    graph.add_node("verify", verify)
    graph.add_node("retrospect", retrospect)
    graph.add_edge(START, "pick")
    graph.add_conditional_edges("pick", lambda s: END if s.get("outcome") else "implement")
    graph.add_conditional_edges("implement", after_implement)
    graph.add_conditional_edges("verify", after_verify)
    graph.add_edge("retrospect", END)
    return graph.compile()
