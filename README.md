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

| 라벨           | 의미                                                     |
| -------------- | -------------------------------------------------------- |
| `bot-ready`    | pypo가 가져가도 되는 작업                                |
| `bot-question` | pypo가 질문을 남김. 답한 뒤 라벨을 지우면 다시 후보가 됨 |
| `bot-failed`   | 3회 시도 후 실패. 이슈를 쪼개거나 직접 처리              |
| `pypo`         | pypo가 만든 PR                                           |

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

| 파일                                                                         | 내용                                      |
| ---------------------------------------------------------------------------- | ----------------------------------------- |
| [`AGENTS.md`](AGENTS.md)                                                     | 이 저장소에서 일하는 모든 에이전트의 규칙 |
| [`agent/persona.md`](agent/persona.md)                                       | pypo의 정체성, 원칙, 말투 (사람만 수정)   |
| [`.github/ISSUE_TEMPLATE/bot-task.yml`](.github/ISSUE_TEMPLATE/bot-task.yml) | 작업 이슈 양식                            |
| `src/app/agents/devbot/`                                                     | pypo 구현                                 |

## 지금 상태

| 단계 | 내용                                                | 상태 |
| ---- | --------------------------------------------------- | ---- |
| M0   | `AGENTS.md`, 페르소나, 이슈 양식, 라벨, 첫 이슈 3개 | 완료 |
| M1   | 로컬 미리 보기 (작업 흐름 + 코드 작성, Ollama)      | 완료 |
| M2   | 실제 PR 생성 + 일일 요약                            |      |
| M3   | 리뷰 코멘트와 CI 실패 반영                          |      |
| M4   | 기억: 회고 작성과 다음 계획에 반영                  |      |
| M5   | GitHub Actions 무인 운영                            |      |
| M6   | 재실행 평가 + 스킬 문서                             |      |
| M7   | 자기 개선 제안                                      |      |

## 작은 모델로 일 잘하게 만들기

pypo는 로컬 `qwen2.5-coder:7b`(16GB Mac, 비용 0원)로 일합니다. 모델을 키우는 대신 **모델이 할 일을 코드가 가져갑니다.** 7B는 짧은 판단(어떤 동사를 쓸지)만 하고, 정확해야 하는 일은 결정적인 코드가 합니다.

### 서브 에이전트를 늘리지 않는 이유

- 16GB에는 모델을 하나만 올릴 수 있어 병렬 처리가 안 됩니다. 에이전트를 늘리면 같은 7B를 여러 번 차례로 부를 뿐이라 시간만 늘어납니다.
- 7B가 가장 약한 것이 형식과 지시 지키기인데, 에이전트끼리 메시지를 주고받는 일이 바로 그것입니다. 계획 단계를 뺀 것도 같은 이유입니다.
- 대신 **코드로 된 서브 에이전트**를 둡니다. AST 발췌, ruff 자동 수정, 정의 옮기기 같은 것들이 pypo의 도구입니다.

### 지금까지 효과가 확인된 것

