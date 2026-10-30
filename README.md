# pypo

**이 저장소에서 일하는 AI 동료.**

사람이 GitHub Issue로 계획을 쓰면, pypo는 매일 작은 작업을 골라 구현하고 PR을 올립니다. 리뷰를 받으면 고치고, 배운 것을 기억해 다음 작업에 씁니다. 처음에는 실력이 부족해도 됩니다. 대신 일할수록 나아지고, AI API 비용은 0원으로 시작합니다.

pypo는 같은 이름의 플랫폼, 즉 **온톨로지 기반 에이전트 엔진** 위에서 돌아갑니다. pypo 자신이 그 엔진의 첫 번째 사용자입니다.

> **Status**: 설계와 준비 단계입니다. M0(규칙, 페르소나, 이슈 양식, 라벨)와 M1(로컬 미리 보기, 이슈 #1·#2 첫 시도 통과)을 마쳤고, 다음은 M2(실제 PR 생성)입니다. 상세 설계는 [docs/DEVBOT.md](docs/DEVBOT.md)에 있습니다.

## pypo에게 일 맡기기

1. GitHub에서 **New issue → "pypo 작업"** 양식을 고릅니다.
2. 목표, 수정할 파일(1~3개), 완료 기준, 하지 않을 것을 채웁니다. 완료 기준은 테스트로 확인할 수 있게 씁니다.
3. 양식으로 만든 이슈에는 `bot-ready` 라벨이 붙습니다. 아직 준비가 안 됐으면 라벨을 떼 둡니다.
4. pypo가 이슈를 가져가 `pypo/<이슈번호>-<slug>` 브랜치에 PR을 올립니다. 리뷰와 머지는 사람이 합니다.

| 라벨           | 의미                                                    |
| -------------- | ------------------------------------------------------- |
| `bot-ready`    | pypo가 가져가도 되는 작업                               |
| `bot-question` | pypo가 질문을 남김. 답한 뒤 라벨을 지우면 다시 후보가 됨 |
| `bot-failed`   | 3회 시도 후 실패. 이슈를 쪼개거나 직접 처리             |
| `pypo`         | pypo가 만든 PR                                          |

pypo는 이슈에 적힌 내용과 파일만 보고 일합니다. 이슈가 정확할수록 결과가 좋습니다.

## pypo가 일하는 방식

```text
작업 고르기 → 구현 → 검증 → PR 생성 → 회고
   코드       LLM    코드     코드      LLM
```

- **LLM은 필요한 곳에만 씁니다.** 고르기, 검증, PR 생성은 일반 코드가 결정적으로 처리합니다.
- **테스트가 판정합니다.** ruff, pytest, typecheck를 통과하지 못하면 에러를 보고 최대 3번 다시 시도하고, 그래도 안 되면 PR 대신 이슈에 실패 기록을 남깁니다.
- **안전장치는 코드로 강제합니다.** 수정 금지 경로, 허용된 명령만 실행, main 직접 푸시 금지, 변경 400줄 상한, 리뷰 대기 PR 3개 상한.
- **기억하고 진화합니다.** 회고를 `agent/memory/`에, 반복되는 절차를 `agent/skills/`에 쌓습니다. 자기 작업 이력을 시험 문제로 삼아, 평가 점수가 오를 때만 자기 개선을 제안합니다. 안전장치와 평가 코드는 pypo가 고칠 수 없습니다.
- **모델은 설정으로 바꿉니다.** `DEVBOT_MODEL="provider:model"`. 기본은 로컬 Ollama(0원)입니다.

| 파일                                                                     | 내용                                         |
| ------------------------------------------------------------------------ | -------------------------------------------- |
| [`AGENTS.md`](AGENTS.md)                                                 | 이 저장소에서 일하는 모든 에이전트의 규칙    |
| [`agent/persona.md`](agent/persona.md)                                   | pypo의 정체성, 원칙, 말투 (사람만 수정)       |
| [`.github/ISSUE_TEMPLATE/bot-task.yml`](.github/ISSUE_TEMPLATE/bot-task.yml) | 작업 이슈 양식                               |
| `src/app/agents/devbot/`                                                 | pypo 구현                                    |

## 지금 상태

| 단계 | 내용                                        | 상태    |
| ---- | ------------------------------------------- | ------- |
| M0   | `AGENTS.md`, 페르소나, 이슈 양식, 라벨, 첫 이슈 3개 | 완료    |
| M1   | 로컬 미리 보기 (작업 흐름 + 코드 작성, Ollama) | 완료    |
| M2   | 실제 PR 생성 + 일일 요약                    |         |
| M3   | 리뷰 코멘트와 CI 실패 반영                  |         |
| M4   | 기억: 회고 작성과 다음 계획에 반영          |         |
| M5   | GitHub Actions 무인 운영                    |         |
| M6   | 재실행 평가 + 스킬 문서                     |         |
| M7   | 자기 개선 제안                              |         |

## pypo가 돌아가는 엔진

도메인 지식을 온톨로지로 모델링하고, 그 위에서 에이전트가 검색·추론·실행하는 플랫폼입니다. LLM 단독으로는 "우리 도메인에서 A와 B가 어떤 관계인가"에 안정적으로 답하기 어렵습니다. 이 간극을 온톨로지로 메우고, 모든 답에 그래프 경로와 출처를 붙입니다. 지식은 대화 로그가 아니라 버전 관리되는 온톨로지로 쌓입니다. pypo의 기억도 나중에 여기로 옮깁니다.

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

GraphDB가 온톨로지의 원장이고, Neo4j는 탐색·분석·시각화를 위한 읽기 투영입니다. 계층별 상세, MCP 도구 계약, 하이브리드 검색, 데이터 모델은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)에 있습니다.

