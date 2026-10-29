# pypo

**Ontology-driven Agent Platform**

도메인 지식을 온톨로지로 모델링하고, 그 지식 위에서 에이전트가 검색·추론·실행하도록 만드는 플랫폼입니다.

> **Status**: 초기 스캐폴딩 단계입니다. 아래 아키텍처는 목표 구조이고, 현재 저장소에는 User/Agent 모델과 LangGraph·MCP·검색 노드의 뼈대가 들어 있습니다.

## 왜 온톨로지 + 에이전트인가

LLM 단독으로는 "우리 도메인에서 A와 B가 어떤 관계인가"에 안정적으로 답하기 어렵습니다. pypo는 이 간극을 온톨로지로 메웁니다.

- **관계 추론**: 명시된 사실뿐 아니라 규칙으로 유도되는 사실까지 답에 사용합니다.
- **근거 있는 답변**: 모든 답변에 엔티티 IRI, 그래프 경로, 출처를 함께 반환합니다.
- **지식 자산화**: 대화 로그가 아니라 버전 관리되는 온톨로지로 지식이 축적됩니다.
- **에이전트 재사용**: 같은 지식 계층을 여러 에이전트와 외부 MCP 클라이언트가 공유합니다.

핵심 설계는 **온톨로지를 에이전트 내부에 숨기지 않고 MCP 서버로 노출**하는 것입니다. 에이전트는 SPARQL을 직접 작성하지 않고, 스키마 조회·엔티티 검색·그래프 탐색·추론 도구를 통해 지식에 접근합니다.

## 아키텍처

```text
Client / External MCP Client
             │
             ▼
┌─────────────────────────────────┐
│ Control Plane (FastAPI)         │
│ agents · ontologies · ingest    │
│ auth · tenant · observability   │
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ Agent Runtime (LangGraph)       │
│ Supervisor → Sub-agents         │
│ Tool Registry (BM25)            │
└───────┬─────────────────┬───────┘
        │ MCP             │ MCP
┌───────▼─────────┐  ┌────▼────────────────┐
│ Ontology        │  │ Knowledge Search    │
│ MCP Server      │  │ pgvector + rerank   │
└───────┬─────────┘  └────┬────────────────┘
        │                 │
┌───────▼─────────┐  ┌────▼────────────────┐
│ GraphDB         │  │ PostgreSQL          │
│ RDF · OWL 2 RL  │  │ + pgvector          │
└───────┬─────────┘  └─────────────────────┘
        │ projection (outbox + Celery)
┌───────▼─────────┐
│ Neo4j           │
│ Cypher · GDS    │
└─────────────────┘
```

**GraphDB가 온톨로지의 원장**이고, **Neo4j는 탐색·분석·시각화를 위한 읽기 투영**입니다. 쓰기는 GraphDB로만 들어가고, 변경 이벤트가 Neo4j로 비동기 반영됩니다.

## 네 개의 계층

### Ontology layer

- OWL/RDF 스키마와 인스턴스 데이터를 **버전이 있는 named graph**로 관리합니다.
- SHACL로 데이터 품질을 검증하고, OWL 2 RL 규칙으로 유도 사실을 물질화합니다.
- SPARQL 1.1 엔드포인트를 제공하되, 외부에는 **제한된 MCP 도구**로만 노출합니다.
- 온톨로지 버전을 에이전트에 고정할 수 있어, 지식이 바뀌어도 답변 재현성이 유지됩니다.

### Graph projection layer

- GraphDB의 RDF를 Neo4j property graph로 투영합니다.
- Cypher 기반 다중 hop 탐색, GDS 중심성·커뮤니티·유사도, Bloom 시각화를 담당합니다.
- 추론된 트리플도 `inferred` 표시와 함께 투영합니다.
- 원장이 아니므로 언제든 재생성할 수 있어야 합니다.

### Agent layer

- **Agent**는 workflow, 지식 범위(ontology version), 도구 목록을 묶은 실행 단위입니다.
- **Supervisor**가 요청을 분해하고 하위 에이전트나 MCP 도구로 위임합니다.
- 도구 탐색은 BM25로, 지식 검색은 pgvector 후보 생성 + 그래프 확장으로 처리합니다.
- 의미론 질의는 GraphDB(SPARQL), 탐색·분석은 Neo4j(Cypher)로 라우팅합니다.
- 모든 실행은 trace로 남기고, 답변에는 그래프 경로와 출처를 붙입니다.

### Identity layer

