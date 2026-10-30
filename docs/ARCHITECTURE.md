# pypo Architecture

이 문서는 pypo의 **목표 아키텍처**를 정리합니다. 현재 저장소는 스캐폴딩 단계이므로, 여기 적힌 구성 요소 중 일부는 아직 구현되지 않았습니다.

## 1. 목표와 비목표

### 목표

- 도메인 지식을 OWL/RDF 온톨로지로 표현하고 버전 관리한다.
- GraphDB를 온톨로지 원장으로, Neo4j를 탐색·분석용 읽기 투영으로 사용한다.
- 온톨로지를 MCP 서버로 노출해 에이전트와 외부 클라이언트가 같은 방식으로 사용하게 한다.
- 벡터 검색과 그래프 탐색, 추론을 결합해 근거 있는 답변을 만든다.
- 자체 세션과 OIDC를 모두 제공하되 단일 Principal로 권한을 판단한다.
- 멀티테넌트 환경에서 온톨로지와 실행을 격리한다.
- 지식 변경이 답변 재현성을 깨지 않도록 온톨로지 버전을 고정한다.

### 비목표 (지금 하지 않는 것)

- 자체 트리플 스토어나 SPARQL 엔진을 만들지 않는다.
- OWL DL 전체를 직접 구현하지 않는다. v1은 OWL 2 RL과 SPARQL CONSTRUCT 규칙으로 시작한다.
- 온톨로지 편집 UI를 API보다 먼저 만들지 않는다.
- 범용 챗봇을 만들지 않는다. 지식이 필요한 도메인 에이전트에 집중한다.

## 2. 시스템 컨텍스트

```text
┌──────────────┐        ┌──────────────────┐
│ Web / API    │        │ External MCP     │
│ Client       │        │ Client           │
└──────┬───────┘        └────────┬─────────┘
       │                         │
       ▼                         ▼
┌─────────────────────────────────────────┐
│ Control Plane (FastAPI)                 │
│ auth · tenant · agents · ontologies     │
│ ingestion · admin · observability       │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ Agent Runtime (LangGraph)               │
│ Supervisor · Sub-agents · Tool Registry │
└────────┬───────────────────────┬────────┘
         │ MCP                   │ MCP
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│ Ontology Service │    │ Knowledge Search │
│ schema · query   │    │ vector · rerank  │
│ reason · validate│    │                  │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│ GraphDB          │    │ PostgreSQL       │
│ RDF · OWL 2 RL   │    │ pgvector         │
└────────┬─────────┘    └──────────────────┘
         │ outbox + Celery projection
┌────────▼─────────┐
│ Neo4j            │
│ Cypher · GDS     │
└──────────────────┘

┌──────────────────┐    ┌──────────────────┐
│ Object Storage   │    │ Redis / Celery   │
│ ontology files   │    │ jobs · cache     │
└──────────────────┘    └──────────────────┘
```

**Control plane**은 설정과 관리(에이전트, 온톨로지, 적재, 권한)를 담당합니다. **Data plane**은 MCP 도구로 노출되어 실제 질의와 추론을 처리합니다. 두 영역을 분리해야 외부 에이전트가 control plane을 거치지 않고 지식에 접근할 수 있습니다.

## 3. 핵심 결정

### ADR-001. 온톨로지를 MCP 서버로 노출한다

에이전트 내부 함수로만 두면 다른 에이전트, 다른 런타임, 외부 고객이 같은 지식을 쓸 수 없습니다. 온톨로지 서비스를 독립 MCP 서버로 두면 지식 계층이 제품 경계가 됩니다.

- 장점: 재사용, 언어/런타임 독립, 권한·쿼터를 한 곳에서 통제
- 단점: 프로세스 경계와 직렬화 비용, MCP 스펙 변화 추종 필요
- 완화: in-process 어댑터를 두되 계약은 MCP 스키마를 단일 출처로 사용

### ADR-002. GraphDB를 원장으로, Neo4j를 읽기 투영으로 둔다

Neo4j는 RDF 트리플 스토어가 아니라 property graph DB입니다. Neo4j를 온톨로지 원장으로 쓰면 SPARQL 1.1, SHACL, OWL 2 RL을 그대로 쓸 수 없고, `n10s`로 RDF를 적재하더라도 추론과 질의 의미론은 상당 부분 직접 구현해야 합니다.

그래서 역할을 나눕니다.

