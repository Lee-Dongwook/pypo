from __future__ import annotations

import os
import uuid

import pytest
from neo4j import Driver, GraphDatabase

from src.app.projection.graphdb_client import Triple
from src.app.projection.mapper import RDF_TYPE, Entity, ProjectionMapper
from src.app.projection.neo4j_client import Neo4jProjectionClient

pytestmark = pytest.mark.integration

NEO4J_URI = os.environ.get("NEO4J_TEST_URI")
GRAPH = "urn:pypo:test:v1:data"


@pytest.fixture(scope="module")
def driver() -> Driver:
    if not NEO4J_URI:
        pytest.skip("set NEO4J_TEST_URI to run Neo4j integration tests")

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password")),
    )
    driver.verify_connectivity()
    yield driver
    driver.close()


@pytest.fixture
def tenant() -> str:
    return f"it-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client(driver: Driver, tenant: str):
    projection = Neo4jProjectionClient(driver)
    yield projection
    projection.clear_version(tenant, "v1")


def _count(driver: Driver, query: str, **params: object) -> int:
    with driver.session() as session:
        return session.run(query, **params).single()["c"]


def test_same_iri_in_two_tenants_stays_separate(driver: Driver) -> None:
    client = Neo4jProjectionClient(driver)
    tenants = [f"it-{uuid.uuid4().hex[:8]}" for _ in range(2)]

    try:
        for name in tenants:
            client.upsert_entities(
                [
                    Entity(
                        iri="urn:shared:entity",
                        tenant=name,
                        ontology_version="v1",
                        labels=["urn:Thing"],
                        properties={"label": name, "quantity": 3, "paid": True, "alias": ["a", "b"]},
                        source_graph=GRAPH,
                    )
                ]
            )

        count = _count(
            driver,
            "MATCH (e:Entity {iri: 'urn:shared:entity'}) WHERE e.tenant IN $tenants RETURN count(e) AS c",
            tenants=tenants,
        )
        assert count == 2

        quantity = _count(
            driver,
            "MATCH (e:Entity {tenant: $tenant, iri: 'urn:shared:entity'}) RETURN e.quantity AS c",
            tenant=tenants[0],
        )
        aliases = _count(
            driver,
            "MATCH (e:Entity {tenant: $tenant, iri: 'urn:shared:entity'}) RETURN size(e.alias) AS c",
            tenant=tenants[0],
        )
        assert quantity == 3
        assert aliases == 2

        client.clear_version(tenants[0], "v1")

        remaining = _count(
            driver,
            "MATCH (e:Entity {iri: 'urn:shared:entity'}) WHERE e.tenant IN $tenants RETURN count(e) AS c",
            tenants=tenants,
        )
        assert remaining == 1
    finally:
        for name in tenants:
            client.clear_version(name, "v1")


def test_relation_to_untyped_iri_is_kept(client: Neo4jProjectionClient, driver: Driver, tenant: str) -> None:
    triples = [
        Triple(s="urn:product:1", p=RDF_TYPE, o="urn:Product", o_type="uri"),
        Triple(s="urn:product:1", p="urn:hasSupplier", o="urn:supplier:1", o_type="uri"),
    ]
    mapping = ProjectionMapper().map(triples, tenant, "v1", GRAPH)

    client.upsert_entities(mapping.entities)
    assert client.upsert_rels(mapping.rels) == 1

    rel_count = _count(
        driver,
        """
        MATCH (a:Entity {tenant: $tenant, ontology_version: 'v1'})-[r:REL {predicate: 'urn:hasSupplier'}]->(b)
        RETURN count(r) AS c
        """,
        tenant=tenant,
    )
    assert rel_count == 1

    stub = _count(
        driver,
        "MATCH (e:Entity {tenant: $tenant, iri: 'urn:supplier:1'}) RETURN count(e) AS c",
        tenant=tenant,
    )
    assert stub == 1


def test_clear_source_graph_removes_that_graph_only(client: Neo4jProjectionClient, driver: Driver, tenant: str) -> None:
    mapper = ProjectionMapper()

    first = mapper.map([Triple("urn:a", RDF_TYPE, "urn:Thing", "uri")], tenant, "v1", "urn:graph:a")
    second = mapper.map([Triple("urn:b", RDF_TYPE, "urn:Thing", "uri")], tenant, "v1", "urn:graph:b")
    client.upsert_entities(first.entities + second.entities)

    assert client.clear_source_graph(tenant, "v1", "urn:graph:a") == 1

    remaining = _count(
        driver,
        "MATCH (e:Entity {tenant: $tenant, ontology_version: 'v1'}) RETURN count(e) AS c",
        tenant=tenant,
    )
    assert remaining == 1


def test_clear_version_removes_relations_too(client: Neo4jProjectionClient, driver: Driver, tenant: str) -> None:
    mapping = ProjectionMapper().map(
        [Triple("urn:a", "urn:relatedTo", "urn:b", "uri")],
        tenant,
        "v1",
        GRAPH,
    )
    client.upsert_entities(mapping.entities)
    client.upsert_rels(mapping.rels)

    assert client.clear_version(tenant, "v1") == 2

    nodes = _count(
        driver,
        "MATCH (e:Entity {tenant: $tenant, ontology_version: 'v1'}) RETURN count(e) AS c",
        tenant=tenant,
    )
    rels = _count(
        driver,
        "MATCH (:Entity {tenant: $tenant})-[r:REL]->() RETURN count(r) AS c",
        tenant=tenant,
    )
    assert nodes == 0
    assert rels == 0
