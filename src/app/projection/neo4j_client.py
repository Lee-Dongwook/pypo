from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, Session

from src.app.shared.neo4j import get_session

from .mapper import Entity, Rel

# The node key is (tenant, ontology_version, iri). Keeping the version in the key
# means re-projecting v2 must not touch v1 nodes; keeping the tenant there means a
# shared external IRI can never be overwritten by another tenant.
_ENTITY_UPSERT = """
UNWIND $rows AS row
MERGE (e:Entity {
    tenant: row.tenant,
    ontology_version: row.ontology_version,
    iri: row.iri
})
SET e.labels = row.labels,
    e.inferred = row.inferred,
    e.source_graph = row.source_graph
SET e += row.properties
RETURN count(e) AS c
"""

_REL_UPSERT = """
UNWIND $rows AS row
MATCH (a:Entity {
    tenant: row.tenant,
    ontology_version: row.ontology_version,
    iri: row.from_iri
})
MATCH (b:Entity {
    tenant: row.tenant,
    ontology_version: row.ontology_version,
    iri: row.to_iri
})
MERGE (a)-[r:REL {predicate: row.predicate}]->(b)
SET r.tenant = row.tenant,
    r.ontology_version = row.ontology_version,
    r.inferred = row.inferred,
    r.rule_id = row.rule_id,
    r.source_graph = row.source_graph
RETURN count(r) AS c
"""

_CLEAR_MATCH = "MATCH (e:Entity {{ {match} }}) WITH e LIMIT $batch DETACH DELETE e"


class Neo4jProjectionClient:
    def __init__(self, driver: Driver | None = None, *, batch_size: int = 10_000) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self._driver = driver
        self.batch_size = batch_size

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if self._driver is not None:
            with self._driver.session() as session:
                yield session
            return
        with get_session() as session:
            yield session

    def _write(self, query: str, params: dict[str, Any]) -> tuple[Any, Any]:
        def run(tx: Any) -> Any:
            result = tx.run(query, **params)
            record = result.single()
            summary = result.consume()
            return record, summary

        with self._session() as session:
            return session.execute_write(run)

    def _write_rows(self, query: str, rows: list[dict[str, Any]]) -> int:
        merged = 0
        for start in range(0, len(rows), self.batch_size):
            chunk = rows[start : start + self.batch_size]
            record, _ = self._write(query, {"rows": chunk})
            merged += record["c"] if record else 0
        return merged

    def upsert_entities(self, entities: list[Entity]) -> int:
        if not entities:
            return 0

        rows = [
            {
                "iri": entity.iri,
                "tenant": entity.tenant,
                "ontology_version": entity.ontology_version,
                "labels": entity.labels,
                "properties": entity.properties,
                "inferred": entity.inferred,
                "source_graph": entity.source_graph,
            }
            for entity in entities
        ]
        return self._write_rows(_ENTITY_UPSERT, rows)

    def upsert_rels(self, rels: list[Rel]) -> int:
        if not rels:
            return 0

        rows = [
            {
                "from_iri": rel.from_iri,
                "to_iri": rel.to_iri,
                "predicate": rel.predicate,
                "tenant": rel.tenant,
                "ontology_version": rel.ontology_version,
                "inferred": rel.inferred,
                "rule_id": rel.rule_id,
                "source_graph": rel.source_graph,
            }
            for rel in rels
        ]
        return self._write_rows(_REL_UPSERT, rows)

    def clear_version(self, tenant: str, ontology_version: str) -> int:
        return self._delete(
            "tenant: $tenant, ontology_version: $ontology_version",
            {"tenant": tenant, "ontology_version": ontology_version},
        )

    def clear_source_graph(self, tenant: str, ontology_version: str, source_graph: str) -> int:
        return self._delete(
            "tenant: $tenant, ontology_version: $ontology_version, source_graph: $source_graph",
            {
                "tenant": tenant,
                "ontology_version": ontology_version,
                "source_graph": source_graph,
            },
        )

    def _delete(self, match: str, params: dict[str, Any]) -> int:
        query = _CLEAR_MATCH.format(match=match)
        deleted = 0

        while True:
            _, summary = self._write(query, {**params, "batch": self.batch_size})
            count = summary.counters.nodes_deleted
            deleted += count
            if count < self.batch_size:
                return deleted