| 시스템 | 역할 | 근거 |
|---|---|---|
| **GraphDB** | 온톨로지 원장(system of record) | OWL 2 RL, SHACL, SPARQL 1.1, named graph, provenance |
| **Neo4j** | 읽기 투영(read model) | Cypher, GDS 중심성·커뮤니티·유사도, Bloom 시각화, 빠른 다중 hop |
| **Oxigraph** | 개발/CI | embedded, 빠른 기동, 테스트 친화 |
| **Stardog** | 관계형 virtual graph POC | 기존 DB를 RDF로 가상화할 필요가 생길 때만 검토 |

- 쓰기는 GraphDB로만 들어갑니다.
- Neo4j는 GraphDB와 PostgreSQL outbox에서 파생되며, 언제든 전체 재생성할 수 있습니다.
- 추론된 트리플도 Neo4j에 투영하되 `inferred: true`와 규칙 ID를 남깁니다.
- 에이전트 도구는 의미론 질의를 GraphDB로, 탐색·분석을 Neo4j로 라우팅합니다.

```python
class OntologyStore(Protocol):
    async def query(self, sparql: str, graphs: list[str]) -> list[dict]: ...
    async def update(self, sparql: str, graph: str) -> None: ...
    async def load(self, data: bytes, graph: str, content_type: str) -> None: ...
    async def validate(self, shapes: bytes, graph: str) -> ValidationReport: ...
    async def materialize(self, graph: str) -> MaterializeReport: ...

class GraphProjection(Protocol):
    async def upsert(self, entities: list[Entity], edges: list[Edge]) -> None: ...
    async def delete(self, iris: list[str], version: str) -> None: ...
    async def rebuild(self, ontology_version_id: str) -> ProjectionReport: ...
    async def reconcile(self, ontology_version_id: str) -> DriftReport: ...
```

Neo4j 단독 구성도 가능하지만, 그 경우 SPARQL·SHACL·표준 추론을 포기하고 규칙 엔진과 질의 계층을 직접 만들어야 합니다. v1에서는 채택하지 않습니다.

### ADR-007. 투영은 outbox + Celery로 동기화한다

- GraphDB 쓰기와 같은 업무 트랜잭션에서 PostgreSQL outbox에 변경 이벤트를 기록합니다.
- Celery worker가 이벤트를 읽어 Neo4j에 멱등 upsert합니다.
- 이벤트에는 `ontology_version_id`, `graph`, `iri`, `op`, `seq`를 넣습니다.
- 새 온톨로지 버전은 새 projection namespace에 적재한 뒤 alias를 전환합니다.
- 야간 reconciliation job이 트리플 수, checksum, 샘플 엔티티를 비교해 drift를 잡습니다.
- 투영 지연은 허용하되, 답변에 `source`와 `as_of`를 표시해 어느 저장소를 읽었는지 밝힙니다.

### ADR-008. 인증은 세션과 OIDC를 하나의 Principal로 수렴한다

자체 세션과 OIDC를 모두 제공하되, 권한 판단은 단일 `Principal` 모델에서 수행합니다.

- **자체 세션**: Argon2id 비밀번호 또는 이메일 매직링크, HttpOnly/Secure/SameSite 쿠키, Redis 세션 저장, 로그인 시 세션 회전, CSRF 토큰.
- **OIDC**: authorization code + PKCE, tenant별 IdP 등록, JIT 프로비저닝, 그룹→역할 매핑, issuer/domain으로 tenant 바인딩.
- **API/MCP**: Bearer 토큰. MCP 클라이언트는 OAuth 2.1 리소스 서버 모델을 따릅니다.
- **계정 연결**: 검증된 이메일을 기준으로 `user_identity`에 provider/subject를 분리 저장합니다.
- **권한**: `owner/admin/editor/viewer` 역할과 `read/admin` 도구 스코프를 함께 검사합니다.
- **감사**: 로그인, 토큰 발급, 권한 변경, admin 도구 호출을 `audit_log`에 남깁니다.

### ADR-003. 검색은 벡터 + 그래프 하이브리드로 간다

벡터 검색은 표현이 다른 질문을 잘 찾지만 관계를 놓칩니다. 그래프 탐색은 관계를 정확히 찾지만 질의 표현에 민감합니다. 두 신호를 합칩니다.

```text
score = α·cosine + β·bm25 + γ·graph + δ·freshness + ε·trust
```

- 후보 생성: pgvector top-k + 라벨/별칭 BM25
- 그래프 확장: 후보 주변 1~2 hop
- 추론: OWL 2 RL 물질화 결과와 도메인 규칙 적용
- 재정렬: Cross-encoder 또는 LLM reranker, 상위 50 → 10
- 컨텍스트 패킹: 압축 트리플 + 라벨 + citation

