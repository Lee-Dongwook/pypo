from __future__ import annotations

import asyncio
import json
import re

import httpx
import pytest

from src.app.projection.graphdb_client import GraphDBClient, ProjectionTooLarge

GRAPH = "urn:pypo:acme:test:v1:data"


def _binding(s: str, p: str, o: str, *, uri: bool = True, lang: str | None = None, datatype: str | None = None) -> dict:
    if uri:
        obj = {"type": "uri", "value": o}
    else:
        obj = {"type": "literal", "value": o}
        if lang:
            obj["xml:lang"] = lang
        if datatype:
            obj["datatype"] = datatype

    return {
        "s": {"type": "uri", "value": s},
        "p": {"type": "uri", "value": p},
        "o": obj,
    }


def _sparql_response(bindings: list[dict]) -> httpx.Response:
    return httpx.Response(
        200,
        content=json.dumps({"head": {"vars": ["s", "p", "o"]}, "results": {"bindings": bindings}}),
        headers={"Content-Type": "application/sparql-results+json"},
    )


def _paging_transport(triples: list[dict], requests: list[tuple[int, int]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        query = request.content.decode()
        limit = int(re.search(r"LIMIT (\d+)", query).group(1))
        offset = int(re.search(r"OFFSET (\d+)", query).group(1))
        requests.append((limit, offset))
        return _sparql_response(triples[offset : offset + limit])

    return httpx.MockTransport(handler)


def test_fetch_triples_walks_all_pages() -> None:
    triples = [
        _binding("urn:s1", "urn:p", "urn:o1"),
        _binding("urn:s1", "urn:p", "urn:o2"),
        _binding("urn:s2", "urn:p", "urn:o3"),
    ]
    requests: list[tuple[int, int]] = []
    client = GraphDBClient("http://store", page_size=2, transport=_paging_transport(triples, requests))

    result = asyncio.run(client.fetch_triples(GRAPH))

    assert [triple.o for triple in result] == ["urn:o1", "urn:o2", "urn:o3"]
    assert requests == [(2, 0), (2, 2)]


def test_exact_multiple_of_page_size_issues_one_empty_page() -> None:
    triples = [_binding("urn:s1", "urn:p", "urn:o1"), _binding("urn:s2", "urn:p", "urn:o2")]
    requests: list[tuple[int, int]] = []
    client = GraphDBClient("http://store", page_size=2, transport=_paging_transport(triples, requests))

    result = asyncio.run(client.fetch_triples(GRAPH))

    assert len(result) == 2
    assert requests == [(2, 0), (2, 2)]


def test_empty_graph_returns_nothing() -> None:
    requests: list[tuple[int, int]] = []
    client = GraphDBClient("http://store", page_size=100, transport=_paging_transport([], requests))

    assert asyncio.run(client.fetch_triples(GRAPH)) == []
    assert requests == [(100, 0)]


def test_max_triples_fails_loudly_instead_of_truncating() -> None:
    triples = [
        _binding("urn:s1", "urn:p", "urn:o1"),
        _binding("urn:s1", "urn:p", "urn:o2"),
        _binding("urn:s2", "urn:p", "urn:o3"),
    ]
    client = GraphDBClient("http://store", page_size=2, transport=_paging_transport(triples, []))

    with pytest.raises(ProjectionTooLarge, match="more than 2 triples"):
        asyncio.run(client.fetch_triples(GRAPH, max_triples=2))


def test_literal_language_and_datatype_are_parsed() -> None:
    triples = [
        _binding("urn:s", "urn:label", "제품", uri=False, lang="ko"),
        _binding("urn:s", "urn:qty", "3", uri=False, datatype="http://www.w3.org/2001/XMLSchema#integer"),
        _binding("urn:s", "urn:link", "urn:o"),
    ]
    client = GraphDBClient("http://store", page_size=10, transport=_paging_transport(triples, []))

    result = asyncio.run(client.fetch_triples(GRAPH))

    assert result[0].o_type == "literal"
    assert result[0].o_lang == "ko"
    assert result[1].o_datatype == "http://www.w3.org/2001/XMLSchema#integer"
    assert result[2].o_type == "uri"


def test_graph_iri_is_validated_before_request() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return _sparql_response([])

    client = GraphDBClient("http://store", transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="valid absolute IRI"):
        asyncio.run(client.fetch_triples("urn:bad> } ?s ?p ?o"))

    assert calls == []


def test_page_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="page_size"):
        GraphDBClient("http://store", page_size=0)


def test_query_orders_triples_for_stable_pagination() -> None:
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(request.content.decode())
        return _sparql_response([])

    client = GraphDBClient("http://store", transport=httpx.MockTransport(handler))
    asyncio.run(client.fetch_triples(GRAPH))

    assert "ORDER BY ?s ?p ?o" in queries[0]
