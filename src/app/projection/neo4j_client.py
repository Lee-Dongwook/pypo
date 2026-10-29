from __future__ import annotations

from src.app.shared.neo4j import get_session

from .mapper import Entity, Rel


class Neo4jProjectionClient:
    def upsert_entities(self, entities: list[Entity]) -> int:
        if not entities:
            return 0

        query = """
        UNWIND $rows AS row
        MERGE (e:Entity {iri: row.iri})
        SET e.tenant = row.tenant,
            e.ontology_version = row.ontology_version,
            e.labels = row.labels,
            e.properties = row.properties,
            e.inferred = row.inferred,
            e.source_graph = row.source_graph
        RETURN count(e) AS c
        """

        rows = [
            {
                "iri": e.iri,
                "tenant": e.tenant,
                "ontology_version": e.ontology_version,
                "labels": e.labels,
                "properties": e.properties,
                "inferred": e.inferred,
                "source_graph": e.source_graph,
            }
            for e in entities
        ]

        with get_session() as session:
            result = session.run(query, rows=rows)
            record = result.single()
            return record["c"] if record else 0

    def upsert_rels(self, rels: list[Rel]) -> int:
        if not rels:
            return 0

        query = """
        UNWIND $rows AS row
        MATCH (a:Entity {iri: row.from_iri})
        MATCH (b:Entity {iri: row.to_iri})
        MERGE (a)-[r:REL {predicate: row.predicate}]->(b)
        SET r.inferred = row.inferred,
            r.rule_id = row.rule_id,
            r.source_graph = row.source_graph
        RETURN count(r) AS c
        """

        rows = [
            {
                "from_iri": r.from_iri,
                "to_iri": r.to_iri,
                "predicate": r.predicate,
                "inferred": r.inferred,
                "rule_id": r.rule_id,
                "source_graph": r.source_graph,
            }
            for r in rels
        ]

        with get_session() as session:
            result = session.run(query, rows=rows)
            record = result.single()
            return record["c"] if record else 0

    def clear_by_version(self, tenant: str, ontology_version: str) -> dict:
        query = """
        MATCH (e:Entity {tenant: $tenant, ontology_version: $ontology_version})
        OPTIONAL MATCH (e)-[r:REL]-()
        DELETE r, e
        RETURN count(DISTINCT e) AS entities
        """
        with get_session() as session:
            result = session.run(query, tenant=tenant, ontology_version=ontology_version)
            record = result.single()
            return {"entities_deleted": record["entities"] if record else 0}