### ADR-004. 온톨로지 버전을 에이전트에 고정한다

온톨로지가 바뀌면 같은 질문의 답이 달라질 수 있습니다. `Agent`는 특정 `ontology_version_id`를 바인딩하고, 질의는 해당 버전의 named graph만 봅니다. 새 버전은 별도 그래프에 적재한 뒤 원자적으로 publish합니다.

### ADR-005. 읽기와 쓰기를 분리하고 SPARQL을 제한한다

- 읽기 도구: `SELECT`, `ASK`만 허용. `SERVICE`, `LOAD`, `INSERT`, `DELETE`, `CLEAR`, `DROP` 차단.
- tenant가 접근 가능한 named graph를 `FROM`에 자동 주입.
- 타임아웃 3초, 최대 1,000행, 쿼리 비용 휴리스틱 적용.
- LLM이 생성한 SPARQL은 스키마 검증 후 읽기 전용으로 실행하고, 실패 시 2회까지 복구를 시도.

### ADR-006. 멀티테넌시는 named graph + RLS로 처리한다

트리플은 tenant별 named graph로, 메타데이터는 PostgreSQL RLS로 격리합니다. Neo4j 투영은 모든 노드/관계에 `tenant`와 `ontology_version`을 붙이고, 도구는 항상 두 값을 필터로 주입합니다. 테넌트별 전용 스토어는 v1에서 도입하지 않습니다. 격리 요구가 강한 고객은 별도 배포로 대응합니다.

## 4. 컴포넌트 책임

| 컴포넌트         | 책임                                         | 현재 저장소                          |
| ---------------- | -------------------------------------------- | ------------------------------------ |
| Control Plane    | 인증, 테넌트, Agent/Ontology CRUD, 적재 요청 | `src/app/user`, `src/app/agents`     |
| Identity         | 세션, OIDC, Principal, RBAC                  | `src/app/user` (확장 예정)           |
| Agent Runtime    | workflow 컴파일, supervisor 실행, 도구 호출  | `src/app/agents/graph`, `supervisor` |
| Tool Registry    | 도구 카탈로그, BM25 검색, describe           | `src/app/agents/supervisor/tools`    |
| Ontology Service | 스키마, SPARQL, SHACL, 추론                  | 미구현 (신규)                        |
| Graph Projection | GraphDB → Neo4j 동기화, 재생성, drift 검증   | 미구현 (신규)                        |
| Knowledge Search | 문서/엔티티 임베딩, 벡터 검색, 리랭킹        | `src/app/engine/search`              |
| Ingestion        | 파일/DB/문서 적재, 임베딩, 버전 publish      | 미구현 (신규)                        |
| Gatekeeper       | 실행 격리, syscall 관찰, 리소스 제한         | `src/app/security/gatekeeper`        |

## 5. 데이터 모델

### 5.1 PostgreSQL

```text
tenant
  uuid, name, slug, status, created_at

user
  uuid, tenant_id, email, name, role, created_at

tenant_membership
  uuid, tenant_id, user_id, role(owner|admin|editor|viewer), created_at

user_identity
  id, user_id, provider(local|oidc), subject, email, email_verified, created_at

session
  id, user_id, tenant_id, auth_method(session|oidc),
  expires_at, revoked_at, ip, user_agent

oidc_provider
  uuid, tenant_id, issuer, client_id, secret_ref, scopes,
  group_role_map jsonb, enabled

outbox
  id, aggregate, event_type, payload jsonb, created_at, processed_at

projection_state
  id, ontology_version_id, target(neo4j), seq, status,
  last_event_at, checksum

ontology
  uuid, tenant_id, name, slug, namespace, current_version_id

ontology_version
  uuid, ontology_id, version, graph_prefix, checksum,
  status(draft|published|deprecated), created_by, created_at

ontology_source
  uuid, version_id, kind(file|url|inline), uri, content_hash

data_source
  uuid, tenant_id, kind(relational|document|rdf), config jsonb, secret_ref

ingestion_run
  uuid, data_source_id, ontology_version_id, status,
  stats jsonb, started_at, finished_at

agent
  uuid, tenant_id, owner_uuid, name, slug, type, description,
  workflow jsonb, ontology_version_id, etag, created_at, updated_at

agent_tool
  uuid, agent_id, tool_ref, config jsonb, enabled

run
  uuid, agent_id, user_uuid, status, input jsonb, output jsonb,
  token_usage jsonb, started_at, finished_at

run_step
  uuid, run_id, node_id, tool_name, input jsonb, output jsonb,
  latency_ms, status, error

entity_embedding
  id, tenant_id, ontology_version_id, iri, label, text,
  embedding vector, metadata jsonb

document_chunk
  id, tenant_id, document_id, chunk_no, text, embedding vector, metadata jsonb

audit_log
  id, tenant_id, actor, action, resource, payload jsonb, created_at
```

