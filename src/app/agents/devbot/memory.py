"""pypo의 기억 (docs/DEVBOT.md 8절). 실패했다가 고친 작업에서 배운 것을 저장소 안 마크다운에 쌓는다.

모델은 한 항목만 쓰고, 덧붙이기·중복 확인·상한은 여기서 코드가 맡는다. 기억 변경은 작업 PR에 함께 들어가 리뷰를 받는다.
"""

from __future__ import annotations

import re
from pathlib import Path

MISTAKES = "agent/memory/mistakes.md"
CONVENTIONS = "agent/memory/conventions.md"
MAX_ENTRIES = 50
MAX_PART_CHARS = 200
_HEADER = (
    "# 실수와 해결\n\n"
    "pypo가 실패했다가 고친 작업에서 배운 것입니다. 회고 단계에서 코드가 덧붙이고, PR 리뷰로 검수합니다.\n\n"
)
_LESSON = re.compile(r"^\W*상황\W*:\s*(.+)\n\W*원인\W*:\s*(.+)\n\W*해결\W*:\s*(.+)$", re.M)


def read(root: Path) -> str:
    """구현 단계 입력에 넣을 기억. 없으면 `(없음)`."""
    parts = [(root / path).read_text(encoding="utf-8").strip() for path in (CONVENTIONS, MISTAKES)
             if (root / path).exists()]
    return "\n\n".join(parts) or "(없음)"


def parse_lesson(text: str) -> tuple[str, str, str] | None:
    """모델 출력에서 `상황/원인/해결` 세 줄. 형식이 틀리거나 너무 길면 None."""
    match = _LESSON.search(text.replace("**", ""))
    if not match:
        return None
    situation, cause, fix = (part.strip() for part in match.groups())
    if all(0 < len(part) <= MAX_PART_CHARS for part in (situation, cause, fix)):
        return situation, cause, fix
    return None


def remember(root: Path, number: int, lesson: tuple[str, str, str]) -> bool:
    """`mistakes.md`에 한 줄로 덧붙인다. 같은 해결이 이미 있으면 덧붙이지 않고 False.

    상한을 넘으면 오래된 항목부터 지운다.
    """
    # ponytail: 해결 문장이 정확히 같을 때만 중복으로 본다. 비슷한 항목이 쌓이면 요약 단계를 붙인다.
    situation, cause, fix = lesson
    file = root / MISTAKES
    entries = [line for line in file.read_text(encoding="utf-8").splitlines() if line.startswith("- ")] \
        if file.exists() else []
    if any(line.endswith(f"해결: {fix}") for line in entries):
        return False
    entries = [*entries, f"- #{number} 상황: {situation} / 원인: {cause} / 해결: {fix}"][-MAX_ENTRIES:]
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(_HEADER + "\n".join(entries) + "\n", encoding="utf-8")
    return True