현재 엔진은 초기 스캐폴딩 단계입니다. User/Agent 모델, LangGraph·MCP·검색 노드의 뼈대, Neo4j 투영, 카드 계산기 API가 있고, 온톨로지 MCP 서버와 Supervisor 루프는 아직 구현 전입니다.

### 설계 원칙

1. **지식과 실행을 분리한다.** 온톨로지는 MCP 서버, 에이전트는 그 소비자입니다.
2. **원장과 투영을 분리한다.** GraphDB가 유일한 원장이고 Neo4j는 재생성 가능한 읽기 모델입니다.
3. **스토어를 추상화한다.** 특정 트리플 스토어나 그래프 DB의 API에 도메인 로직을 묶지 않습니다.
4. **읽기와 쓰기를 나눈다.** 질의 도구는 읽기 전용이고, 적재·추론은 admin 경로로 분리합니다.
5. **인증은 하나의 Principal로 수렴한다.** 세션과 OIDC가 같은 권한 모델을 사용합니다.
6. **버전과 출처를 남긴다.** 온톨로지 버전, 실행 trace, citation 없는 답변은 실패로 봅니다.
7. **평가를 먼저 만든다.** 골든 질문셋과 지표 없이 검색·프롬프트를 바꾸지 않습니다.
8. **처음부터 멀티테넌트를 전제한다.** tenant는 데이터 모델과 named graph 규약에 처음부터 들어갑니다.

### 기술 스택