### 5.2 RDF named graph 규약

```text
urn:pypo:{tenant}:{ontology}:{version}:schema     # OWL/T-Box
urn:pypo:{tenant}:{ontology}:{version}:data       # A-Box
urn:pypo:{tenant}:{ontology}:{version}:inferred   # 추론 결과
urn:pypo:{tenant}:{ontology}:{version}:meta       # 적재 이력, checksum
```

- `schema`, `data`는 publish 후 불변입니다.
- `inferred`는 언제든 재생성 가능해야 합니다.
- 엔티티 IRI는 원천 키에서 안정적으로 만들어야 하며, 키가 바뀌면 별도 매핑 테이블에 남깁니다.
- 기본 IRI 네임스페이스는 `https://data.pypo.dev/{tenant}/{ontology}/`를 사용하고 설정으로 교체 가능하게 합니다.

### 5.3 Neo4j 투영 규약

```text
(:Entity {
  iri, ontology_version, tenant,
  labels, label, label_lang, ...literal properties,
  inferred, source_graph
})
-[:REL {
  predicate, tenant, ontology_version, inferred, rule_id, source_graph
}]->
(:Entity)
```

- 노드 키는 `(tenant, ontology_version, iri)`입니다. IRI만 키로 쓰면 v2를 투영할 때 v1 노드를 덮어쓰고, 테넌트가 공유하는 외부 IRI도 서로 침범합니다.
- `MERGE`로 멱등 upsert합니다. 재적재 전에 `source_graph`(또는 버전 전체) 단위로 지웁니다.
- SPARQL은 `ORDER BY ?s ?p ?o` + `OFFSET` 페이지네이션으로 전량을 읽습니다. `max_triples`를 넘으면 조용히 자르지 않고 실패합니다.
- blank node는 안정적인 IRI 키가 없어 건너뛰고, 건너뛴 노드·유실된 관계 수를 결과에 보고합니다.
- `rdf:type`이 없는 IRI도 stub 노드로 만듭니다. 그래야 외부 IRI로 향하는 관계가 `MATCH` 실패로 사라지지 않습니다.
- `rdf:type`은 노드 라벨과 `labels` 속성에 함께 기록합니다.
- literal은 노드 속성으로 평탄화하고, object property는 관계로 투영합니다. Neo4j는 맵을 속성값으로 저장할 수 없기 때문에 `properties` 같은 중첩 맵은 두지 않습니다. 숫자·불리언은 Neo4j 기본 타입으로 저장하고, 여러 값은 리스트로 두되 타입이 섞이면 문자열로 통일합니다.
- 추론 트리플은 `inferred: true`, `rule_id`를 남깁니다.
- 모든 노드/관계에 `tenant`, `ontology_version`을 붙여 버전별 질의와 재생성을 가능하게 합니다.
- 에이전트 도구는 read-only Neo4j 계정과 사전 정의된 Cypher 템플릿만 사용합니다.

## 6. MCP 도구 계약

### `ontology.schema`

```json
// input
{ "ontology_version_id": "uuid", "detail": "summary|full", "token_budget": 4000 }
// output
{
  "classes": [{ "iri": "...", "label": "제품", "comment": "...", "properties": ["..."] }],
  "properties": [{ "iri": "...", "domain": "...", "range": "...", "kind": "object|datatype" }],
  "truncated": false
}
```

### `ontology.search`

```json
// input
{ "query": "공급사 리스크", "type": "urn:...", "limit": 10, "mode": "hybrid" }
// output
{
  "results": [
    { "iri": "...", "label": "...", "type": "...", "score": 0.82,
      "matched_by": ["vector", "label"], "graph": "urn:pypo:..." }
  ]
}
```

### `ontology.entity`

```json
// input
{ "iri": "...", "hops": 1, "predicates": ["..."], "limit": 50 }
// output
{ "iri": "...", "properties": {...}, "neighbors": [{ "predicate": "...", "target": "...", "label": "..." }] }
```

### `ontology.query`

```json
// input
{ "sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 20", "limit": 100 }
// output
{ "variables": ["s", "p", "o"], "rows": [["...", "...", "..."]], "truncated": false }
```

### `ontology.ingest` / `ontology.materialize` / `ontology.validate`

