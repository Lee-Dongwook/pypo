"""GitHub 접근. 실행 환경의 `gh` 인증을 그대로 쓴다 (docs/DEVBOT.md 9절)."""

from __future__ import annotations

import json
import subprocess
from typing import Any

READY = "bot-ready"
PAUSED = {"bot-question", "bot-failed"}


def _gh(*args: str) -> Any:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def candidate_issues(number: int | None = None) -> list[dict[str, Any]]:
    """번호를 주면 그 이슈만, 아니면 `bot-ready` 이슈를 오래된 순으로."""
    if number is not None:
        return [_gh("issue", "view", str(number), "--json", "number,title,body")]

    issues = _gh("issue", "list", "--label", READY, "--state", "open", "--limit", "50",
                 "--json", "number,title,body,labels,createdAt")
    ready = [issue for issue in issues if not PAUSED & {label["name"] for label in issue["labels"]}]
    return sorted(ready, key=lambda issue: issue["createdAt"])
