"""pypo의 작업 흐름 (docs/DEVBOT.md 4절, 2~5단계).

작업 고르기 → 계획 → 구현 → 검증. LLM은 계획과 구현에만 쓰고, 나머지는 코드가 판정한다.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from string import Template
from typing import Any, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from . import github, workspace
from .guards import MAX_ATTEMPTS, MAX_DIFF_LINES, path_violations
from .issue import Task, parse_task

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


def _prompt(repo: Path, name: str, **values: str) -> str:
    return Template((repo / "agent" / "prompts" / f"{name}.md").read_text(encoding="utf-8")).substitute(values)


def _ask(model: BaseChatModel, prompt: str) -> str:
    return str(model.invoke(prompt).content)


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
        text = _ask(model, _prompt(repo, "plan", **state["context"])).strip()
        if text.startswith("QUESTION:"):
            return {"outcome": "question", "message": text.removeprefix("QUESTION:").strip()}
        return {"plan": text}

    def implement(state: DevbotState) -> DevbotState:
        root = Path(state["worktree"])
        text = _ask(model, _prompt(repo, "implement", plan=state["plan"], feedback=state["feedback"],
                                   **state["context"]))
        edits = workspace.parse_file_blocks(text)
        problems = path_violations(edits, state["task"].files, root) if edits else ["출력 형식에 맞는 파일 블록이 없음"]
        if problems:
            return _retry(state, "출력이 규칙을 어겼습니다:\n- " + "\n- ".join(problems))
        workspace.apply(root, edits)
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
        return {"outcome": "passed", "checks": checks, "message": f"{state['attempts'] + 1}번째 시도에서 통과"}

    def _retry(state: DevbotState, feedback: str) -> DevbotState:
        attempts = state["attempts"] + 1
        if attempts >= MAX_ATTEMPTS:
            return {"attempts": attempts, "outcome": "failed", "message": feedback, "feedback": feedback}
        return {"attempts": attempts, "feedback": f"\n# 이전 시도 실패 ({attempts}/{MAX_ATTEMPTS})\n\n{feedback}\n"}

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