- 모두 admin 권한과 tenant 범위를 요구합니다.
- 적재는 비동기 job으로 시작하고 `ingestion_run_id`를 반환합니다.
- `materialize`는 대상 graph와 규칙 집합을 명시합니다.

### `knowledge.search`

```json
// input
{ "query": "...", "limit": 10, "filters": { "document_type": "policy" } }
// output
{ "results": [{ "chunk_id": "...", "text": "...", "score": 0.91, "source": {...} }] }
```

### `graph.neighbors` / `graph.path` / `graph.analytics`

```json
// graph.neighbors input
{ "iri": "...", "hops": 2, "predicates": ["..."], "limit": 100 }
// graph.neighbors output
{ "nodes": [{ "iri": "...", "labels": ["..."], "properties": {...} }],
  "edges": [{ "from": "...", "to": "...", "predicate": "...", "inferred": false }] }

// graph.path input
{ "from": "...", "to": "...", "max_hops": 4, "predicates": ["..."] }
// graph.path output
{ "paths": [{ "nodes": ["..."], "edges": [{ "predicate": "..." }], "length": 3 }] }

// graph.analytics input
{ "algorithm": "degree|pagerank|community|similarity",
  "ontology_version_id": "uuid", "limit": 20 }
```

`graph.*` 도구는 Cypher를 직접 노출하지 않습니다. 서버에 등록된 템플릿과 파라미터만 받고, read-only 계정과 GDS allowlist로 실행합니다.

## 7. Agent workflow DSL

Agent의 `workflow`는 버전이 있는 JSON DSL로 정의하고, `GraphBuilder`가 LangGraph로 컴파일합니다.

```json
{
  "version": "1",
  "knowledge": {
    "ontology_version_id": "uuid",
    "default_limit": 20
  },
  "nodes": [
    { "id": "schema", "type": "tool", "tool": "ontology.schema" },
    { "id": "retrieve", "type": "tool", "tool": "ontology.search" },
    { "id": "expand", "type": "tool", "tool": "ontology.entity" },
    { "id": "plan", "type": "llm", "model": "default" },
    { "id": "delegate", "type": "subagent", "slug": "risk-analyst" },
    { "id": "answer", "type": "respond", "citations": true }
  ],
  "edges": [
    { "from": "schema", "to": "retrieve" },
    { "from": "retrieve", "to": "expand" },
    { "from": "expand", "to": "plan" },
    { "from": "plan", "to": "delegate", "condition": "needs_specialist" },
    { "from": "plan", "to": "answer", "condition": "ready" },
    { "from": "delegate", "to": "answer" }
  ]
}
```

허용 노드 타입은 `llm`, `tool`, `subagent`, `branch`, `respond`로 시작합니다. 각 노드는 `timeout`, `retry`, `max_tokens`를 가질 수 있습니다.

### Supervisor 루프

1. 의도 분류와 지식 범위 확인
2. `ontology.schema`로 질의에 필요한 클래스/프로퍼티 파악
3. 도구 카탈로그에서 BM25 + 스키마 적합도로 후보 선택
4. 도구 호출 또는 하위 에이전트 위임
5. 결과가 부족하면 질의 재작성 후 1회 재시도
6. citation과 함께 답변 합성
7. `remaining_steps`, 토큰 예산, wall-clock 예산으로 중단

## 8. 검색·추론 파이프라인

### 8.1 질의 이해

- LLM으로 엔티티 mention, 관계, 제약(시간, 유형)을 추출합니다.
- 온톨로지 스키마 요약을 프롬프트에 넣어 클래스/프로퍼티 후보로 정규화합니다.
- 확신이 낮은 mention은 `ontology.search`로 넘깁니다.

### 8.2 후보 생성

- 엔티티 임베딩: 라벨, 별칭, 설명, 이웃 요약을 합쳐 임베딩합니다.
- 문서 임베딩: 청크 단위, 메타데이터 필터 지원.
- BM25: 라벨/별칭/타입명에 강하게 가중합니다.
- 두 결과를 RRF(reciprocal rank fusion)로 합칩니다.

### 8.3 그래프 확장

- 상위 후보에서 1~2 hop까지 확장합니다.
- 확장 시 도메인/레인지 제약을 지켜 무관한 노드 폭발을 막습니다.
- hop 수와 노드 수에 예산을 둡니다.

### 8.4 질의 라우팅

