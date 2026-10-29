import pytest

from src.app.agents.supervisor.tools.index import Bm25Index, tokenize

NAMES = [
    "ontology search",
    "graph path",
    "document ingest",
    "graph analytics",
]


def test_tokenize_lowercases_words() -> None:
    assert tokenize("Graph Path") == ["graph", "path"]


def test_search_ranks_matching_documents() -> None:
    index = Bm25Index.from_names(NAMES)

    assert index.search("graph", k=2) == ["graph path", "graph analytics"]
    assert index.search("ingest", k=1) == ["document ingest"]


def test_search_respects_k() -> None:
    index = Bm25Index.from_names(NAMES)

    assert len(index.search("graph", k=1)) == 1


def test_search_returns_empty_for_unknown_terms() -> None:
    index = Bm25Index.from_names(NAMES)

    assert index.search("zzz", k=5) == []


def test_empty_index_is_safe() -> None:
    index = Bm25Index.from_names([])

    assert index.avg_length == 0.0
    assert index.search("graph", k=5) == []


def test_non_positive_k_returns_empty() -> None:
    index = Bm25Index.from_names(NAMES)

    assert index.search("graph", k=0) == []


@pytest.mark.xfail(
    strict=True,
    reason="한글은 글자 단위로 쪼개져서 '공급사'가 3토큰이 된다. 형태소 분석기나 bigram이 필요하다.",
)
def test_hangul_term_stays_whole() -> None:
    assert tokenize("공급사") == ["공급사"]
