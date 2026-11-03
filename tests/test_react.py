from src.app.agents.react import build_prompt, parse_action


def test_parse_action_parses_plain_json() -> None:
    action = parse_action('{"thought": "생각", "action": "tool_search", "action_input": {"query": "검색"}}')

    assert action is not None
    assert action.thought == "생각"
    assert action.action == "tool_search"
    assert action.action_input == {"query": "검색"}


def test_parse_action_parses_fenced_json() -> None:
    raw = '```json\n{"thought": "t", "action": "finish", "action_input": {"answer": "done"}}\n```'

    action = parse_action(raw)

    assert action is not None
    assert action.action == "finish"
    assert action.action_input == {"answer": "done"}


def test_parse_action_parses_json_embedded_in_prose() -> None:
    raw = '잠시만요. {"thought": "t", "action": "finish", "action_input": {}} 입니다.'

    action = parse_action(raw)

    assert action is not None
    assert action.action == "finish"


def test_parse_action_skips_invalid_json_object_and_uses_next_one() -> None:
    raw = '{"action": 42} 그리고 {"thought": "t", "action": "finish", "action_input": {}}'

    action = parse_action(raw)

    assert action is not None
    assert action.action == "finish"


def test_parse_action_rejects_non_dict_action_input() -> None:
    assert parse_action('{"action": "finish", "action_input": "done"}') is None


def test_parse_action_returns_none_for_empty_string() -> None:
    assert parse_action("") is None


def test_parse_action_returns_none_when_action_missing() -> None:
    assert parse_action('{"thought": "t", "action_input": {}}') is None


def test_build_prompt_includes_tools_history_and_task() -> None:
    prompt = build_prompt("작업", ["Step 1 - Observation: 관찰"], [{"name": "echo", "description": "d", "parameters": {}}])

    assert "작업" in prompt
    assert "Step 1 - Observation: 관찰" in prompt
    assert '"echo"' in prompt
    assert "finish" in prompt