- 자체 세션과 OIDC를 **하나의 `Principal`로 수렴**시킵니다.
- 웹은 HttpOnly 세션 쿠키, API/MCP는 Bearer 토큰을 사용합니다.
- OIDC는 authorization code + PKCE, tenant별 IdP, JIT 프로비저닝, 그룹→역할 매핑을 지원합니다.
- 계정 연결은 검증된 이메일을 기준으로 하며, `user_identity`에 provider/subject를 분리 저장합니다.

## MCP 도구 표면 (계획)

| 도구                   | 역할                                                | 노출  |
| ---------------------- | --------------------------------------------------- | ----- |
| `ontology.list`        | 접근 가능한 온톨로지와 버전 목록                    | read  |
| `ontology.schema`      | 클래스·프로퍼티·라벨 요약 (토큰 예산 적용)          | read  |
| `ontology.search`      | 라벨/별칭/임베딩 기반 엔티티 검색                   | read  |
| `ontology.entity`      | IRI 기준 엔티티와 주변 그래프 조회                  | read  |
| `ontology.query`       | 읽기 전용 SPARQL SELECT/ASK, tenant graph 자동 주입 | read  |
| `ontology.validate`    | SHACL 검증 리포트                                   | admin |
| `ontology.ingest`      | Turtle/JSON-LD 적재, 비동기 job                     | admin |
| `ontology.materialize` | 추론 규칙 실행 및 유도 그래프 생성                  | admin |
| `knowledge.search`     | 문서 청크 벡터 검색                                 | read  |
| `graph.neighbors`      | Cypher 기반 다중 hop 이웃 탐색                      | read  |
| `graph.path`           | 두 엔티티 사이 경로 탐색                            | read  |
| `graph.analytics`      | GDS 중심성·커뮤니티·유사도 (사전 정의된 알고리즘)  | read  |

## 하이브리드 검색 (계획)

```text
질문
  → 1. 질의 이해 (엔티티/관계 후보 추출)
  → 2. 후보 생성 (pgvector + BM25)
  → 3. 그래프 확장 (GraphDB SPARQL + Neo4j Cypher)
  → 4. 추론 (OWL 2 RL / 도메인 규칙)
  → 5. 재정렬 (유사도 + 그래프 중심성 + 출처 신뢰도)
  → 6. 컨텍스트 패킹 (서브그래프 + citation)
  → LLM 답변
```

벡터 검색만으로는 "관계"를 놓치고, 그래프 탐색만으로는 표현이 다른 질문을 놓칩니다. 두 신호를 합치는 것이 pypo의 핵심 차별점입니다.

## 기술 스택

| 영역          | 현재                                      | 도입 예정                                                       |
| ------------- | ----------------------------------------- | --------------------------------------------------------------- |
| API           | FastAPI, Pydantic v2                      | OpenAPI 기반 SDK                                                |
| Orchestration | LangGraph, LangChain                      | workflow DSL, 실행 trace                                        |
| Tool protocol | MCP, FastMCP                              | 온톨로지 MCP 서버                                               |
| Ontology      | —                                         | GraphDB (원장), Oxigraph (dev/CI), `rdflib`, `pyshacl`          |
| Graph         | —                                         | Neo4j (읽기 투영), GDS, Bloom                                   |
| 인증          | —                                         | 자체 세션 + OIDC, RBAC, tenant membership                       |
| 저장소        | PostgreSQL, pgvector, SQLAlchemy, Alembic | S3/MinIO, named graph 규약, outbox                              |
| 비동기        | Redis, Celery                             | 적재·임베딩·추론·Neo4j 투영 job                                 |
| 모델          | PyTorch                                   | 임베딩/리랭커 교체 가능한 어댑터                                |
| 관측          | —                                         | OpenTelemetry, run trace, audit log                             |

트리플 스토어는 교체 가능하게 설계합니다. 개발/CI는 Oxigraph, 운영 원장은 GraphDB를 사용합니다. Neo4j는 원장이 아니라 투영이므로 언제든 GraphDB에서 재생성합니다. 관계형 데이터 가상화가 필요해지면 Stardog을 별도로 검토합니다.

## 저장소 구조

```text
src/app/
├── agents/            # Agent 모델, GraphBuilder, Supervisor, MCP 연동
│   ├── graph/         # workflow → LangGraph 컴파일
│   ├── mcp/           # MCP 서버 스펙과 클라이언트
│   └── supervisor/    # 상위 오케스트레이션, 도구 탐색
├── engine/
│   └── search/        # 지식 검색 노드 (pgvector + graph)
├── security/
│   └── gatekeeper/    # 실행 격리, syscall 관찰
├── shared/            # DB, registry, 공통 타입
└── user/              # 사용자와 소유권
```

