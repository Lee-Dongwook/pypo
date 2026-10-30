// Projection key is (tenant, ontology_version, iri). Version and tenant have to be
// part of the key: with an IRI-only key, re-projecting v2 overwrites v1 nodes and a
// shared external IRI lets one tenant overwrite another. Dropping the old constraint
// is safe because Neo4j is a rebuildable read model.
DROP CONSTRAINT entity_iri_unique IF EXISTS;

CREATE CONSTRAINT entity_key_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.tenant, e.ontology_version, e.iri) IS UNIQUE;

// Indexes for lookups
CREATE INDEX entity_tenant_version IF NOT EXISTS
FOR (e:Entity) ON (e.tenant, e.ontology_version);

CREATE INDEX entity_labels IF NOT EXISTS
FOR (e:Entity) ON (e.labels);

CREATE INDEX entity_source_graph IF NOT EXISTS
FOR (e:Entity) ON (e.source_graph);

// Relation indexes
CREATE INDEX rel_predicate IF NOT EXISTS
FOR ()-[r:REL]-() ON (r.predicate);

CREATE INDEX rel_source_graph IF NOT EXISTS
FOR ()-[r:REL]-() ON (r.source_graph);

CREATE INDEX rel_tenant_version IF NOT EXISTS
FOR ()-[r:REL]-() ON (r.tenant, r.ontology_version);

// Knowledge search: keep this name and field list in sync with
// src/app/engine/search/queries.py.
CREATE FULLTEXT INDEX combinedIndex IF NOT EXISTS
FOR (n:Link|Memo|File) ON EACH [n.title, n.tags, n.description]
OPTIONS {indexConfig: {`fulltext.analyzer`: 'cjk'}};

// Personal knowledge graph written by src/app/engine/search/graph.py.
CREATE CONSTRAINT user_uuid_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.uuid IS UNIQUE;

CREATE CONSTRAINT link_uuid_unique IF NOT EXISTS
FOR (n:Link) REQUIRE n.uuid IS UNIQUE;

CREATE CONSTRAINT memo_uuid_unique IF NOT EXISTS
FOR (n:Memo) REQUIRE n.uuid IS UNIQUE;

CREATE CONSTRAINT file_uuid_unique IF NOT EXISTS
FOR (n:File) REQUIRE n.uuid IS UNIQUE;

CREATE CONSTRAINT tag_user_name_unique IF NOT EXISTS
FOR (t:Tag) REQUIRE (t.user_uuid, t.name) IS UNIQUE;

CREATE INDEX link_user_created IF NOT EXISTS
FOR (n:Link) ON (n.user_uuid, n.created_at);

CREATE INDEX memo_user_created IF NOT EXISTS
FOR (n:Memo) ON (n.user_uuid, n.created_at);

CREATE INDEX file_user_created IF NOT EXISTS
FOR (n:File) ON (n.user_uuid, n.created_at);