| 질문 유형 | 저장소 | 도구 |
|---|---|---|
| 제약·의미론·provenance | GraphDB | `ontology.query`, `ontology.entity` |
| 탐색·경로·중심성·커뮤니티 | Neo4j | `graph.neighbors`, `graph.path`, `graph.analytics` |
| 둘 다 필요 | 양쪽 | 후보를 IRI로 병합하고 GraphDB 사실을 우선 |

- Supervisor가 도구 설명과 스키마 적합도로 라우팅합니다.
- 투영 지연이 있으면 GraphDB로 폴백하고, 답변에 `as_of`를 표시합니다.
- 엄격한 의미론이 필요한 답변은 Neo4j만으로 만들지 않습니다.

### 8.5 추론

- OWL 2 RL: GraphDB reasoner로 물질화하고 `inferred` 그래프에 기록합니다.
- 도메인 규칙: 이식성을 위해 SPARQL CONSTRUCT로 작성합니다.
- 규칙은 온톨로지 버전에 묶고, 변경 시 checksum을 갱신합니다.
- 추론 결과에는 `prov:wasDerivedFrom`으로 근거를 남깁니다.
- 추론된 트리플은 Neo4j 투영에도 `inferred: true`, `rule_id`와 함께 반영합니다.

### 8.6 재정렬과 패킹

- 상위 50개를 cross-encoder 또는 LLM reranker로 재정렬합니다.
- 최종 10개를 고릅니다.
- 컨텍스트는 트리플 단위로 압축하고, 각 사실에 IRI와 출처를 붙입니다.
- 토큰 예산을 넘으면 그래프 중심성이 낮은 사실부터 버립니다.

### 8.7 검색 서브그래프 (`src/app/engine/search`)

지식 검색은 `create_search_subgraph()`가 컴파일하는 독립 LangGraph 서브그래프로 실행합니다.

```text
START
  └─ full_context_extractor      질문 → Lucene 질의 (또는 입력 질의 그대로 사용)
       └─ full_context_retriever  Neo4j full-text index 조회 (user_uuid 범위)
            └─ chunk_context_retriever  중복 제거·정규화, 결과 없음/실패 시 END
                 └─ search_insight      메시지 + structured_response 생성 → END
```

- 입력 계약은 `SearchInput`입니다. `user_question`이 있으면 그대로 질의로 쓰고, 없으면 `messages`의 마지막 human 메시지를 LLM으로 재작성합니다.
- `user_uuid`는 필수 검색 범위입니다. 인덱스는 `Link|Memo|File`의 `title/tags/description`을 CJK analyzer로 색인하며, 이름과 필드 목록은 `queries.py`와 `scripts/neo4j/init.cypher`가 공유합니다.
- 노드는 `Command`로 라우팅합니다. 검색 실패나 0건은 `chunk_context_retriever`에서 바로 `END`로 단락됩니다.
- 출력은 `search_results`(정규화된 문서 목록)와 `structured_response`입니다. 각 결과에는 `node_id`, `title`, `url`, `description`, `score`, `tags`, `created_at`이 포함됩니다.
- 모델은 `config["configurable"]["search_model"]` 또는 `SEARCH_MODEL`로 선택합니다. `provider` 또는 `provider:model` 형식을 받으며, provider 패키지(예: `langchain-openai`)가 설치되어 있어야 합니다.

#### 개인 지식 그래프 (`Link`, `Memo`, `File`)

검색 대상 노드는 `src/app/engine/search/items.py`의 모델과 `src/app/engine/search/graph.py`의 `KnowledgeGraph`가 함께 관리합니다.

```text
(:User {uuid})
  ├─[:OWNS]→ (:Link)   {uuid, user_uuid, title, url, description, tags, created_at, updated_at}
  ├─[:OWNS]→ (:Memo)   {uuid, user_uuid, title, content, description, tags, created_at, updated_at}
  └─[:OWNS]→ (:File)   {uuid, user_uuid, title, url, mime_type, size_bytes, description, tags, ...}

(:Memo)-[:ATTACHED_TO]→(:Link|:File)
(:Link)-[:REFERENCES]→(:File)
(:Link|:Memo|:File)-[:TAGGED]→(:Tag {user_uuid, name})
```

- `created_at`/`updated_at`은 epoch milliseconds입니다. 검색 결과 포매터가 `/1000` 후 KST로 변환합니다.
- `KnowledgeGraph.upsert()`는 라벨별 노드를 `MERGE`하고, 소유자 엣지와 태그 엣지를 함께 갱신합니다. 재-upsert 시 `created_at`은 보존하고 `updated_at`만 서버 시각으로 덮어씁니다.
- 다른 사용자의 `uuid`를 재사용하려 하면 `PermissionError`로 거부합니다. 조회·삭제·관계 생성도 모두 `user_uuid`로 범위를 제한합니다.
- 제약조건과 인덱스는 `scripts/neo4j/init.cypher`에 있습니다. 데모 데이터는 `make neo4j-init && make seed-search`로 넣을 수 있습니다.

