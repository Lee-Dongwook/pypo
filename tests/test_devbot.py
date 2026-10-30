import shutil
import subprocess
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.app.agents.devbot import workspace
from src.app.agents.devbot.graph import build_graph
from src.app.agents.devbot.guards import MAX_ATTEMPTS, path_violations, removed_tests
from src.app.agents.devbot.issue import parse_task

REPO = Path(__file__).resolve().parents[1]

BODY = """### 목표

add가 두 수를 더한다

### 수정할 파일

calc.py

### 완료 기준

tests/test_calc.py 통과

### 통과해야 할 테스트 (선택)

_No response_

### 하지 않을 것

테스트는 고치지 않는다
"""

FIXED = """=== FILE: calc.py ===
<<<<<<< SEARCH
    return a - b
=======
    return a + b
>>>>>>> REPLACE
=== END ==="""


def test_issue_form_body_becomes_a_task() -> None:
    task = parse_task(7, "제목", BODY.replace("calc.py\n", "- `calc.py`\n./tests/test_calc.py\n"))

    assert task.goal == "add가 두 수를 더한다"
    assert task.files == ("calc.py", "tests/test_calc.py")
    assert task.tests == ""
    assert task.missing() == []


def test_task_without_required_fields_is_not_taken() -> None:
    task = parse_task(7, "제목", "### 목표\n\n뭔가 한다\n")

    assert task.missing() == ["완료 기준", "하지 않을 것", "수정할 파일은 1~3개"]


