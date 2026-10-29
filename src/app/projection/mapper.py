from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .graphdb_client import Triple

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

_XSD = "http://www.w3.org/2001/XMLSchema#"
_XSD_INTEGERS = {
    _XSD + name
    for name in (
        "integer",
        "int",
        "long",
        "short",
        "byte",
        "nonNegativeInteger",
        "nonPositiveInteger",
        "negativeInteger",
        "positiveInteger",
        "unsignedLong",
        "unsignedInt",
        "unsignedShort",
        "unsignedByte",
    )
}
_XSD_FLOATS = {_XSD + name for name in ("decimal", "double", "float")}
_XSD_BOOLEAN = _XSD + "boolean"

# Labels are chosen in this order: untagged, Korean, English, then the first
# remaining language. Tools can rely on `properties["label"]` being readable.
_LANGUAGE_PREFERENCE = (None, "ko", "en")


def _local_name(iri: str) -> str:
    if "#" in iri:
        value = iri.rsplit("#", 1)[-1]
    else:
        value = iri.rstrip("/").rsplit("/", 1)[-1]
    return value or iri


def is_blank_node(term: str) -> bool:
    return term.startswith("_:")


def _convert_literal(value: str, datatype: str | None) -> Any:
    """Store numbers and booleans natively so Cypher can compare them.

    Dates stay as ISO-8601 strings: mixing naive and zoned temporal values in one
    Neo4j property is an error, and sorting ISO strings is good enough for v1.
    """
    if datatype in _XSD_INTEGERS:
        try:
            return int(value)
        except ValueError:
            return value
    if datatype in _XSD_FLOATS:
        try:
            return float(value)
        except ValueError:
            return value
    if datatype == _XSD_BOOLEAN:
        return value.strip().lower() in {"true", "1"}
    return value


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _add_property(properties: dict[str, Any], key: str, value: Any) -> None:
    if key not in properties:
        properties[key] = value
        return

    existing = properties[key]
    if isinstance(existing, list):
        if value in existing:
            return
        # Neo4j arrays must be homogeneous, so a mixed predicate degrades to strings.
        if any(type(item) is not type(value) for item in existing):
            existing[:] = [_stringify(item) for item in existing]
            value = _stringify(value)
        if value not in existing:
            existing.append(value)
        return

    if existing == value and type(existing) is type(value):
        return
    if type(existing) is type(value):
        properties[key] = [existing, value]
        return
    properties[key] = [_stringify(existing), _stringify(value)]


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
    tenant: str = ""
    ontology_version: str = ""
    inferred: bool = False
    rule_id: str | None = None
    source_graph: str = ""


@dataclass
class MapResult:
    entities: list[Entity] = field(default_factory=list)
    rels: list[Rel] = field(default_factory=list)
    blank_nodes_skipped: int = 0
    rels_dropped: int = 0


class ProjectionMapper:
    def map(
        self,
        triples: list[Triple],
        tenant: str,
        ontology_version: str,
        source_graph: str,
        *,
        inferred: bool = False,
        rule_id: str | None = None,
    ) -> MapResult:
        types: dict[str, list[str]] = defaultdict(list)
        literals: dict[str, dict[str, Any]] = defaultdict(dict)
        labels: dict[str, list[tuple[str | None, str]]] = defaultdict(list)
        subjects: set[str] = set()
        rels: list[Rel] = []
        blank_nodes: set[str] = set()
        rels_dropped = 0

        for triple in triples:
            if is_blank_node(triple.s):
                blank_nodes.add(triple.s)
                if triple.p != RDF_TYPE and triple.o_type == "uri" and not is_blank_node(triple.o):
                    rels_dropped += 1
                continue

            subjects.add(triple.s)

            if triple.o_type == "uri" and is_blank_node(triple.o):
                blank_nodes.add(triple.o)
                if triple.p != RDF_TYPE:
                    rels_dropped += 1
                continue

            if triple.p == RDF_TYPE and triple.o_type == "uri":
                types[triple.s].append(triple.o)
                continue

            if triple.o_type == "literal":
                if triple.p == RDFS_LABEL:
                    labels[triple.s].append((triple.o_lang, triple.o))
                    continue
                key = _local_name(triple.p)
                _add_property(literals[triple.s], key, _convert_literal(triple.o, triple.o_datatype))
                continue

            if triple.o_type == "uri":
                rels.append(
                    Rel(
                        from_iri=triple.s,
                        to_iri=triple.o,
                        predicate=triple.p,
                        tenant=tenant,
                        ontology_version=ontology_version,
                        inferred=inferred,
                        rule_id=rule_id,
                        source_graph=source_graph,
                    )
                )

        # Every IRI that appears in the data becomes a node, even without rdf:type.
        # Otherwise relations to external IRIs cannot be projected: the endpoint
        # MATCH finds nothing and the edge is lost.
        entity_iris = set(subjects)
        entity_iris.update(rel.to_iri for rel in rels)
        entity_iris.update(types)

        entities: list[Entity] = []
        for iri in sorted(entity_iris):
            type_list = sorted(set(types.get(iri, [])))
            properties = dict(literals.get(iri, {}))

            label, label_lang = _pick_label(labels.get(iri, []))
            if label is None:
                label = _local_name(type_list[0]) if type_list else _local_name(iri)
            properties["label"] = label
            if label_lang is not None:
                properties["label_lang"] = label_lang

            entities.append(
                Entity(
                    iri=iri,
                    tenant=tenant,
                    ontology_version=ontology_version,
                    labels=type_list,
                    properties=properties,
                    inferred=inferred,
                    source_graph=source_graph,
                )
            )

        return MapResult(
            entities=entities,
            rels=rels,
            blank_nodes_skipped=len(blank_nodes),
            rels_dropped=rels_dropped,
        )


def _pick_label(candidates: list[tuple[str | None, str]]) -> tuple[str | None, str | None]:
    if not candidates:
        return None, None

    by_lang: dict[str | None, str] = {}
    for lang, value in candidates:
        by_lang.setdefault(lang, value)

    for lang in _LANGUAGE_PREFERENCE:
        if lang in by_lang:
            return by_lang[lang], lang
    lang = sorted(by_lang, key=lambda item: item or "")
    return by_lang[lang[0]], lang[0]