| 장치                               | 무엇을 해결했나                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| AST 발췌                           | 큰 파일에서 이슈에 필요한 정의만 넣어 문맥을 12k 안에 맞춤                        |
| `ruff --fix`                       | 쓰지 않는 import, import 순서를 모델 재호출 없이 고침 (#2 첫 시도 통과)           |
| 재시도 프롬프트에 이전 출력 포함   | 처음부터 새로 짜지 않고 틀린 곳만 고치게 함                                       |
| 재시도 온도 0.6                    | 같은 오답 반복을 줄임 (첫 시도는 온도 0)                                          |
| 출력 상한 1024토큰                 | 맞는 답은 짧음. 파일 통째로 다시 쓰기에 6분씩 쓰지 않게 함                        |
| `DELETE 이름`, `MOVE 이름 TO 경로` | 7B는 큰 정의를 그대로 베끼지 못함. 이름만 받고 코드는 pypo가 지우고 옮김          |
| 습관 해석                          | "DELETE + 다른 파일에 다시 타이핑"은 MOVE로 처리. 다시 친 코드의 환각을 버림 (#3) |
| 즉시 거부 + 구체적 힌트            | 이미 있는 코드를 다시 쓰면 "MOVE 한 줄만 쓸 것"처럼 정확한 지시로 되돌림          |
| 이슈에 테스트 이름 필수            | 테스트가 없으면 아무것도 안 한 답도 통과함 (#3 첫 실행)                           |
| `RENAME 이름 TO 새이름`            | 이름 바꾸기도 이름만 받고, 그 파일과 이슈 파일에서 쓰는 곳은 pypo가 바꿈          |
| 빠진 import 자동 추가              | 정의되지 않은 이름(F821)이 `src/`에 한 곳만 있으면 pypo가 import를 넣음           |
| 에러를 한 줄 지시로                | ImportError·F811·F821·순환 import를 "X는 이 파일에 있으니 거기서 import"로 바꿈   |
| import하는 곳 보여 주기            | 수정할 파일을 import하는 줄을 프롬프트에 넣어 옮기기·이름 바꾸기의 파급을 보게 함 |

### 개선 루프

1. **측정한다.** 풀었던 이슈를 그때 커밋과 함께 `agent/evals/cases.json`에 고정하고, 하네스를 바꿀 때마다
   `uv run python -m src.app.agents.devbot eval`로 통과율·호출 수·시간을 잰다. 새 이슈는 실패하는 테스트를 먼저 넣은
   브랜치를 `--base`로 지정해 `--dry-run`으로 잰다.
2. **실패 로그를 읽는다.** 원문은 임시 폴더의 `pypo-logs/`에 남는다.
3. **실패를 규칙으로 바꾼다.** 새 동사, 습관 해석, 즉시 거부 힌트 중 하나로. 프롬프트 문구를 다듬는 것보다 효과가 크다.
4. **데이터가 쌓인다.** 통과한 작업은 `~/.pypo/trajectories.jsonl`에 남고, 약 200건이 모이면 같은 모델을 LoRA로 학습한다.

### 다음 후보

- 시그니처 바꾸기: 지금은 SEARCH/REPLACE로 하고, 호출하는 곳을 놓치는 실패가 보이면 동사로 만든다
- 메모리가 커지면 이슈와 관련된 항목만 골라 넣기 (지금은 비어 있음)
- 이슈가 풀릴 때마다 `agent/evals/cases.json`에 한 줄씩 추가
- 메모리가 허락하면 Ollama 병렬 요청(`OLLAMA_NUM_PARALLEL`)으로 2개 생성 후 통과한 쪽 고르기

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

| 단계                      | 목표                                                                   | 완료 기준                                                         |
| ------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **0. Foundation**         | 로컬 인프라, 설정, CI, 테스트 하네스, store 포트                       | `docker compose up`으로 Postgres/Redis/Oxigraph/Neo4j 기동        |
| **1. Ontology core**      | 온톨로지 적재·검증·버전 관리, schema/search/query 도구, 세션·OIDC 인증 | 외부 MCP 클라이언트에서 샘플 온톨로지 질의, 세션/OIDC 로그인 성공 |
| **2. Agent loop**         | Agent CRUD, workflow DSL, GraphBuilder, Supervisor                     | 질문 → 근거 있는 답변 E2E 1개                                     |
| **3. Hybrid retrieval**   | pgvector 임베딩, 그래프 확장, 재정렬, OWL 2 RL, Neo4j 투영             | 골든셋에서 recall/groundedness 목표 달성                          |
| **4. Ingestion at scale** | 관계형 매핑, 문서 파이프라인, 증분 적재                                | 100만 트리플 / 1만 문서 처리                                      |
| **5. Platform**           | 멀티테넌시, 쿼터, 감사, 관측, RBAC 고도화                              | 테넌트 2개 이상 완전 격리                                         |
| **6. Ecosystem**          | 온톨로지 템플릿, 마켓플레이스, SDK                                     | 외부 에이전트가 MCP로 지식 계층 사용                              |

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
