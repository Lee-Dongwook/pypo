from __future__ import annotations

import asyncio
from typing import Any

from src.app.projection.graphdb_client import Triple
from src.app.projection.service import ProjectionService

T = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
REL = "https://data.pypo.dev/test/ontology/hasSupplier"

GRAPH_A = "urn:pypo:acme:v1:data"
GRAPH_B = "urn:pypo:acme:v1:inferred"


def _triple(s: str, p: str, o: str, o_type: str = "uri") -> Triple:
    return Triple(s=s, p=p, o=o, o_type=o_type)


TRIPLES_A = [
    _triple("urn:product:1", T, "urn:Product"),
    _triple("urn:product:1", REL, "urn:supplier:1"),
]
TRIPLES_B = [_triple("urn:product:1", "urn:inferredFrom", "urn:order:9")]


class FakeGraphDB:
    def __init__(self, events: list[tuple[Any, ...]], triples: dict[str, list[Triple]]) -> None:
        self.events = events
        self.triples = triples

    async def fetch_triples(self, graph_iri: str, *, max_triples: int | None = None) -> list[Triple]:
        self.events.append(("fetch", graph_iri, max_triples))
        return self.triples[graph_iri]


class FakeNeo4j:
    def __init__(self, events: list[tuple[Any, ...]], *, rels_merged: int | None = None) -> None:
        self.events = events
        self.rels_merged = rels_merged
        self.entities: list[Any] = []
        self.rels: list[Any] = []

    def clear_version(self, tenant: str, version: str) -> int:
        self.events.append(("clear_version", tenant, version))
        return 5

    def clear_source_graph(self, tenant: str, version: str, graph: str) -> int:
        self.events.append(("clear_source_graph", tenant, version, graph))
        return 2

    def upsert_entities(self, entities: list[Any]) -> int:
        self.events.append(("entities", len(entities)))
        self.entities = entities
        return len(entities)

    def upsert_rels(self, rels: list[Any]) -> int:
        self.events.append(("rels", len(rels)))
        self.rels = rels
        return len(rels) if self.rels_merged is None else self.rels_merged


def _service(events: list[tuple[Any, ...]], triples: dict[str, list[Triple]], **kwargs: Any) -> ProjectionService:
    return ProjectionService(graphdb=FakeGraphDB(events, triples), neo4j=FakeNeo4j(events, **kwargs))


def test_single_graph_fetches_before_clearing() -> None:
    events: list[tuple[Any, ...]] = []
    service = _service(events, {GRAPH_A: TRIPLES_A})

    result = asyncio.run(service.rebuild_from_graph(GRAPH_A, "acme", "v1"))

    assert events == [
        ("fetch", GRAPH_A, service.max_triples),
        ("clear_source_graph", "acme", "v1", GRAPH_A),
        ("entities", 2),
        ("rels", 1),
    ]
    assert result == {
        "graph": GRAPH_A,
        "deleted_entities": 2,
        "triples_fetched": 2,
        "entities_upserted": 2,
        "rels_upserted": 1,
        "rels_dropped": 0,
        "blank_nodes_skipped": 0,
    }


def test_replace_false_keeps_existing_projection() -> None:
    events: list[tuple[Any, ...]] = []
    service = _service(events, {GRAPH_A: TRIPLES_A})

    result = asyncio.run(service.rebuild_from_graph(GRAPH_A, "acme", "v1", replace=False))

    assert ("clear_source_graph", "acme", "v1", GRAPH_A) not in events
    assert result["deleted_entities"] == 0


def test_unmatched_relation_endpoints_are_reported() -> None:
    events: list[tuple[Any, ...]] = []
    service = _service(events, {GRAPH_A: TRIPLES_A}, rels_merged=0)

    result = asyncio.run(service.rebuild_from_graph(GRAPH_A, "acme", "v1"))

    assert result["rels_upserted"] == 0
    assert result["rels_dropped"] == 1


def test_multiple_graphs_are_fetched_first_and_cleared_once() -> None:
    events: list[tuple[Any, ...]] = []
    service = _service(events, {GRAPH_A: TRIPLES_A, GRAPH_B: TRIPLES_B})

    result = asyncio.run(service.rebuild_from_graphs([GRAPH_A, GRAPH_B], "acme", "v1", inferred=True))

    assert events[:3] == [
        ("fetch", GRAPH_A, service.max_triples),
        ("fetch", GRAPH_B, service.max_triples),
        ("clear_version", "acme", "v1"),
    ]
    assert result["deleted_entities"] == 5
    assert [entry["graph"] for entry in result["graphs"]] == [GRAPH_A, GRAPH_B]
    assert result["graphs"][0] == {
        "graph": GRAPH_A,
        "triples_fetched": 2,
        "entities_mapped": 2,
        "rels_mapped": 1,
        "blank_nodes_skipped": 0,
        "rels_dropped": 0,
    }
    assert result["totals"] == {
        "triples_fetched": 3,
        "entities_upserted": 3,
        "rels_upserted": 2,
        "rels_dropped": 0,
        "blank_nodes_skipped": 0,
    }


def test_inferred_graph_cannot_overwrite_asserted_entity() -> None:
    events: list[tuple[Any, ...]] = []
    asserted = [
        _triple("urn:product:1", T, "urn:Product"),
        _triple("urn:product:1", "http://www.w3.org/2000/01/rdf-schema#label", "제품", "literal"),
    ]
    inferred = [_triple("urn:product:1", REL, "urn:supplier:1")]
    neo4j = FakeNeo4j(events)
    service = ProjectionService(
        graphdb=FakeGraphDB(events, {GRAPH_A: asserted, GRAPH_B: inferred}),
        neo4j=neo4j,
    )

    asyncio.run(
        service.rebuild_from_graphs(
            [GRAPH_A, GRAPH_B],
            "acme",
            "v1",
            inferred_graphs={GRAPH_B},
            rule_id="rule-7",
        )
    )

    by_iri = {entity.iri: entity for entity in neo4j.entities}
    product = by_iri["urn:product:1"]
    assert product.properties["label"] == "제품"
    assert product.inferred is False
    assert product.labels == ["urn:Product"]

    supplier = by_iri["urn:supplier:1"]
    assert supplier.inferred is True
    assert supplier.source_graph == GRAPH_B

    assert neo4j.rels[0].inferred is True
    assert neo4j.rels[0].rule_id == "rule-7"


def test_multiple_graphs_can_skip_replacement() -> None:
    events: list[tuple[Any, ...]] = []
    service = _service(events, {GRAPH_A: TRIPLES_A})

    asyncio.run(service.rebuild_from_graphs([GRAPH_A], "acme", "v1", replace=False))

    assert all(event[0] != "clear_version" for event in events)


def test_max_triples_is_passed_to_the_store() -> None:
    events: list[tuple[Any, ...]] = []
    service = _service(events, {GRAPH_A: TRIPLES_A})
    service.max_triples = 10

    asyncio.run(service.rebuild_from_graph(GRAPH_A, "acme", "v1", max_triples=7))

    assert events[0] == ("fetch", GRAPH_A, 7)
