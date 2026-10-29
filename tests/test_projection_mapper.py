from src.app.projection.graphdb_client import Triple
from src.app.projection.mapper import (
    RDF_TYPE,
    RDFS_LABEL,
    MapResult,
    ProjectionMapper,
    is_blank_node,
)

EX = "https://data.pypo.dev/test/ontology/"
XSD_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"
XSD_BOOLEAN = "http://www.w3.org/2001/XMLSchema#boolean"
XSD_DATE = "http://www.w3.org/2001/XMLSchema#date"


def _uri(s: str, p: str, o: str) -> Triple:
    return Triple(s=s, p=p, o=o, o_type="uri")


def _literal(s: str, p: str, o: str, datatype: str | None = None, lang: str | None = None) -> Triple:
    return Triple(s=s, p=p, o=o, o_type="literal", o_lang=lang, o_datatype=datatype)


def _map(*triples: Triple) -> MapResult:
    return ProjectionMapper().map(list(triples), "acme", "v1", "urn:graph")


def test_typed_entity_gets_labels_and_label() -> None:
    result = _map(
        _uri(EX + "Product", RDF_TYPE, EX + "Product"),
        _literal(EX + "Product", RDFS_LABEL, "제품", lang="ko"),
    )

    entity = result.entities[0]
    assert entity.labels == [EX + "Product"]
    assert entity.properties["label"] == "제품"
    assert entity.properties["label_lang"] == "ko"


def test_label_language_preference() -> None:
    result = _map(
        _uri(EX + "Supplier", RDF_TYPE, EX + "Supplier"),
        _literal(EX + "Supplier", RDFS_LABEL, "Supplier", lang="en"),
        _literal(EX + "Supplier", RDFS_LABEL, "공급사", lang="ko"),
    )

    assert result.entities[0].properties["label"] == "공급사"


def test_untagged_label_wins() -> None:
    result = _map(
        _literal(EX + "Supplier", RDFS_LABEL, "Supplier A", lang="en"),
        _literal(EX + "Supplier", RDFS_LABEL, "Supplier A"),
    )

    assert result.entities[0].properties["label"] == "Supplier A"
    assert "label_lang" not in result.entities[0].properties


def test_untyped_iri_becomes_stub_node() -> None:
    result = _map(_uri(EX + "Product", EX + "hasSupplier", "https://external.example/supplier/1"))

    iris = {entity.iri for entity in result.entities}
    assert "https://external.example/supplier/1" in iris

    stub = next(e for e in result.entities if e.iri == "https://external.example/supplier/1")
    assert stub.labels == []
    assert stub.properties["label"] == "1"


def test_relation_is_projected_to_a_stub_endpoint() -> None:
    result = _map(_uri(EX + "Product", EX + "hasSupplier", "https://external.example/supplier/1"))

    assert len(result.rels) == 1
    rel = result.rels[0]
    assert rel.from_iri == EX + "Product"
    assert rel.to_iri == "https://external.example/supplier/1"
    assert rel.tenant == "acme"
    assert rel.ontology_version == "v1"


def test_subject_with_only_literals_is_projected() -> None:
    result = _map(_literal(EX + "Note", EX + "text", "hello"))

    assert [entity.iri for entity in result.entities] == [EX + "Note"]


def test_blank_nodes_are_skipped_and_reported() -> None:
    result = _map(
        _literal("_:b0", RDFS_LABEL, "anonymous"),
        _uri(EX + "Product", EX + "hasPart", "_:b1"),
    )

    assert [entity.iri for entity in result.entities] == [EX + "Product"]
    assert result.blank_nodes_skipped == 2
    assert result.rels_dropped == 1
    assert is_blank_node("_:b0") is True


def test_repeated_literals_become_a_list() -> None:
    result = _map(
        _literal(EX + "Product", EX + "alias", "P1"),
        _literal(EX + "Product", EX + "alias", "P2"),
    )

    assert result.entities[0].properties["alias"] == ["P1", "P2"]


def test_duplicate_literals_are_collapsed() -> None:
    result = _map(
        _literal(EX + "Product", EX + "alias", "P1"),
        _literal(EX + "Product", EX + "alias", "P1"),
    )

    assert result.entities[0].properties["alias"] == "P1"


def test_numeric_and_boolean_literals_keep_their_type() -> None:
    result = _map(
        _literal(EX + "Order", EX + "quantity", "3", datatype=XSD_INTEGER),
        _literal(EX + "Order", EX + "paid", "true", datatype=XSD_BOOLEAN),
        _literal(EX + "Order", EX + "placedOn", "2026-10-29", datatype=XSD_DATE),
    )

    properties = result.entities[0].properties
    assert properties["quantity"] == 3
    assert properties["paid"] is True
    assert properties["placedOn"] == "2026-10-29"


def test_inferred_flag_and_rule_id_are_propagated() -> None:
    result = ProjectionMapper().map(
        [_uri(EX + "A", EX + "relatedTo", EX + "B")],
        "acme",
        "v1",
        "urn:inferred",
        inferred=True,
        rule_id="rule-7",
    )

    assert all(entity.inferred for entity in result.entities)
    assert result.rels[0].inferred is True
    assert result.rels[0].rule_id == "rule-7"


def test_multiple_types_are_sorted_and_deduplicated() -> None:
    result = _map(
        _uri(EX + "A", RDF_TYPE, EX + "Z"),
        _uri(EX + "A", RDF_TYPE, EX + "B"),
        _uri(EX + "A", RDF_TYPE, EX + "B"),
    )

    assert result.entities[0].labels == [EX + "B", EX + "Z"]


def test_rdf_type_is_not_projected_as_a_relation() -> None:
    result = _map(_uri(EX + "A", RDF_TYPE, EX + "B"))

    assert result.rels == []


def test_mixed_literal_types_degrade_to_a_string_list() -> None:
    result = _map(
        _literal(EX + "Order", EX + "quantity", "3", datatype=XSD_INTEGER),
        _literal(EX + "Order", EX + "quantity", "3 (estimated)"),
    )

    assert result.entities[0].properties["quantity"] == ["3", "3 (estimated)"]