## 현재 실행

```bash
uv sync
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
uv run alembic upgrade head
uv run python main.py
```

- OpenAPI UI: <http://localhost:8000/docs>
- OpenAPI YAML: <http://localhost:8000/openapi.yaml>

검사와 테스트:

```bash
uv run pytest
uv run ruff check .
```

- 마이그레이션은 `migrations/`에 있고, 모델을 바꾼 뒤 `uv run alembic revision --autogenerate -m "..."`로 추가합니다.
- CI는 lint → pytest → `alembic upgrade head` → `alembic check` 순서로 돌아 모델과 스키마의 드리프트를 잡습니다.
- 온톨로지 MCP 서버, Supervisor 루프, 벡터 스토어 백엔드는 아직 구현 전입니다.


## B2C 위성 제품 (실험)

B2B 온톨로지 플랫폼은 그대로 유지하고, 첫 B2C 제품으로 **직무 생존 지도**를 검증합니다. 사용자가 직무를 입력하면 과업별 AI 노출도, 인접 직무, 부족 스킬과 학습 경로를 그래프와 출처로 보여주는 서비스입니다.

- 제품 브리프: [docs/B2C_CAREER_GRAPH.md](docs/B2C_CAREER_GRAPH.md)
- 원칙: 온톨로지는 뒤에 숨기고, 사용자에게는 지도·경로·근거만 보여줍니다.
- 검증: 6주 안에 리포트 완료율·공유율·지불 의향으로 Go/No-Go를 판단합니다.

## 로드맵

| 단계                      | 목표                                                   | 완료 기준                                            |
| ------------------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| **0. Foundation**         | 로컬 인프라, 설정, CI, 테스트 하네스, store 포트       | `docker compose up`으로 Postgres/Redis/Oxigraph/Neo4j 기동 |
| **1. Ontology core**      | 온톨로지 적재·검증·버전 관리, schema/search/query 도구, 세션·OIDC 인증 | 외부 MCP 클라이언트에서 샘플 온톨로지 질의, 세션/OIDC 로그인 성공 |
| **2. Agent loop**         | Agent CRUD, workflow DSL, GraphBuilder, Supervisor     | 질문 → 근거 있는 답변 E2E 1개                        |
| **3. Hybrid retrieval**   | pgvector 임베딩, 그래프 확장, 재정렬, OWL 2 RL, Neo4j 투영 | 골든셋에서 recall/groundedness 목표 달성             |
| **4. Ingestion at scale** | 관계형 매핑, 문서 파이프라인, 증분 적재                | 100만 트리플 / 1만 문서 처리                         |
| **5. Platform**           | 멀티테넌시, 쿼터, 감사, 관측, RBAC 고도화              | 테넌트 2개 이상 완전 격리                            |
| **6. Ecosystem**          | 온톨로지 템플릿, 마켓플레이스, SDK                     | 외부 에이전트가 MCP로 지식 계층 사용                 |

## 설계 원칙

1. **지식과 실행을 분리한다.** 온톨로지는 MCP 서버, 에이전트는 그 소비자입니다.
2. **원장과 투영을 분리한다.** GraphDB가 유일한 원장이고 Neo4j는 재생성 가능한 읽기 모델입니다.
3. **스토어를 추상화한다.** 특정 트리플 스토어나 그래프 DB의 API에 도메인 로직을 묶지 않습니다.
4. **읽기와 쓰기를 나눈다.** 질의 도구는 읽기 전용이고, 적재·추론은 admin 경로로 분리합니다.
5. **인증은 하나의 Principal로 수렴한다.** 세션과 OIDC가 같은 권한 모델을 사용합니다.
6. **버전과 출처를 남긴다.** 온톨로지 버전, 실행 trace, citation 없는 답변은 실패로 봅니다.
7. **평가를 먼저 만든다.** 골든 질문셋과 지표 없이 검색·프롬프트를 바꾸지 않습니다.
8. **처음부터 멀티테넌트를 전제한다.** tenant는 데이터 모델과 named graph 규약에 처음부터 들어갑니다.

## 문서

- [Architecture](docs/ARCHITECTURE.md): 계층, 데이터 모델, MCP 계약, 검색·추론, 보안, 로드맵 상세
