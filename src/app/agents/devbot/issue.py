"""GitHub Issue 본문을 pypo 작업으로 읽는다.

본문 형식은 `.github/ISSUE_TEMPLATE/bot-task.yml` 양식이 만드는 `### 제목` 구조를 따른다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .guards import normalize

MAX_FILES = 3
_EMPTY = "_No response_"


def _section(body: str, title: str) -> str:
    match = re.search(rf"^### {re.escape(title)}[^\n]*\n(.*?)(?=^### |\Z)", body, re.S | re.M)
    text = match.group(1).strip() if match else ""
    return "" if text == _EMPTY else text


@dataclass(frozen=True)
class Task:
    number: int
    title: str
    body: str
    goal: str
    files: tuple[str, ...]
    done: str
    tests: str
    out_of_scope: str

    def missing(self) -> list[str]:
        """비어 있거나 잘못된 필수 항목. 비어 있으면 pypo가 가져갈 수 있다."""
        problems = [name for name, value in [("목표", self.goal), ("완료 기준", self.done)] if not value]
        if not self.out_of_scope:
            problems.append("하지 않을 것")
        # 테스트 이름이 없으면 검증이 ruff·pytest뿐이라, 아무것도 안 한 답도 통과한다 (#3).
        if not re.search(r"\btest_\w+", self.tests):
            problems.append("통과해야 할 테스트")
        if not 1 <= len(self.files) <= MAX_FILES:
            problems.append(f"수정할 파일은 1~{MAX_FILES}개")
        return problems


def parse_task(number: int, title: str, body: str) -> Task:
    files = tuple(
        normalize(line.lstrip("-* ")) for line in _section(body, "수정할 파일").splitlines() if line.strip()
    )
    return Task(
        number=number,
        title=title,
        body=body,
        goal=_section(body, "목표"),
        files=files,
        done=_section(body, "완료 기준"),
        tests=_section(body, "통과해야 할 테스트"),
        out_of_scope=_section(body, "하지 않을 것"),
    )
