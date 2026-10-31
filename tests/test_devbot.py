import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_ollama import ChatOllama

from src.app.agents.devbot import github, memory, workspace
from src.app.agents.devbot import graph as devbot_graph
from src.app.agents.devbot.graph import LOG_DIR, RETRY_TEMPERATURE, build_graph, model_for_attempt
from src.app.agents.devbot.guards import MAX_ATTEMPTS, MAX_DIFF_LINES, branch_name, path_violations, removed_tests
from src.app.agents.devbot.issue import parse_task

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def trajectories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """테스트가 홈의 실제 학습 데이터에 쓰지 않게 한다."""
    path = tmp_path / "trajectories.jsonl"
    monkeypatch.setattr(devbot_graph, "TRAJECTORIES", path)
    return path

BODY = """### 목표

add가 두 수를 더한다

### 수정할 파일

calc.py

### 완료 기준

tests/test_calc.py 통과

### 통과해야 할 테스트 (선택)

test_add

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
    assert task.tests == "test_add"
    assert task.missing() == []


def test_task_without_required_fields_is_not_taken() -> None:
    task = parse_task(7, "제목", "### 목표\n\n뭔가 한다\n")

    assert task.missing() == ["완료 기준", "하지 않을 것", "통과해야 할 테스트", "수정할 파일은 1~3개"]


def test_task_without_a_named_test_is_not_taken_because_doing_nothing_would_pass() -> None:
    task = parse_task(7, "제목", BODY.replace("test_add\n", "_No response_\n"))

    assert task.missing() == ["통과해야 할 테스트"]


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

    assert workspace.apply_edits(tmp_path, edits) == {"a.py": "x = 1\ny = 3\n\n\nz = 4\n", "new.py": "n = 0\n"}


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


def local_python(root: Path) -> list[str]:
    """테스트에서는 Docker 없이 지금 Python으로 검증한다. 샌드박스 자체는 따로 확인한다."""
    return [sys.executable]


def run(repo: Path, responses: list[str]) -> dict:
    graph = build_graph(
        FakeListChatModel(responses=responses),
        repo,
        local_python,
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
        local_python,
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
    body = BODY.replace("test_add\n", "test_add_zero\n")
    added = FIXED.replace(
        "=== END ===",
        "=== END ===\n=== FILE: tests/test_zero.py ===\n<<<<<<< SEARCH\n=======\nfrom calc import add\n\n\ndef test_add_zero():\n"
        "    assert add(0, 0) == 0\n>>>>>>> REPLACE\n=== END ===",
    )
    graph = build_graph(
        FakeListChatModel(responses=[FIXED, added]),
        repo,
        local_python,
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


def test_large_target_files_are_excerpted_for_the_llm(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    source = "\n\n\n".join(f"def helper_{i}(value):\n    return value + {i}\n" for i in range(300))

    (tmp_path / "src" / "big.py").write_text(source)

    text = workspace.file_content(tmp_path, "src/big.py", "helper_7 추가")

    assert "def helper_7" in text
    assert "def helper_42" not in text


def test_small_target_files_are_sent_in_full(tmp_path: Path) -> None:
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")

    assert workspace.file_content(tmp_path, "calc.py", "add") == "def add(a, b):\n    return a + b\n"


def test_unmatched_hint_keeps_the_whole_file(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    source = "\n\n\n".join(f"def helper_{i}(value):\n    return value + {i}\n" for i in range(300))

    (tmp_path / "src" / "big.py").write_text(source)

    assert workspace.file_content(tmp_path, "src/big.py", "전혀 모르는 함수") == source


def test_long_question_with_a_plan_is_a_format_error_not_a_question(tmp_path: Path) -> None:
    rambling = "QUESTION: 이슈를 이해했습니다.\n" + "\n".join(f"{i}. 테스트를 추가합니다" for i in range(6))

    state = run(make_repo(tmp_path / "repo"), [rambling, FIXED])

    assert state["outcome"] == "passed"
    assert state["attempts"] == 1


def test_unmarked_block_is_appended_and_its_imports_are_hoisted(tmp_path: Path) -> None:
    (tmp_path / "t.py").write_text("import os\n\n\ndef test_a():\n    pass\n")
    reply = "=== FILE: t.py ===\n```python\nimport sys\n\n\ndef test_b():\n    assert sys\n```\n=== END ==="

    edits = workspace.parse_edits(reply)

    assert workspace.apply_edits(tmp_path, edits) == {
        "t.py": "import os\nimport sys\n\n\ndef test_a():\n    pass\n\n\ndef test_b():\n    assert sys\n"
    }


def test_unmarked_block_creates_a_new_file(tmp_path: Path) -> None:
    edits = workspace.parse_edits("=== FILE: tests/test_x.py ===\nimport os\n\n\ndef test_x():\n    assert os\n=== END ===")

    assert workspace.apply_edits(tmp_path, edits) == {"tests/test_x.py": "import os\n\n\ndef test_x():\n    assert os\n"}


def test_safe_lint_fixes_are_applied_before_verification(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    unused = FIXED.replace("    return a + b\n>>>>>>> REPLACE", "    return a + b\n>>>>>>> REPLACE\n<<<<<<< SEARCH\n=======\nimport os\n>>>>>>> REPLACE")

    state = run(repo, [unused])

    assert state["outcome"] == "passed"
    assert "import os" not in state["diff"]


def test_trailing_whitespace_written_by_the_model_is_removed() -> None:
    reply = "=== FILE: a.py ===\ndef f():\n    x = 1\n    \n    return x  \n=== END ===\n"

    [edit] = workspace.parse_edits(reply)

    assert edit.replace == "def f():\n    x = 1\n\n    return x\n"


def test_change_over_the_line_limit_is_retried(tmp_path: Path) -> None:
    filler = "".join(f"x{i} = {i}\n" for i in range(MAX_DIFF_LINES + 1))
    huge = FIXED.replace("    return a + b\n", "    return a + b\n\n\n" + filler)

    state = run(make_repo(tmp_path / "repo"), [huge, FIXED])

    assert state["outcome"] == "passed"
    assert "상한" in state["history"][0]


def test_broken_syntax_is_left_to_pytest_not_reported_as_deleted_tests() -> None:
    assert removed_tests("def test_a():\n    pass\n", "def test_a(:\n") == []


# 샌드박스 안에는 docker 명령이 없으므로 실행 전에 찾는다.
HAS_DOCKER = shutil.which("docker") is not None and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@pytest.mark.skipif(not HAS_DOCKER, reason="Docker 없음")
def test_sandbox_has_no_network_and_sees_only_the_worktree(tmp_path: Path) -> None:
    python = workspace.sandboxed_python(workspace.sandbox_image(REPO), tmp_path)
    probe = (
        "import os, socket\n"
        "assert not os.path.exists(os.path.expanduser('~/.ssh'))\n"
        f"assert not os.path.exists({str(REPO / 'pyproject.toml')!r})\n"
        "socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
    )

    result = subprocess.run([*python, "-c", probe], capture_output=True, text=True)

    assert result.returncode != 0
    assert "OSError" in result.stderr or "unreachable" in result.stderr
    assert "AssertionError" not in result.stderr


def test_branch_name_is_pypo_number_and_ascii_slug() -> None:
    assert branch_name(1, "[pypo] analyze_card_tier 단위 테스트 추가") == "pypo/1-analyze-card-tier"
    assert branch_name(2, "한글만 있는 제목") == "pypo/2-task"


def test_commit_message_follows_agents_md_format() -> None:
    tests_only = parse_task(1, "t", BODY.replace("calc.py\n", "tests/test_card_calculator.py\n"))
    code = parse_task(2, "t", BODY.replace("calc.py\n", "src/app/card/calculator.py\n"))

    assert github.commit_message(tests_only) == "test(card): resolve #1"
    assert github.commit_message(code) == "feat(card): resolve #2"


def test_pr_body_closes_the_issue_and_reports_checks() -> None:
    checks = [workspace.Check("ruff", True, ""), workspace.Check("pytest", True, "12 passed, 1 skipped in 0.5s\n")]

    body = github.pr_body(parse_task(7, "t", BODY), checks, attempts=1)

    assert "- pytest: 12개 통과" in body
    assert "2번째에 통과" in body
    assert body.endswith("Closes #7\n\n— pypo")


def test_push_goes_only_to_pypo_branches_as_pypo(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")

    with pytest.raises(ValueError, match="pypo/"):
        workspace.push(repo, "main", "fix(calc): resolve #1")
    workspace.push(repo, "pypo/1-calc", "fix(calc): resolve #1")

    log = subprocess.run(["git", "log", "-1", "--format=%an %s", "pypo/1-calc"], cwd=remote, capture_output=True,
                         text=True, check=True).stdout
    assert log == "pypo-agent fix(calc): resolve #1\n"


def test_redoing_an_issue_pushes_a_new_branch_instead_of_overwriting(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)

    names = []
    for content in ("a + b", "b + a", "a + b + 0"):
        (repo / "calc.py").write_text(f"def add(a, b):\n    return {content}\n")
        names.append(workspace.push(repo, "pypo/1-calc", "fix(calc): resolve #1"))

    assert names == ["pypo/1-calc", "pypo/1-calc-2", "pypo/1-calc-3"]


LESSON = "상황: add 수정에서 형식 없이 답함\n원인: FILE 블록을 쓰지 않음\n해결: 첫 줄부터 FILE 블록으로 시작한다"


def test_failure_then_pass_is_remembered_in_the_pr(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), ["형식 없는 답", FIXED, LESSON])

    assert state["outcome"] == "passed"
    assert state["calls"] == 3
    assert state["remembered"] is True
    assert "+- #1 상황: add 수정에서 형식 없이 답함 / 원인: FILE 블록을 쓰지 않음 / 해결: 첫 줄부터" in state["diff"]


def test_first_try_pass_leaves_no_memory(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), [FIXED])

    assert state["calls"] == 1
    assert "mistakes.md" not in state["diff"]


def test_malformed_lesson_is_skipped_not_retried(tmp_path: Path) -> None:
    state = run(make_repo(tmp_path / "repo"), ["형식 없는 답", FIXED, "잘 모르겠습니다"])

    assert state["outcome"] == "passed"
    assert state["calls"] == 3
    assert "mistakes.md" not in state["diff"]


def test_memory_skips_duplicate_fixes_and_keeps_the_newest(tmp_path: Path) -> None:
    lesson = memory.parse_lesson(LESSON)
    assert lesson is not None

    assert memory.remember(tmp_path, 1, lesson) is True
    assert memory.remember(tmp_path, 2, lesson) is False
    for i in range(memory.MAX_ENTRIES + 5):
        memory.remember(tmp_path, 3, (f"상황{i}", "원인", f"해결{i}"))

    entries = [line for line in (tmp_path / memory.MISTAKES).read_text().splitlines() if line.startswith("- ")]
    assert len(entries) == memory.MAX_ENTRIES
    assert entries[-1].endswith(f"해결: 해결{memory.MAX_ENTRIES + 4}")


def test_memory_in_the_base_commit_is_given_to_the_model(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "agent" / "memory").mkdir()
    (repo / memory.MISTAKES).write_text("- #9 상황: x / 원인: y / 해결: 기억해 둔 해결\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "memory"], cwd=repo, check=True)

    run(repo, [FIXED])

    assert "기억해 둔 해결" in (LOG_DIR / "issue1-try1.prompt.md").read_text()


def test_journal_entry_reports_result_and_calls() -> None:
    task = parse_task(1, "[pypo] add 고치기", BODY)

    entry = github.journal_entry(date(2026, 10, 31), task, "passed", "2번째 시도에서 통과", 3,
                                 "https://github.com/o/r/pull/7", remembered=True)

    assert entry.splitlines()[:5] == [
        "## 2026-10-31",
        "",
        "- 이슈: #1 add 고치기",
        "- 결과: PR https://github.com/o/r/pull/7 (2번째 시도에서 통과)",
        "- LLM 호출: 3회",
    ]
    assert "mistakes.md" in entry


def test_retries_sample_with_higher_temperature_but_first_try_stays_deterministic() -> None:
    model = ChatOllama(model="qwen2.5-coder:7b", temperature=0, num_ctx=12288)

    assert model_for_attempt(model, 0) is model
    retry = model_for_attempt(model, 1)
    assert retry.temperature == RETRY_TEMPERATURE
    assert retry.num_ctx == 12288
    assert model.temperature == 0


def test_retry_prompt_shows_the_previous_reply_so_only_the_problem_is_fixed(tmp_path: Path) -> None:
    run(make_repo(tmp_path / "repo"), ["형식 없는 답", FIXED])

    prompt = (LOG_DIR / "issue1-try2.prompt.md").read_text(encoding="utf-8")
    assert "# 이전 출력\n\n형식 없는 답" in prompt
    assert "위 문제만 고쳐" in prompt


def test_only_passing_work_is_saved_as_training_data(tmp_path: Path, trajectories: Path) -> None:
    run(make_repo(tmp_path / "pass"), ["형식 없는 답", FIXED])
    run(make_repo(tmp_path / "fail"), ["형식 없는 답"] * MAX_ATTEMPTS)

    rows = [json.loads(line) for line in trajectories.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["attempts"] == 2
    assert [m["role"] for m in rows[0]["messages"]] == ["user", "assistant"]
    assert "# 이전 출력\n\n형식 없는 답" in rows[0]["messages"][0]["content"]
    assert rows[0]["messages"][1]["content"] == FIXED


def test_training_data_drops_code_fences_and_flags_answers_ruff_had_to_fix(tmp_path: Path, trajectories: Path) -> None:
    fenced = FIXED.replace("<<<<<<< SEARCH", "```python\n<<<<<<< SEARCH").replace("REPLACE\n", "REPLACE\n```\n")
    unused_import = """=== FILE: calc.py ===
