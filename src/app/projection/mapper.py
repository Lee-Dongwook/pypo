from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .graphdb_client import Triple


RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


@dataclass
class Entity:
    iri: str
    tenant: str
    ontology_version: str
    labels: list[str]
    properties: dict[str, Any]
    inferred: bool = False
    source_graph: str = ""


@dataclass
class Rel:
    from_iri: str
    to_iri: str
    predicate: str
    inferred: bool = False
    rule_id: str | None = None
    source_graph: str = ""


def _local_name(iri: str) -> str:
    if "#" in iri:
        return iri.rsplit("#", 1)[-1]
    return iri.rstrip("/").rsplit("/", 1)[-1]


class ProjectionMapper:
    def map(
        self,
        triples: list[Triple],
        tenant: str,
        ontology_version: str,
        source_graph: str,
    ) -> tuple[list[Entity], list[Rel]]:
        types: dict[str, list[str]] = defaultdict(list)
        literals: dict[str, dict[str, Any]] = defaultdict(dict)
        rels: list[Rel] = []

        for triple in triples:
            if triple.p == RDF_TYPE and triple.o_type == "uri":
                types[triple.s].append(triple.o)
                continue

            if triple.o_type == "literal":
                if triple.p == RDFS_LABEL:
                    literals[triple.s]["label"] = triple.o
                    continue
                key = _local_name(triple.p)
                if key and key not in literals[triple.s]:
                    literals[triple.s][key] = triple.o
                continue

            if triple.o_type == "uri":
                rels.append(
                    Rel(
                        from_iri=triple.s,
                        to_iri=triple.o,
                        predicate=triple.p,
                        inferred=False,
                        rule_id=None,
                        source_graph=source_graph,
                    )
                )

        entities: list[Entity] = []
        for iri, type_list in types.items():
            props = dict(literals.get(iri, {}))
            if type_list:
                fallback_label = _local_name(type_list[-1])
            else:
                fallback_label = iri
            label = props.pop("label", fallback_label)
            entities.append(
                Entity(
                    iri=iri,
                    tenant=tenant,
                    ontology_version=ontology_version,
                    labels=type_list,
                    properties={"label": label, **props},
                    inferred=False,
                    source_graph=source_graph,
                )
            )

        return entities, rels
