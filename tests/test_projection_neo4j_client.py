from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from src.app.projection.mapper import Entity, Rel
from src.app.projection.neo4j_client import Neo4jProjectionClient


def _entity(iri: str, tenant: str = "acme", version: str = "v1") -> Entity:
    return Entity(
        iri=iri,
        tenant=tenant,
        ontology_version=version,
        labels=["urn:Thing"],
        properties={"label": iri},
        inferred=False,
        source_graph="urn:graph",
    )


def _rel(source: str, target: str) -> Rel:
    return Rel(
        from_iri=source,
        to_iri=target,
        predicate="urn:relatedTo",
        tenant="acme",
        ontology_version="v1",
        inferred=True,
        rule_id="rule-7",
        source_graph="urn:graph",
    )


class FakeResult:
    def __init__(self, record: dict[str, Any] | None = None, nodes_deleted: int = 0) -> None:
        self.record = record
        self.nodes_deleted = nodes_deleted

    def single(self) -> dict[str, Any] | None:
        return self.record

    def consume(self) -> SimpleNamespace:
        return SimpleNamespace(counters=SimpleNamespace(nodes_deleted=self.nodes_deleted))


class FakeTx:
    def __init__(self, log: list[tuple[str, dict[str, Any]]], deleted: list[int]) -> None:
        self.log = log
        self.deleted = deleted

    def run(self, query: str, **params: Any) -> FakeResult:
        self.log.append((query, params))
        if "DETACH DELETE" in query:
            return FakeResult(nodes_deleted=self.deleted.pop(0) if self.deleted else 0)
        return FakeResult(record={"c": len(params.get("rows", []))})


class FakeSession:
    def __init__(self, tx: FakeTx) -> None:
        self.tx = tx

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        return False

    def execute_write(self, fn: Any) -> Any:
        return fn(self.tx)


class FakeDriver:
    def __init__(self, deleted: list[int] | None = None) -> None:
        self.log: list[tuple[str, dict[str, Any]]] = []
        self.tx = FakeTx(self.log, deleted or [])

    def session(self) -> FakeSession:
        return FakeSession(self.tx)


def test_entity_key_includes_tenant_and_version() -> None:
    driver = FakeDriver()
    client = Neo4jProjectionClient(driver)

    assert client.upsert_entities([_entity("urn:a")]) == 1

    query, params = driver.log[0]
    assert "MERGE (e:Entity {" in query
    assert "tenant: row.tenant" in query
    assert "ontology_version: row.ontology_version" in query
    assert "iri: row.iri" in query
    assert params["rows"][0]["tenant"] == "acme"
    assert params["rows"][0]["ontology_version"] == "v1"


def test_entities_are_written_in_batches() -> None:
    driver = FakeDriver()
    client = Neo4jProjectionClient(driver, batch_size=2)
    entities = [_entity(f"urn:e{index}") for index in range(3)]

    assert client.upsert_entities(entities) == 3

    assert [len(params["rows"]) for _, params in driver.log] == [2, 1]


def test_relation_merge_matches_scoped_endpoints() -> None:
    driver = FakeDriver()
    client = Neo4jProjectionClient(driver)

    assert client.upsert_rels([_rel("urn:a", "urn:b")]) == 1

    query, params = driver.log[0]
    assert query.count("MATCH (") == 2
    assert "iri: row.from_iri" in query
    assert "iri: row.to_iri" in query
    assert "MERGE (a)-[r:REL {predicate: row.predicate}]->(b)" in query
    row = params["rows"][0]
    assert row["inferred"] is True
    assert row["rule_id"] == "rule-7"
    assert row["tenant"] == "acme"
    assert row["ontology_version"] == "v1"


def test_clear_version_deletes_every_batch() -> None:
    driver = FakeDriver(deleted=[2, 1])
    client = Neo4jProjectionClient(driver, batch_size=2)

    assert client.clear_version("acme", "v1") == 3

    assert len(driver.log) == 2
    for query, params in driver.log:
        assert "DETACH DELETE e" in query
        assert "WITH e LIMIT $batch" in query
        assert params["tenant"] == "acme"
        assert params["ontology_version"] == "v1"
        assert params["batch"] == 2


def test_clear_source_graph_is_scoped_to_the_graph() -> None:
    driver = FakeDriver(deleted=[1])
    client = Neo4jProjectionClient(driver)

    assert client.clear_source_graph("acme", "v1", "urn:graph") == 1

    _, params = driver.log[0]
    assert params["source_graph"] == "urn:graph"


def test_empty_input_does_not_touch_the_database() -> None:
    driver = FakeDriver()
    client = Neo4jProjectionClient(driver)

    assert client.upsert_entities([]) == 0
    assert client.upsert_rels([]) == 0
    assert driver.log == []
