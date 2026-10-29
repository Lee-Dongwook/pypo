from __future__ import annotations

from typing import Any

from .graphdb_client import GraphDBClient, ProjectionTooLarge, Triple
from .mapper import Entity, MapResult, ProjectionMapper, Rel
from .neo4j_client import Neo4jProjectionClient

DEFAULT_MAX_TRIPLES = 2_000_000


class ProjectionService:
    def __init__(
        self,
        graphdb: GraphDBClient | None = None,
        mapper: ProjectionMapper | None = None,
        neo4j: Neo4jProjectionClient | None = None,
        *,
        max_triples: int | None = DEFAULT_MAX_TRIPLES,
    ) -> None:
        self.graphdb = graphdb or GraphDBClient()
        self.mapper = mapper or ProjectionMapper()
        self.neo4j = neo4j or Neo4jProjectionClient()
        self.max_triples = max_triples

    async def rebuild_from_graph(
        self,
        graph_iri: str,
        tenant: str,
        ontology_version: str,
        *,
        inferred: bool = False,
        rule_id: str | None = None,
        replace: bool = True,
        max_triples: int | None = None,
    ) -> dict[str, Any]:
        """Project one named graph, removing that graph's previous projection.

        Fetching happens before anything is deleted, so a store error leaves the
        existing projection intact. When a version is made of several named graphs,
        prefer `rebuild_from_graphs`: clearing one graph can remove nodes shared with
        the others.
        """
        limit = self.max_triples if max_triples is None else max_triples
        triples = await self.graphdb.fetch_triples(graph_iri, max_triples=limit)

        deleted = self.neo4j.clear_source_graph(tenant, ontology_version, graph_iri) if replace else 0
        mapping = self.mapper.map(
            triples,
            tenant,
            ontology_version,
            graph_iri,
            inferred=inferred,
            rule_id=rule_id,
        )
        return self._load(mapping, len(triples), deleted, graph_iri)

    async def rebuild_from_graphs(
        self,
        graphs: list[str],
        tenant: str,
        ontology_version: str,
        *,
        inferred: bool = False,
        inferred_graphs: set[str] | None = None,
        rule_id: str | None = None,
        replace: bool = True,
        max_triples: int | None = None,
    ) -> dict[str, Any]:
        """Project several named graphs as one ontology version.

        All graphs are fetched first, then the version is cleared once and loaded.
        `max_triples` applies per graph. `inferred_graphs` marks only those graphs as
        inferred; without it, `inferred` applies to every graph. Graphs are merged
        before writing so an inferred graph cannot overwrite asserted labels or mark
        shared entities as inferred; values from earlier graphs win when they conflict.
        """
        limit = self.max_triples if max_triples is None else max_triples
        fetched: list[tuple[str, list[Triple]]] = []
        for graph_iri in graphs:
            fetched.append((graph_iri, await self.graphdb.fetch_triples(graph_iri, max_triples=limit)))

        deleted = self.neo4j.clear_version(tenant, ontology_version) if replace else 0

        mappings = []
        for graph_iri, triples in fetched:
            is_inferred = inferred if inferred_graphs is None else graph_iri in inferred_graphs
            mappings.append(
                self.mapper.map(
                    triples,
                    tenant,
                    ontology_version,
                    graph_iri,
                    inferred=is_inferred,
                    rule_id=rule_id,
                )
            )
        merged = _merge_mappings(mappings)

        entities = self.neo4j.upsert_entities(merged.entities)
        rels = self.neo4j.upsert_rels(merged.rels)

        graphs_report = [
            {
                "graph": graph_iri,
                "triples_fetched": len(triples),
                "entities_mapped": len(mapping.entities),
                "rels_mapped": len(mapping.rels),
                "blank_nodes_skipped": mapping.blank_nodes_skipped,
                "rels_dropped": mapping.rels_dropped,
            }
            for (graph_iri, triples), mapping in zip(fetched, mappings, strict=True)
        ]
        totals = {
            "triples_fetched": sum(len(triples) for _, triples in fetched),
            "entities_upserted": entities,
            "rels_upserted": rels,
            "rels_dropped": merged.rels_dropped + (len(merged.rels) - rels),
            "blank_nodes_skipped": merged.blank_nodes_skipped,
        }

        return {"deleted_entities": deleted, "graphs": graphs_report, "totals": totals}

    def _load(
        self,
        mapping: MapResult,
        triples_fetched: int,
        deleted: int,
        graph_iri: str,
    ) -> dict[str, Any]:
        entities = self.neo4j.upsert_entities(mapping.entities)
        rels = self.neo4j.upsert_rels(mapping.rels)

        return {
            "graph": graph_iri,
            "deleted_entities": deleted,
            "triples_fetched": triples_fetched,
            "entities_upserted": entities,
            "rels_upserted": rels,
            # Endpoints now always exist as stub nodes, but blank nodes and any
            # remaining unmatched endpoints are reported instead of vanishing.
            "rels_dropped": mapping.rels_dropped + (len(mapping.rels) - rels),
            "blank_nodes_skipped": mapping.blank_nodes_skipped,
        }


def _merge_mappings(mappings: list[MapResult]) -> MapResult:
    """Fold per-graph mappings into one write for a whole ontology version."""
    entities: dict[str, Entity] = {}
    rels: dict[tuple[str, str, str], Rel] = {}
    blank_nodes = 0
    rels_dropped = 0

    for mapping in mappings:
        blank_nodes += mapping.blank_nodes_skipped
        rels_dropped += mapping.rels_dropped

        for entity in mapping.entities:
            current = entities.get(entity.iri)
            if current is None:
                entities[entity.iri] = Entity(
                    iri=entity.iri,
                    tenant=entity.tenant,
                    ontology_version=entity.ontology_version,
                    labels=list(entity.labels),
                    properties=dict(entity.properties),
                    inferred=entity.inferred,
                    source_graph=entity.source_graph,
                )
                continue

            current.labels = sorted(set(current.labels) | set(entity.labels))
            # Earlier graphs win, so a sparse inferred stub cannot replace an
            # asserted label or property with the IRI's local name.
            current.properties = {**entity.properties, **current.properties}
            current.inferred = current.inferred and entity.inferred

        for rel in mapping.rels:
            key = (rel.from_iri, rel.to_iri, rel.predicate)
            current_rel = rels.get(key)
            if current_rel is None:
                rels[key] = Rel(
                    from_iri=rel.from_iri,
                    to_iri=rel.to_iri,
                    predicate=rel.predicate,
                    tenant=rel.tenant,
                    ontology_version=rel.ontology_version,
                    inferred=rel.inferred,
                    rule_id=rel.rule_id,
                    source_graph=rel.source_graph,
                )
                continue

            current_rel.inferred = current_rel.inferred and rel.inferred
            if current_rel.rule_id is None:
                current_rel.rule_id = rel.rule_id

    return MapResult(
        entities=[entities[iri] for iri in sorted(entities)],
        rels=[rels[key] for key in sorted(rels)],
        blank_nodes_skipped=blank_nodes,
        rels_dropped=rels_dropped,
    )


__all__ = ["DEFAULT_MAX_TRIPLES", "ProjectionService", "ProjectionTooLarge"]