<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
import json


def add(a, b):
    return a + b
>>>>>>> REPLACE
=== END ==="""

    run(make_repo(tmp_path / "fenced"), [fenced])
    run(make_repo(tmp_path / "unused"), [unused_import])

    rows = [json.loads(line) for line in trajectories.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert "```" not in rows[0]["messages"][1]["content"]
    assert [row["ruff_fixed"] for row in rows] == [False, True]


def test_delete_line_removes_a_whole_definition_so_the_model_need_not_copy_it(tmp_path: Path) -> None:
    (tmp_path / "shapes.py").write_text(
        "import functools\n\n\n@functools.cache\nclass Box:\n    width: int\n\n\ndef area(w, h):\n    return w * h\n",
        encoding="utf-8",
    )
    edits = workspace.parse_edits("=== FILE: shapes.py ===\nDELETE Box\nfrom models import Box\n=== END ===")

    content = workspace.apply_edits(tmp_path, edits)["shapes.py"]

    assert "class Box" not in content
    assert "@functools.cache" not in content
    assert "from models import Box" in content
    assert "def area(w, h):" in content


def test_deleting_an_unknown_definition_is_reported_with_its_name(tmp_path: Path) -> None:
    (tmp_path / "shapes.py").write_text("def area(w, h):\n    return w * h\n", encoding="utf-8")
    edits = workspace.parse_edits("=== FILE: shapes.py ===\nDELETE Box\n=== END ===")

    with pytest.raises(workspace.EditError, match="Box"):
        workspace.apply_edits(tmp_path, edits)


def test_move_line_cuts_a_definition_into_another_file_and_leaves_an_import(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "shapes.py").write_text(
        "class Box:\n    width: int\n\n\ndef area(box: Box) -> int:\n    return box.width\n", encoding="utf-8"
    )
    (tmp_path / "lib" / "models.py").write_text("import dataclasses\n\n\nclass Circle:\n    r: int\n", encoding="utf-8")
    edits = workspace.parse_edits("=== FILE: lib/shapes.py ===\nMOVE Box TO lib/models.py\n=== END ===")

    contents = workspace.apply_edits(tmp_path, edits)

    assert "class Box" not in contents["lib/shapes.py"]
    assert contents["lib/shapes.py"].startswith("from .models import Box\n")
    assert contents["lib/models.py"].endswith("class Circle:\n    r: int\n\n\nclass Box:\n    width: int\n")


def test_rewriting_existing_definitions_is_rejected_with_a_move_hint(tmp_path: Path) -> None:
    (tmp_path / "shapes.py").write_text("class Box:\n    width: int\n", encoding="utf-8")
    edits = workspace.parse_edits("=== FILE: shapes.py ===\nclass Box:\n    width: int\n\n\nclass New:\n    pass\n=== END ===")

    problems = workspace.rewritten_definitions(tmp_path, edits)

    assert len(problems) == 1
    assert "Box" in problems[0] and "MOVE" in problems[0]
    assert "New" not in problems[0]


def test_delete_plus_retyped_copy_elsewhere_moves_the_original_instead(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "shapes.py").write_text("class Box:\n    width: int\n", encoding="utf-8")
    (tmp_path / "lib" / "models.py").write_text("class Circle:\n    r: int\n", encoding="utf-8")
    reply = (
        "=== FILE: lib/shapes.py ===\nDELETE Box\n=== END ===\n"
        "=== FILE: lib/models.py ===\nfrom .shapes import Circle\n\nclass Box:\n    width: int\n"
        "    invented: str = 'made up'\n=== END ==="
    )

    contents = workspace.apply_edits(tmp_path, workspace.parse_edits(reply))

    assert contents["lib/models.py"].endswith("class Box:\n    width: int\n")
    assert "invented" not in contents["lib/models.py"]
    assert "from .shapes" not in contents["lib/models.py"]
    assert contents["lib/shapes.py"].startswith("from .models import Box\n")


def test_move_also_fixes_imports_in_other_issue_files(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "shapes.py").write_text("class Box:\n    width: int\n\n\ndef area():\n    pass\n", encoding="utf-8")
    (tmp_path / "lib" / "models.py").write_text("class Circle:\n    r: int\n", encoding="utf-8")
    (tmp_path / "lib" / "draw.py").write_text("from .shapes import (\n    Box,\n    area,\n)\n\nx = Box\n", encoding="utf-8")
    edits = workspace.parse_edits("=== FILE: lib/shapes.py ===\nMOVE Box TO lib/models.py\n=== END ===")

    contents = workspace.apply_edits(tmp_path, edits, ("lib/shapes.py", "lib/models.py", "lib/draw.py"))

    assert contents["lib/draw.py"] == "from .shapes import area\nfrom .models import Box\n\nx = Box\n"


def test_rename_line_renames_a_definition_and_its_uses_in_issue_files_but_not_strings(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "shapes.py").write_text('def area():\n    return "area"\n\n\nx = area()  # area\n')
    (tmp_path / "lib" / "draw.py").write_text("from .shapes import area\n\ny = area()\n")
    reply = (
        "=== FILE: lib/shapes.py ===\nRENAME area TO surface\n"
        "<<<<<<< SEARCH\nx = area()  # area\n=======\nx = area() + 1  # area\n>>>>>>> REPLACE\n=== END ==="
    )

    contents = workspace.apply_edits(tmp_path, workspace.parse_edits(reply), ("lib/shapes.py", "lib/draw.py"))

    assert contents["lib/shapes.py"] == 'def surface():\n    return "area"\n\n\nx = surface() + 1  # area\n'
    assert contents["lib/draw.py"] == "from .shapes import surface\n\ny = surface()\n"


def test_renaming_onto_an_existing_name_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "shapes.py").write_text("def area():\n    pass\n\n\ndef size():\n    pass\n")
    edits = workspace.parse_edits("=== FILE: shapes.py ===\nRENAME area TO size\n=== END ===")

    with pytest.raises(workspace.EditError, match="size"):
        workspace.apply_edits(tmp_path, edits)


def test_missing_import_of_a_name_defined_once_in_src_is_added(tmp_path: Path) -> None:
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "schemas.py").write_text("class Card:\n    pass\n")
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True)

    workspace.apply(tmp_path, {"tests/test_card.py": "def test_card():\n    assert Card and Unknown\n"})

    assert (tmp_path / "tests" / "test_card.py").read_text().startswith("from src.app.schemas import Card\n")


def test_common_errors_become_one_line_instructions_that_say_where_the_name_lives(tmp_path: Path) -> None:
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "schemas.py").write_text("class Card:\n    pass\n")

    assert workspace.explain(tmp_path, "E   ImportError: cannot import name 'Card' from 'src.app.calc' (/w/calc.py)") == [
        "`src.app.calc`에는 `Card`가 없다. `Card`는 src/app/schemas.py에 있으니 거기서 import한다"
    ]
    assert "MOVE" in workspace.explain(tmp_path, "a.py:9:5: F811 [*] Redefinition of unused `Card` from line 2")[0]
    assert workspace.explain(tmp_path, "AssertionError: 1 != 2") == []


def test_files_importing_the_issue_files_are_shown_to_the_model(tmp_path: Path) -> None:
    (tmp_path / "src" / "card").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "card" / "calc.py").write_text("def evaluate():\n    pass\n")
    (tmp_path / "src" / "card" / "api.py").write_text("from .calc import evaluate\n")
    (tmp_path / "tests" / "test_calc.py").write_text("from src.card.calc import evaluate\n")

    assert workspace.importers(tmp_path, ("src/card/calc.py",)) == (
        "src/card/api.py:1: from .calc import evaluate\ntests/test_calc.py:1: from src.card.calc import evaluate"
    )
