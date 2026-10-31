"""GitHub 접근. 실행 환경의 `gh` 인증을 그대로 쓴다 (docs/DEVBOT.md 9절)."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from datetime import date
from typing import Any

from .guards import BRANCH_PREFIX
from .issue import Task
from .workspace import Check

READY = "bot-ready"
QUESTION = "bot-question"
FAILED = "bot-failed"
PAUSED = {QUESTION, FAILED}
BOT = "pypo"
JOURNAL_TITLE = "pypo 일지"
SIGNATURE = "\n\n— pypo"


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def _gh_json(*args: str) -> Any:
    return json.loads(_gh(*args))


def open_pr_branches() -> list[str]:
    """리뷰를 기다리는 pypo PR의 브랜치."""
    prs = _gh_json("pr", "list", "--label", BOT, "--state", "open", "--json", "headRefName")
    return [pr["headRefName"] for pr in prs]


def candidate_issues(number: int | None = None) -> list[dict[str, Any]]:
    """번호를 주면 그 이슈만, 아니면 `bot-ready` 이슈를 오래된 순으로. 이미 PR이 열린 이슈는 뺀다."""
    if number is not None:
        return [_gh_json("issue", "view", str(number), "--json", "number,title,body")]

    issues = _gh_json("issue", "list", "--label", READY, "--state", "open", "--limit", "50",
                      "--json", "number,title,body,labels,createdAt")
    taken = {int(m.group(1)) for b in open_pr_branches() if (m := re.match(rf"{BRANCH_PREFIX}(\d+)-", b))}
    ready = [
        issue for issue in issues
        if not PAUSED & {label["name"] for label in issue["labels"]} and issue["number"] not in taken
    ]
    return sorted(ready, key=lambda issue: issue["createdAt"])


def commit_message(task: Task) -> str:
    """`AGENTS.md` 형식 (`test(card): ...`). 종류와 범위는 첫 번째 수정 파일에서 정한다."""
    kind = "test" if all(path.startswith("tests/") for path in task.files) else "feat"
    parts = task.files[0].split("/")
    if parts[:2] == ["src", "app"] and len(parts) > 3:
        scope = parts[2]
    elif parts[0] == "tests":
        scope = parts[-1].removeprefix("test_").removesuffix(".py").split("_")[0]
    else:
        scope = parts[1] if parts[0] in ("apps", "packages") and len(parts) > 2 else parts[0]
    return f"{kind}({scope}): resolve #{task.number}"


def pr_body(task: Task, checks: Sequence[Check], attempts: int, remembered: bool = False) -> str:
    """`agent/persona.md`의 PR 본문 형식."""
    pytest = next((check.output for check in checks if check.name == "pytest"), "")
    passed = match.group(1) if (match := re.search(r"(\d+) passed", pytest)) else "?"
    web = any(path.startswith(("apps/", "packages/")) for path in task.files)
    return (
        f"## 한 일\n\n{task.goal}\n\n"
        "## 확인\n\n"
        f"- ruff: 통과\n- pytest: {passed}개 통과\n- typecheck: {'실행 안 함' if web else '해당 없음'}\n"
        f"- 시도: {attempts + 1}번째에 통과\n\n"
        "## 판단한 것\n\n판단 기록은 아직 남기지 않습니다.\n\n"
        + ("## 기억\n\n이번 실패와 해결을 `agent/memory/mistakes.md`에 추가했습니다. 다음 작업 입력에 들어가니 "
           "내용이 맞는지 같이 봐 주세요.\n\n" if remembered else "")
        + f"Closes #{task.number}{SIGNATURE}"
    )


def create_pr(task: Task, branch: str, base: str, body: str) -> str:
    """PR을 만들고 주소를 돌려준다."""
    title = task.title.removeprefix("[pypo]").strip()
    return _gh("pr", "create", "--head", branch, "--base", base, "--title", title, "--body", body,
               "--label", BOT).strip()


def comment(number: int, body: str, label: str | None = None) -> None:
    """이슈에 코멘트를 남기고, 주면 라벨을 붙인다. 라벨이 붙은 이슈는 다음 후보에서 빠진다."""
    _gh("issue", "comment", str(number), "--body", body + SIGNATURE)
    if label:
        _gh("issue", "edit", str(number), "--add-label", label)


def journal_issue() -> int | None:
    """사람이 만들어 둔 "pypo 일지" 이슈 번호. pypo는 이슈를 만들지 않는다 (docs/DEVBOT.md 13절)."""
    issues = _gh_json("issue", "list", "--state", "open", "--search", f"{JOURNAL_TITLE} in:title",
                      "--json", "number,title")
    return next((issue["number"] for issue in issues if issue["title"] == JOURNAL_TITLE), None)


def journal_entry(today: date, task: Task | None, outcome: str, message: str, calls: int,
                  pr_url: str | None = None, remembered: bool = False) -> str:
    """일일 요약 (docs/DEVBOT.md 10절): 한 일, 실패한 일, 남긴 질문, 사용한 호출 수."""
    result = {
        "passed": f"PR {pr_url or '(미리 보기)'} ({message})",
        "failed": "실패. 이슈에 마지막 에러를 남김",
        "question": "질문을 남김",
        "no_task": message,
    }[outcome]
    lines = [f"## {today.isoformat()}", ""]
    if task:
        lines.append(f"- 이슈: #{task.number} {task.title.removeprefix('[pypo]').strip()}")
    lines += [f"- 결과: {result}", f"- LLM 호출: {calls}회"]
    if remembered:
        lines.append("- 기억: 이번 실패와 해결을 `agent/memory/mistakes.md`에 추가 (PR에 포함)")
    return "\n".join(lines)