def test_guards_allow_targets_and_new_tests_only(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_old.py").write_text("")

    problems = path_violations(
        ["calc.py", "tests/test_new.py", "tests/test_old.py", ".github/ci.yml", "../x.py", "other.py"],
        ["calc.py"],
        tmp_path,
    )

    assert problems == [
        "tests/test_old.py: 이슈에 지정되지 않은 파일",
        ".github/ci.yml: 수정 금지 경로",
        "../x.py: 저장소 밖 경로",
        "other.py: 이슈에 지정되지 않은 파일",
    ]


def test_forbidden_paths_win_even_when_the_issue_lists_them(tmp_path: Path) -> None:
    assert path_violations(["migrations/env.py"], ["migrations/env.py"], tmp_path) == [
        "migrations/env.py: 수정 금지 경로"
    ]


def test_search_replace_blocks_are_parsed_and_text_outside_is_ignored() -> None:
    text = f"설명\n```\n{FIXED}\n```\n=== FILE: b.py ===\n<<<<<<< SEARCH\n=======\nx = 1\n>>>>>>> REPLACE\n=== END ===\n"

    assert workspace.parse_edits(text) == [
        workspace.Edit("calc.py", "    return a - b\n", "    return a + b\n"),
        workspace.Edit("b.py", "", "x = 1\n"),
    ]


def test_edits_replace_once_append_and_create(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    edits = [
        workspace.Edit("a.py", "y = 2\n", "y = 3\n"),
        workspace.Edit("a.py", "", "z = 4\n"),
        workspace.Edit("new.py", "", "n = 0\n"),
    ]

    assert workspace.apply_edits(tmp_path, edits) == {"a.py": "x = 1\ny = 3\nz = 4\n", "new.py": "n = 0\n"}


def test_trailing_spaces_in_search_are_tolerated(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")

    assert workspace.apply_edits(tmp_path, [workspace.Edit("a.py", "x = 1  \n", "x = 9\n")]) == {"a.py": "x = 9\ny = 2\n"}


@pytest.mark.parametrize(
    ("content", "search", "message"),
    [("x = 1\n", "y = 2\n", "일치하지 않음"), ("x = 1\nx = 1\n", "x = 1\n", "2곳과 일치")],
)
def test_search_must_match_exactly_one_place(tmp_path: Path, content: str, search: str, message: str) -> None:
    (tmp_path / "a.py").write_text(content)

    with pytest.raises(workspace.EditError, match=message):
        workspace.apply_edits(tmp_path, [workspace.Edit("a.py", search, "z\n")])


def make_repo(path: Path) -> Path:
    """버그 있는 calc.py와 그 테스트, pypo 규칙·프롬프트를 가진 작은 저장소."""
    (path / "tests").mkdir(parents=True)
    (path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (path / "tests" / "test_calc.py").write_text("from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n")
    (path / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath = ["."]\n')
    shutil.copy(REPO / "AGENTS.md", path / "AGENTS.md")
    shutil.copytree(REPO / "agent" / "prompts", path / "agent" / "prompts")
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
        subprocess.run(["git", *args], cwd=path, check=True)
    return path


def run(repo: Path, responses: list[str]) -> dict:
    graph = build_graph(
        FakeListChatModel(responses=responses),
        repo,
        base="HEAD",
        issues=lambda number: [{"number": 1, "title": "add 고치기", "body": BODY}],
    )
    state = graph.invoke({"issue": None})
    if worktree := state.get("worktree"):
        state["diff"] = workspace.diff(Path(worktree))
        workspace.remove(repo, Path(worktree))
    return state


def test_bad_output_is_retried_and_tests_decide(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), ["형식 없는 답", FIXED])

    assert state["outcome"] == "passed"
    assert state["attempts"] == 1
    assert "+    return a + b" in state["diff"]


def test_ambiguous_issue_ends_with_a_question(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), ["QUESTION: 음수도 다뤄야 하나요?"])

    assert state["outcome"] == "question"
    assert state["message"] == "음수도 다뤄야 하나요?"


def test_deleting_existing_tests_is_rejected_even_if_pytest_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    wipe = """=== FILE: tests/test_calc.py ===
<<<<<<< SEARCH
def test_add():
    assert add(1, 2) == 3
=======
def test_new():
    assert True
>>>>>>> REPLACE
=== END ==="""
    body = BODY.replace("calc.py\n\n### 완료", "calc.py\ntests/test_calc.py\n\n### 완료")
    graph = build_graph(
        FakeListChatModel(responses=[wipe, FIXED]),
        repo,
        base="HEAD",
        issues=lambda number: [{"number": 1, "title": "t", "body": body}],
    )

    state = graph.invoke({"issue": None})
    workspace.remove(repo, Path(state["worktree"]))

    # 첫 시도는 형식·경로가 맞고 pytest도 통과하지만, test_add를 지워서 거부된다.
    assert state["outcome"] == "passed"
    assert state["attempts"] == 1


def test_removed_tests_lists_only_deleted_test_functions() -> None:
    before = "def test_a():\n    pass\n\nasync def test_b():\n    pass\n\ndef helper():\n    pass\n"

    assert removed_tests(before, "def test_b():\n    pass\n") == ["test_a"]
    assert removed_tests(before, before + "def test_c():\n    pass\n") == []


def test_touching_forbidden_paths_fails_after_max_attempts(tmp_path: Path) -> None:
    bad = "=== FILE: .github/ci.yml ===\n<<<<<<< SEARCH\n=======\nx\n>>>>>>> REPLACE\n=== END ==="

    state = run(make_repo(tmp_path / "repo"), [bad] * MAX_ATTEMPTS)

    assert state["outcome"] == "failed"
    assert state["attempts"] == MAX_ATTEMPTS
    assert "수정 금지 경로" in state["message"]


def test_fenced_question_is_still_a_question(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), ["```plaintext\nQUESTION: 음수도 다뤄야 하나요?\n```"])

    assert state["outcome"] == "question"


def test_tests_named_in_the_issue_must_exist(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    body = BODY.replace("### 통과해야 할 테스트 (선택)\n\n_No response_", "### 통과해야 할 테스트 (선택)\n\ntest_add_zero")
    added = FIXED.replace(
        "=== END ===",
        "=== END ===\n=== FILE: tests/test_zero.py ===\n<<<<<<< SEARCH\n=======\nfrom calc import add\n\n\ndef test_add_zero():\n"
        "    assert add(0, 0) == 0\n>>>>>>> REPLACE\n=== END ===",
    )
    graph = build_graph(
        FakeListChatModel(responses=[FIXED, added]),
        repo,
        base="HEAD",
        issues=lambda number: [{"number": 1, "title": "t", "body": body}],
    )

    state = graph.invoke({"issue": None})
    workspace.remove(repo, Path(state["worktree"]))

    assert state["outcome"] == "passed"
    assert state["attempts"] == 1
    assert "test_add_zero" in state["history"][0]


def test_question_is_ignored_when_edits_are_present(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), [f"QUESTION: 이렇게 하면 되나요?\n{FIXED}"])

    assert state["outcome"] == "passed"


def test_reference_snippets_keep_only_what_the_issue_needs(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(
        "class Result:\n    x: int\n\n\ndef wanted():\n    return Result()\n\n\ndef unrelated():\n    return 1\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_m.py").write_text("from src.m import wanted, unrelated\n")

    text = workspace.reference_snippets(tmp_path, ("tests/test_m.py",), "`wanted` 테스트 추가")

    assert "def wanted" in text and "class Result" in text
    assert "unrelated" not in text


def test_long_question_with_a_plan_is_a_format_error_not_a_question(tmp_path: Path) -> None:
    rambling = "QUESTION: 이슈를 이해했습니다.\n" + "\n".join(f"{i}. 테스트를 추가합니다" for i in range(6))

    state = run(make_repo(tmp_path / "repo"), [rambling, FIXED])

    assert state["outcome"] == "passed"
    assert state["attempts"] == 1
