from src.app.engine.search.node.utils import format_search_results


def test_formats_every_result() -> None:
    output = format_search_results([{"title": "A"}, {"title": "B"}, {"title": "C"}])

    assert "Found 3 related results" in output
    assert output.index("1. A") < output.index("2. B") < output.index("3. C")


def test_empty_results() -> None:
    assert format_search_results([]) == "Result not found."


def test_missing_score_does_not_crash() -> None:
    output = format_search_results([{"title": "A", "score": None}])

    assert "Score: 0.00" in output


def test_missing_url_has_no_placeholder() -> None:
    output = format_search_results([{"title": "A"}])

    assert "http:example" not in output


def test_tags_and_kst_timestamp() -> None:
    output = format_search_results(
        [{"title": "A", "tags": ["policy", "supplier"], "created_at": 0}]
    )

    assert "Tags: policy, supplier" in output
    assert "Created: 1970-01-01 09:00:00" in output


def test_default_tags_marker() -> None:
    assert "Tags: -" in format_search_results([{"title": "A"}])
