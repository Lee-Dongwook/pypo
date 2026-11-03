import pytest

from src.app.agents.tools.registry import ToolRegistry


def _echo(text: str, count: int = 1) -> str:
    return text * count


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("echo", "문자열을 count만큼 반복해 반환합니다.")(_echo)
    return registry


def test_register_builds_json_schema_from_type_hints() -> None:
    spec = _make_registry().get("echo")

    assert spec is not None
    assert spec.parameters["properties"]["text"] == {"type": "string"}
    assert spec.parameters["properties"]["count"] == {"type": "integer"}
    assert spec.parameters["required"] == ["text"]


def test_register_rejects_duplicate_name() -> None:
    registry = _make_registry()

    with pytest.raises(ValueError, match="이미 등록된 도구"):
        registry.register("echo", "중복 등록")(_echo)


def test_register_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="비어 있습니다"):
        ToolRegistry().register("  ", "설명")(_echo)


def test_schemas_expose_name_description_and_parameters() -> None:
    [schema] = _make_registry().schemas

    assert schema["name"] == "echo"
    assert schema["description"] == "문자열을 count만큼 반복해 반환합니다."
    assert schema["parameters"]["type"] == "object"


def test_execute_returns_result_for_valid_kwargs() -> None:
    assert _make_registry().execute("echo", {"text": "ab", "count": 2}) == "abab"


def test_execute_unknown_tool_returns_korean_error() -> None:
    result = _make_registry().execute("nope", {})

    assert "알 수 없는 도구" in result
    assert "nope" in result


def test_execute_missing_required_argument_returns_korean_error() -> None:
    assert "인자가 올바르지 않습니다" in _make_registry().execute("echo", {})


def test_execute_unexpected_argument_returns_korean_error() -> None:
    assert "인자가 올바르지 않습니다" in _make_registry().execute("echo", {"text": "a", "bogus": 1})


def test_execute_non_dict_kwargs_returns_korean_error() -> None:
    assert "action_input은 객체여야 합니다" in _make_registry().execute("echo", "text")


def test_execute_tool_exception_is_mapped_to_korean_error() -> None:
    registry = ToolRegistry()

    def boom() -> str:
        raise RuntimeError("터짐")

    registry.register("boom", "항상 실패합니다.")(boom)

    result = registry.execute("boom", {})

    assert "RuntimeError" in result
    assert "터짐" in result