| 영역          | 현재                                      | 도입 예정                                              |
| ------------- | ----------------------------------------- | ------------------------------------------------------ |
| API           | FastAPI, Pydantic v2                      | OpenAPI 기반 SDK                                       |
| Orchestration | LangGraph, LangChain                      | workflow DSL, 실행 trace                               |
| Tool protocol | MCP, FastMCP                              | 온톨로지 MCP 서버                                      |
| Ontology      | —                                         | GraphDB (원장), Oxigraph (dev/CI), `rdflib`, `pyshacl` |
| Graph         | Neo4j (읽기 투영)                         | GDS, Bloom                                             |
| 인증          | —                                         | 자체 세션 + OIDC, RBAC, tenant membership              |
| 저장소        | PostgreSQL, pgvector, SQLAlchemy, Alembic | S3/MinIO, named graph 규약, outbox                     |
| 비동기        | Redis, Celery                             | 적재·임베딩·추론·Neo4j 투영 job                        |
| 모델          | PyTorch                                   | 로컬 Ollama(pypo), 임베딩/리랭커 교체 가능한 어댑터    |
| 웹            | Next.js, TanStack Query, Zustand          |                                                        |
| 관측          | —                                         | OpenTelemetry, run trace, audit log                    |

### 엔진 로드맵

| 단계                      | 목표                                                                     | 완료 기준                                                         |
| ------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| **0. Foundation**         | 로컬 인프라, 설정, CI, 테스트 하네스, store 포트                         | `docker compose up`으로 Postgres/Redis/Oxigraph/Neo4j 기동        |
| **1. Ontology core**      | 온톨로지 적재·검증·버전 관리, schema/search/query 도구, 세션·OIDC 인증   | 외부 MCP 클라이언트에서 샘플 온톨로지 질의, 세션/OIDC 로그인 성공 |
| **2. Agent loop**         | Agent CRUD, workflow DSL, GraphBuilder, Supervisor                       | 질문 → 근거 있는 답변 E2E 1개                                     |
| **3. Hybrid retrieval**   | pgvector 임베딩, 그래프 확장, 재정렬, OWL 2 RL, Neo4j 투영               | 골든셋에서 recall/groundedness 목표 달성                          |
| **4. Ingestion at scale** | 관계형 매핑, 문서 파이프라인, 증분 적재                                  | 100만 트리플 / 1만 문서 처리                                      |
| **5. Platform**           | 멀티테넌시, 쿼터, 감사, 관측, RBAC 고도화                                | 테넌트 2개 이상 완전 격리                                         |
| **6. Ecosystem**          | 온톨로지 템플릿, 마켓플레이스, SDK                                       | 외부 에이전트가 MCP로 지식 계층 사용                              |

엔진 작업은 제품(B2C 앱, pypo)이 필요로 할 때만 당겨옵니다.

## 제품 전략

같은 엔진을 B2B와 B2C 두 채널로 가져갑니다. B2C 앱은 엔진을 한 층씩 증명하는 시연장이고, B2B는 같은 엔진을 조직에 파는 채널입니다. 첫 B2C인 카드 실적 배분 계산기(`src/app/card/`, `apps/web/`)는 지금 일시 중단 상태입니다. 단계별 계획과 Go/No-Go 기준은 [docs/STRATEGY.md](docs/STRATEGY.md)에 있습니다.

## 개발 환경

```bash
uv sync
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
uv run alembic upgrade head
uv run python main.py          # API: http://localhost:8000/docs
pnpm install && pnpm dev       # 웹: http://localhost:3000
```

검사:

```bash
uv run ruff check .
uv run pytest                  # DB가 필요한 통합 테스트는 환경 변수가 없으면 자동 skip
pnpm typecheck
```

- 마이그레이션은 `migrations/`에 있고, 모델을 바꾼 뒤 `uv run alembic revision --autogenerate -m "..."`로 추가합니다.
- CI는 lint → pytest → `alembic upgrade head` → `alembic check` 순서로 돌아 모델과 스키마의 드리프트를 잡습니다.

## 문서

- [DEVBOT](docs/DEVBOT.md): pypo(AI 동료) 설계, 단계, 안전장치, 기억과 진화
- [Strategy](docs/STRATEGY.md): B2B·B2C 관계, 단계별 Go/No-Go
- [Architecture](docs/ARCHITECTURE.md): 엔진 계층, 데이터 모델, MCP 계약, 검색·추론, 보안
- [PRD](docs/PRD.md): 카드 실적 배분 계산기 (일시 중단)
