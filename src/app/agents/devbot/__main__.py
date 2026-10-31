"""pypo 실행.

    uv run python -m src.app.agents.devbot day [--dry-run] [--issue N] [--base origin/main] [--keep]

통과하면 `pypo/*` 브랜치에 푸시하고 PR을 연다. 실패하거나 질문이 있으면 이슈에 코멘트와 라벨을 남긴다.
`--dry-run`이면 GitHub에는 아무것도 쓰지 않고 결과와 변경 내용만 출력한다.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from functools import partial
from pathlib import Path

from src.app.engine.models import resolve_chat_model
from src.app.shared.settings import settings

from . import github, workspace
from .graph import DevbotState, build_graph
from .guards import MAX_OPEN_PRS, branch_name

REPO = Path(__file__).resolve().parents[4]


def _model(reference: str):
    # Ollama 기본 문맥(4k)은 짧고, 16k는 16GB Mac에서 스왑을 일으킨다. 참고 파일을 발췌해 12k 안에 맞춘다. 넘치면 Ollama가 앞부분을 조용히 잘라 버린다.
    # num_predict: 맞는 답은 수백 토큰이다. 더 긴 답은 거의 파일 통째로 다시 쓰기라 시간만 든다 (#3에서 2048토큰에 6분).
    extra = {"num_ctx": 12288, "num_predict": 1024} if reference.startswith("ollama") else {}
    return resolve_chat_model(reference, **extra)


def _publish(state: DevbotState, root: Path | None) -> str | None:
    """결과를 GitHub에 남기고, PR을 열었으면 주소를 돌려준다 (docs/DEVBOT.md 4절 5단계)."""
    task, outcome = state.get("task"), state["outcome"]
    if task is None:
        return None
    if outcome == "passed" and root is not None:
        branch = branch_name(task.number, task.title)
        branch = workspace.push(root, branch, github.commit_message(task))
        body = github.pr_body(task, state.get("checks", []), state["attempts"], state.get("remembered", False))
        # `--base`는 작업을 시작할 커밋일 뿐이다. 실패하는 테스트를 먼저 넣은 브랜치에서 시작해도 PR은 main으로 간다.
        url = github.create_pr(task, branch, "main", body)
        print(f"[pypo] PR: {url}")
        return url
    elif outcome == "question":
        github.comment(task.number, f"작업 전에 확인이 필요합니다.\n\n{state['message']}\n\n"
                       f"답을 남기고 `{github.QUESTION}` 라벨을 지우면 다시 작업합니다.", github.QUESTION)
    elif outcome == "failed":
        github.comment(task.number, f"{state['attempts']}번 시도했지만 검증을 통과하지 못했습니다. "
                       f"이슈를 더 작게 나누거나 직접 처리해 주세요.\n\n## 마지막 에러\n\n"
                       f"```\n{state['message'][-2000:]}\n```", github.FAILED)
    return None


def _journal(state: DevbotState, pr_url: str | None) -> None:
    entry = github.journal_entry(date.today(), state.get("task"), state["outcome"], state.get("message", ""),
                                 state.get("calls", 0), pr_url, state.get("remembered", False))
    if (number := github.journal_issue()) is None:
        print(f"[pypo] '{github.JOURNAL_TITLE}' 이슈가 없어 일일 요약을 남기지 않습니다.\n{entry}")
        return
    github.comment(number, entry)
    print(f"[pypo] 일일 요약: #{number}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pypo")
    parser.add_argument("command", choices=["day"])
    parser.add_argument("--dry-run", action="store_true", help="GitHub에 쓰지 않고 결과만 출력")
    parser.add_argument("--issue", type=int, help="이 이슈만 처리 (기본: bot-ready 중 가장 오래된 것)")
    parser.add_argument("--base", default="origin/main", help="작업을 시작할 커밋")
    parser.add_argument("--model", default=settings.devbot_model)
    parser.add_argument("--keep", action="store_true", help="작업 공간(worktree)을 지우지 않고 남김")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[pypo] %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    print(f"[pypo] model={args.model} base={args.base}")
    try:
        image = workspace.sandbox_image(REPO)
    except RuntimeError as error:
        raise SystemExit(f"[pypo] {error}") from error
    if not args.dry_run and len(waiting := github.open_pr_branches()) >= MAX_OPEN_PRS:
        raise SystemExit(f"[pypo] 리뷰를 기다리는 PR이 {len(waiting)}개라 새 작업을 시작하지 않습니다.")
    graph = build_graph(_model(args.model), REPO, partial(workspace.sandboxed_python, image), base=args.base)
    state = graph.invoke({"issue": args.issue})

    task = state.get("task")
    print(f"[pypo] 이슈: {f'#{task.number} {task.title}' if task else '-'}")
    print(f"[pypo] 결과: {state['outcome']} ({state.get('message', '')[:500]})")
    for line in state.get("history", []):
        print(f"[pypo] {line[:800]}")
    for check in state.get("checks", []):
        print(f"[pypo] {check.name}: {'통과' if check.ok else '실패'}")
    print(f"[pypo] LLM 호출: {state.get('calls', 0)}회")

    root = Path(worktree) if (worktree := state.get("worktree")) else None
    if root is not None and state["outcome"] == "passed":
        print(f"[pypo] 변경 내용:\n{workspace.diff(root)}")
    try:
        if not args.dry_run:
            _journal(state, _publish(state, root))
    finally:
        if root is not None and args.keep:
            print(f"[pypo] 작업 공간: {root}")
        elif root is not None:
            workspace.remove(REPO, root)


if __name__ == "__main__":
    main()
