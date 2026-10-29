from __future__ import annotations

from .graphdb_client import GraphDBClient
from .mapper import ProjectionMapper
from .neo4j_client import Neo4jProjectionClient


class ProjectionService:
    def __init__(self) -> None:
        self.graphdb = GraphDBClient()
        self.mapper = ProjectionMapper()
        self.neo4j = Neo4jProjectionClient()

    async def rebuild_from_graph(self, graph_iri: str, tenant: str, ontology_version: str) -> dict:
        triples = await self.graphdb.fetch_triples(graph_iri)
        entities, rels = self.mapper.map(triples, tenant, ontology_version, graph_iri)
        ec = self.neo4j.upsert_entities(entities)
        rc = self.neo4j.upsert_rels(rels)
        return {
            "graph": graph_iri,
            "triples_fetched": len(triples),
            "entities_upserted": ec,
            "rels_upserted": rc,
        }

    async def rebuild_from_graphs(
        self,
        graphs: list[str],
        tenant: str,
        ontology_version: str,
    ) -> list[dict]:
        results: list[dict] = []
        for graph_iri in graphs:
            res = await self.rebuild_from_graph(graph_iri, tenant, ontology_version)
            results.append(res)
        return results
