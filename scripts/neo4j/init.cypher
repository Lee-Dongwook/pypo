// Entity uniqueness
CREATE CONSTRAINT entity_iri_unique IF NOT EXISTS
FOR (e:Entity)
REQUIRE e.iri IS UNIQUE;

// Query Optimization
CREATE INDEX entity_tenant_version IF NOT EXISTS
FOR (e:Entity)
ON (e.tenant, e.ontology_version);

CREATE INDEX entity_labels IF NOT EXISTS
FOR (e:Entity)
ON (e.labels);

CREATE INDEX entity_source_graph IF NOT EXISTS
FOR (e:Entity)
ON (e.source_graph);

// Relation predicate lookup
CREATE INDEX rel_predicate IF NOT EXISTS
FOR ()-[r:REL]-()
ON (r.predicate);
