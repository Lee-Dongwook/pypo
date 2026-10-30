"""pypo 실행.

    uv run python -m src.app.agents.devbot day --dry-run [--issue N] [--base origin/main] [--keep]

M1은 미리 보기만 한다. GitHub에는 아무것도 쓰지 않고, 결과와 변경 내용을 출력한다.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.app.engine.models import resolve_chat_model
from src.app.shared.settings import settings

from . import workspace
from .graph import build_graph

REPO = Path(__file__).resolve().parents[4]


def _model(reference: str):
    # Ollama는 기본 문맥이 짧아 파일 몇 개만 넣어도 잘린다.
    extra = {"num_ctx": 16384} if reference.startswith("ollama") else {}
    return resolve_chat_model(reference, **extra)


def main() -> None:
    parser = argparse.ArgumentParser(prog="pypo")
    parser.add_argument("command", choices=["day"])
    parser.add_argument("--dry-run", action="store_true", required=True, help="M1은 미리 보기만 지원합니다")
    parser.add_argument("--issue", type=int, help="이 이슈만 처리 (기본: bot-ready 중 가장 오래된 것)")
    parser.add_argument("--base", default="origin/main", help="작업을 시작할 커밋")
    parser.add_argument("--model", default=settings.devbot_model)
    parser.add_argument("--keep", action="store_true", help="작업 공간(worktree)을 지우지 않고 남김")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[pypo] %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    print(f"[pypo] model={args.model} base={args.base}")
    graph = build_graph(_model(args.model), REPO, base=args.base)
    state = graph.invoke({"issue": args.issue})

    task = state.get("task")
    print(f"[pypo] 이슈: {f'#{task.number} {task.title}' if task else '-'}")
    print(f"[pypo] 결과: {state['outcome']} ({state.get('message', '')[:500]})")
    if state.get("plan"):
        print(f"[pypo] 계획:\n{state['plan']}")
    for line in state.get("history", []):
        print(f"[pypo] {line[:800]}")
    for check in state.get("checks", []):
        print(f"[pypo] {check.name}: {'통과' if check.ok else '실패'}")

    if worktree := state.get("worktree"):
        root = Path(worktree)
        if state["outcome"] == "passed":
            print(f"[pypo] 변경 내용:\n{workspace.diff(root)}")
        if args.keep:
            print(f"[pypo] 작업 공간: {root}")
        else:
            workspace.remove(REPO, root)


if __name__ == "__main__":
    main()