## 9. 적재 파이프라인

### 파일 (Turtle / OWL / JSON-LD)

```text
upload → parse(rdflib) → SHACL validate → stage graph
       → embed labels/descriptions → materialize → publish version
       → outbox → Neo4j projection
```

### 관계형 데이터

- v1: R2RML 매핑으로 RDF를 생성해 적재합니다.
- v2: Stardog virtual graph 또는 CDC 기반 증분 적재를 검토합니다.
- 민감 컬럼은 매핑 단계에서 제외하고, 접근 권한을 별도로 둡니다.

### 문서

```text
extract(PDF/HTML) → chunk → embed → entity linking
                  → candidate triples → review queue → load
```

LLM이 만든 트리플은 바로 신뢰하지 않습니다. `confidence`와 `source_span`을 붙이고, 임계값 이하는 검토 큐로 보냅니다.

### 공통 원칙

- 모든 job은 `content_hash`로 멱등하게 만듭니다.
- 적재는 draft graph에서 끝나고, publish는 포인터 교체로 처리합니다.
- publish 후 outbox 이벤트로 Neo4j 투영을 갱신하고, 투영 완료를 `projection_state`에 기록합니다.
- 실패 job은 dead-letter 큐로 보내고 `ingestion_run`에 이유를 남깁니다.

## 10. 보안

- **SPARQL guard**: 허용 문법 제한, graph allowlist, timeout, row limit, 비용 추정.
- **Cypher guard**: read-only 계정, 사전 정의 템플릿, 파라미터 바인딩, `LIMIT`/timeout, GDS 프로시저 allowlist. LLM이 만든 Cypher는 실행하지 않습니다.
- **테넌트 격리**: named graph allowlist + PostgreSQL RLS + Neo4j tenant/version 필터 + 테스트로 검증.
- **도구 권한**: read / admin 스코프를 분리하고 MCP 호출마다 tenant와 agent를 확인합니다.
- **세션 보안**: HttpOnly/Secure/SameSite 쿠키, CSRF 토큰, 로그인 시 세션 회전, Argon2id, Redis TTL.
- **OIDC 보안**: authorization code + PKCE, `state`/`nonce` 검증, issuer·audience·tenant 바인딩, JIT 프로비저닝 시 이메일 검증.
- **MCP 인증**: OAuth 2.1 리소스 서버로 동작하고 토큰 audience와 tenant를 확인합니다.
- **실행 격리**: gatekeeper로 tool 코드 실행을 감시하고, 네트워크 egress allowlist와 리소스 제한을 적용합니다.
- **비밀 관리**: 자격 증명은 secret manager 참조만 저장하고 온톨로지/프롬프트에 넣지 않습니다.
- **감사**: 로그인, 토큰 발급, admin 작업, 적재, 대량 질의는 `audit_log`에 남깁니다.
- **프롬프트 인젝션**: 검색된 문서와 온톨로지 라벨을 신뢰 경계 밖 데이터로 취급하고, 도구 호출 권한을 별도로 검사합니다.

## 11. 관측과 평가

### Trace

API 요청 → supervisor → tool call → SPARQL/Cypher → GraphDB/Neo4j까지 하나의 trace로 묶습니다. `run_step`에 노드별 입출력, 지연, 오류를 남깁니다.

### 지표

- 검색: Recall@k, MRR, nDCG
- 답변: citation precision, groundedness, hallucination rate
- 시스템: p50/p95 지연, 도구 오류율, 쿼리 시간, 캐시 적중률
- 비용: 요청당 토큰, 임베딩 비용, 스토어 부하

### 골든셋

도메인별 질문 50~100개를 만들고, 정답 엔티티/관계/출처를 라벨링합니다. 검색이나 프롬프트를 바꾸면 이 셋으로 회귀를 확인합니다. CI에는 느린 평가를 분리하고, PR에는 소규모 스모크 셋만 돌립니다.

## 12. 로드맵 상세

### Phase 0. Foundation (1~2주)

- `docker compose`로 PostgreSQL+pgvector, Redis, Oxigraph, Neo4j 기동
- 설정 로딩, `/health`, 구조화 로깅
- CI: ruff, pytest, 타입 체크
- `OntologyStore` 포트와 Oxigraph 어댑터, `GraphProjection` 포트
- 작은 Turtle fixture로 load/query 왕복 테스트

