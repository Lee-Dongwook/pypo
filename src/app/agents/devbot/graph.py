"""pypo의 작업 흐름 (docs/DEVBOT.md 4절, 2~5단계).

작업 고르기 → 계획 → 구현 → 검증. LLM은 계획과 구현에만 쓰고, 나머지는 코드가 판정한다.
"""

from __future__ import annotations

import logging
import operator
import re
import time
from collections.abc import Callable
from pathlib import Path
from string import Template
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from . import github, workspace
from .guards import MAX_ATTEMPTS, MAX_DIFF_LINES, path_violations, removed_tests
from .issue import Task, parse_task

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```[\w-]*\n|\n?```\s*$", re.M)

Outcome = Literal["passed", "question", "failed", "no_task"]
IssueSource = Callable[[int | None], list[dict[str, Any]]]


class DevbotState(TypedDict, total=False):
    issue: int | None
    task: Task
    worktree: str
    context: dict[str, str]
    plan: str
    attempts: int
    feedback: str
    checks: list[workspace.Check]
    outcome: Outcome
    message: str
    history: Annotated[list[str], operator.add]


def _prompt(repo: Path, name: str, **values: str) -> str:
    """공통 문맥(context.md) 뒤에 단계별 지시를 붙인다.

    모든 호출의 앞부분이 글자 하나 다르지 않아야 Ollama가 이미 읽은 부분을 캐시로 재사용한다.
    """
    prompts = repo / "agent" / "prompts"
    parts = [(prompts / "context.md").read_text(encoding="utf-8"), (prompts / f"{name}.md").read_text(encoding="utf-8")]
    return "\n".join(Template(part).substitute(values) for part in parts)


def _ask(model: BaseChatModel, prompt: str, step: str) -> str:
    started = time.monotonic()
    reply = model.invoke(prompt)
    meta = reply.response_metadata or {}
    logger.info(
        "llm %s: 입력 %s토큰(읽는 데 %.0fs) 출력 %s토큰, 총 %.0fs",
        step,
        meta.get("prompt_eval_count", "?"),
        meta.get("prompt_eval_duration", 0) / 1e9,
        meta.get("eval_count", "?"),
        time.monotonic() - started,
    )
    return str(reply.content)


def build_graph(
    model: BaseChatModel,
    repo: Path,
    base: str = "origin/main",
    issues: IssueSource = github.candidate_issues,
) -> CompiledStateGraph:
    """`repo`는 pypo 자신의 규칙과 프롬프트를 읽는 곳, `base`는 작업을 시작할 커밋이다."""

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
            refs = workspace.references(root, task.files)
            context = {
                "agents": (repo / "AGENTS.md").read_text(encoding="utf-8"),
                "number": str(task.number),
                "title": task.title,
                "body": task.body,
                "references": "\n\n".join(f"--- {p} ---\n{workspace.read(root, p)}" for p in refs) or "(없음)",
                "files": "\n\n".join(f"--- {p} ---\n{workspace.read(root, p)}" for p in task.files),
            }
            return {"task": task, "worktree": str(root), "context": context, "attempts": 0, "feedback": ""}
        reason = f" 건너뜀: {', '.join(skipped)}" if skipped else ""
        return {"outcome": "no_task", "message": f"가져갈 수 있는 이슈가 없습니다.{reason}"}

    def plan(state: DevbotState) -> DevbotState:
        # 작은 모델은 답을 코드 블록으로 감싸곤 한다. 감싼 표시를 벗겨야 QUESTION을 알아본다.
        text = _FENCE.sub("", _ask(model, _prompt(repo, "plan", **state["context"]), "plan")).strip()
        if text.startswith("QUESTION:"):
            return {"outcome": "question", "message": text.removeprefix("QUESTION:").strip()}
        return {"plan": text}

    def implement(state: DevbotState) -> DevbotState:
        root = Path(state["worktree"])
        prompt = _prompt(repo, "implement", plan=state["plan"], feedback=state["feedback"], **state["context"])
        text = _ask(model, prompt, f"implement#{state['attempts'] + 1}")
        edits = workspace.parse_edits(text)
        problems = path_violations({e.path for e in edits}, state["task"].files, root) if edits else [
            "출력 형식에 맞는 SEARCH/REPLACE 블록이 없음"
        ]
        contents: dict[str, str] = {}
        if not problems:
            workspace.reset(root)
            try:
                contents = workspace.apply_edits(root, edits)
            except workspace.EditError as error:
                problems.append(str(error))
        for path, content in contents.items():
            if (root / path).exists() and (gone := removed_tests((root / path).read_text(encoding="utf-8"), content)):
                problems.append(f"{path}: 기존 테스트를 지움 ({', '.join(gone)}). 바꿀 부분만 SEARCH/REPLACE로 쓸 것")
        if problems:
            return _retry(state, "출력이 규칙을 어겼습니다:\n- " + "\n- ".join(problems))
        workspace.apply(root, contents)
        return {"feedback": ""}

    def verify(state: DevbotState) -> DevbotState:
        root = Path(state["worktree"])
        checks = workspace.run_checks(root)
        failed = [check for check in checks if not check.ok]
        if failed:
            details = "\n\n".join(f"## {check.name}\n{check.output}" for check in failed)
            return {**_retry(state, f"검증에 실패했습니다.\n\n{details}"), "checks": checks}
        if (lines := workspace.diff_lines(root)) > MAX_DIFF_LINES:
            return {**_retry(state, f"변경이 {lines}줄로 상한 {MAX_DIFF_LINES}줄을 넘습니다. 필요한 부분만 바꾸세요."),
                    "checks": checks}
        if missing := workspace.missing_tests(root, re.findall(r"test_\w+", state["task"].tests)):
            return {**_retry(state, f"이슈가 요구한 테스트가 없습니다: {', '.join(missing)}. 이 이름으로 테스트를 만드세요."),
                    "checks": checks}
        return {"outcome": "passed", "checks": checks, "message": f"{state['attempts'] + 1}번째 시도에서 통과"}

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
        return END if state.get("outcome") else "implement"

    graph = StateGraph(DevbotState)
    graph.add_node("pick", pick)
    graph.add_node("plan", plan)
    graph.add_node("implement", implement)
    graph.add_node("verify", verify)
    graph.add_edge(START, "pick")
    graph.add_conditional_edges("pick", lambda s: END if s.get("outcome") else "plan")
    graph.add_conditional_edges("plan", lambda s: END if s.get("outcome") else "implement")
    graph.add_conditional_edges("implement", after_implement)
    graph.add_conditional_edges("verify", after_verify)
    return graph.compile()