**Exit**: CI green, 로컬에서 GraphDB 대체 스토어와 Neo4j 투영 왕복 성공.

### Phase 1. Ontology core + Identity (3~4주)

- 온톨로지 업로드, 파싱, SHACL 검증, 버전 생성
- `ontology.schema`, `ontology.search`(라벨/BM25), `ontology.query`
- FastMCP 기반 온톨로지 MCP 서버
- 자체 세션 인증: 가입/로그인, 세션 쿠키, CSRF, Redis 세션
- OIDC: authorization code + PKCE, tenant별 IdP, JIT 프로비저닝
- `Principal`, `tenant_membership`, `user_identity` 모델과 RBAC

**Exit**: 외부 MCP 클라이언트에서 샘플 온톨로지 질의, 세션/OIDC 로그인 모두 성공.

### Phase 2. Agent loop (3~4주)

- Agent CRUD, workflow DSL 스키마, `GraphBuilder`
- Supervisor, tool registry, 하위 에이전트 위임
- citation 포함 응답 포맷
- E2E 데모 1개

**Exit**: 질문 → 도구 호출 → 근거 있는 답변.

### Phase 3. Hybrid retrieval & reasoning (4주)

- 엔티티/문서 임베딩 파이프라인
- 벡터 + BM25 + 그래프 확장 + rerank
- OWL 2 RL 물질화, 도메인 규칙
- outbox + Celery 기반 Neo4j 투영, reconciliation
- `graph.*` 도구와 질의 라우팅
- 골든셋과 평가 하네스

**Exit**: 골든셋에서 목표 recall/groundedness 달성, 투영 drift 0.

### Phase 4. Ingestion at scale (4주)

- R2RML 매핑, 문서 추출 파이프라인
- Celery job, 재시도, dead-letter, 증분 적재
- 대용량 publish 전략

**Exit**: 100만 트리플 / 1만 문서 처리.

### Phase 5. Platform (4주)

- 멀티테넌시, 쿼터, RBAC 고도화
- 감사 로그, OpenTelemetry, 대시보드
- admin API와 운영 도구

**Exit**: 테넌트 2개 이상 완전 격리, 부하 테스트 통과.

### Phase 6. Ecosystem

- 온톨로지 템플릿과 마켓플레이스
- 외부 MCP 클라이언트용 SDK/문서
- 파트너 온톨로지 연합(federation) 검토

## 13. 주요 리스크와 완화

| 리스크                 | 영향             | 완화                                                        |
| ---------------------- | ---------------- | ----------------------------------------------------------- |
| 온톨로지 모델링 병목   | 도입 지연        | 템플릿, 스키마 어시스턴트, SHACL 피드백                     |
| 추론 성능              | 질의 지연        | 물질화, 증분 추론, 버전별 캐시                              |
| LLM 생성 SPARQL 신뢰도 | 오답/장애        | 도구 우선, 템플릿, 검증·복구 루프                           |
| 투영 지연·drift        | 오래된 탐색 결과 | outbox seq, `as_of` 표시, reconciliation, GraphDB 폴백      |
| Neo4j 운영 부담        | 장애 범위 확대   | 언제든 재생성, read-only 계정, health check                 |
| 인증 복잡도            | 계정 중복/권한 불일치 | 단일 Principal, 검증된 이메일 연결, RBAC 통합 테스트   |
| 스토어 종속            | 교체 비용        | 어댑터 + conformance test suite                             |
| 데이터 품질            | 신뢰 하락        | SHACL gate, provenance, 검토 큐                             |
| 범위 팽창              | 출시 지연        | phase exit criteria 고정                                    |

## 14. 열린 결정

- **확정**: GraphDB를 온톨로지 원장으로, Neo4j를 읽기 투영으로 사용한다.
- **확정**: OWL 2 RL로 시작한다. OWL DL/HermiT가 필요한 도메인은 Phase 3 이후 별도 검증한다.
- **확정**: 자체 세션과 OIDC를 모두 제공하고, 단일 `Principal`로 권한을 판단한다.
- Neo4j 투영 범위: 전체 그래프 vs 분석용 subgraph
- 임베딩 모델: hosted API vs 로컬 torch 모델
- 테넌시: 공유 스토어 + named graph로 충분한가, 규제 고객은 전용 배포인가
- 문서 추출: 외부 파서 vs 자체 파이프라인
- 외부 MCP 노출 범위와 과금 모델
- UI 범위: API-first 유지 vs 온톨로지 편집기 우선
