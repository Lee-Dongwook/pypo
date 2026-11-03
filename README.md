# pypo

**이 저장소에서 일하는 AI 동료, 그리고 그것이 도는 엔진.**

pypo는 온톨로지 기반 에이전트 엔진 위에서 도는 플랫폼이고, pypo(AI 동료)는 그 엔진의 첫 번째 사용자입니다.

> **지금의 우선순위는 하나입니다: hermes agent 체계 수립.** 그 위에서 pypo(AI 동료)와 플랫폼이 돌아갑니다. 상세 설계와 로드맵은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)와 [docs/DEVBOT.md](docs/DEVBOT.md)에 있습니다.

## 지금 하는 일: hermes agent

**hermes**는 pypo 엔진 위의 범용 자율 에이전트입니다. 주어진 목표를 ReAct(생각 → 행동 → 관찰) 루프로 풀고, 필요한 도구를 스스로 찾아 호출합니다. 소형 로컬 모델(Ollama, 비용 0원)에서도 동작하도록 도구 호출을 JSON 한 조각으로만 주고받습니다.

```text
Task → [agent: LLM이 tool call을 JSON으로 응답] → [tools: 레지스트리에서 실행] → 관찰을 돌려주며 반복
```

### 구성 요소

| 위치 | 내용 |
| ---- | ---- |
| `src/app/agents/react.py` | ReAct 프로토콜 공통 파서 (펜스·설명 문장이 섞여도 첫 유효 JSON을 찾는다) |
| `src/app/agents/agent_loop.py` | hermes 독립 실행 루프 (`AgentLoop`) |
| `src/app/agents/tools/registry.py` | 도구 레지스트리. 타입 힌트로 JSON Schema 생성, 오류는 한국어로 반환 |
| `src/app/agents/tools/catalog.py` | 기본 도구 카탈로그 조립 (`build_default_registry`) |
| `src/app/agents/tools/builtin_tools.py` | 기본 도구 (`run_python_test`: AST 관문 통과 코드만 실행) |
| `src/app/agents/supervisor/workflow.py` | 감독자 LangGraph (`build_supervisor_graph`): `agent` ↔ `tools` 노드 |
| `src/app/agents/supervisor/tools/search.py` | `tool_search` / `tool_describe`. BM25로 도구를 검색해 필요한 것만 프롬프트에 노출 |
| `src/app/agents/supervisor/agent_call.py` | `agent_call`. slug로 서브에이전트를 찾아 실행 (실행 엔진은 주입) |

### 모델

`settings.hermes_model` / `settings.search_model` (`"provider:model"` 형식, 기본 `ollama:qwen2.5-coder:7b`). 코드를 바꾸지 않고 모델을 교체할 수 있습니다.

### 아직 안 되는 것

- **서브에이전트 실행 엔진**: `agent_call`은 `SubAgentInvoker`를 주입받을 때만 실제로 실행합니다. workflow DSL 실행기(`GraphBuilder`)는 아직 스캐폴딩입니다.
- **온톨로지 MCP 서버, Supervisor의 전체 권한 모델**: 미구현입니다.

### 검증

```bash
uv run pytest        # hermes 관련 테스트: tests/test_react.py, test_agent_loop.py, test_tool_registry.py, ...
```

## pypo (AI 동료)

사람이 GitHub Issue로 계획을 쓰면, pypo가 작은 작업을 골라 구현하고 PR을 올립니다. LLM은 필요한 곳에만 쓰고, 검증은 코드(ruff·pytest·typecheck)가 판정합니다. 리뷰를 받으면 고치고, 배운 것을 `agent/memory/`에 기억합니다. 진행 상황: M0(규칙·양식·라벨), M1(로컬 미리 보기) 완료, M2(실제 PR 생성)부터 차례입니다. 상세는 [docs/DEVBOT.md](docs/DEVBOT.md)에 있습니다.

## 엔진 개요

pypo 플랫폼은 도메인 지식을 온톨로지로 모델링하고, 에이전트가 검색·추론·실행할 때 그래프 경로와 출처를 답에 붙입니다. GraphDB가 유일한 원장이고, Neo4j는 읽기 투영입니다. 현재 초기 스캐폴딩 단계이며, 우선순위는 위의 hermes agent입니다. 계층·데이터 모델·MCP 계약은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)에 있습니다.

## 제품 전략

같은 엔진을 B2B·B2C로 가져갑니다. 첫 B2C인 카드 실적 배분 계산기(`src/app/card/`, `apps/web/`)는 일시 중단 상태입니다. 단계별 계획과 Go/No-Go 기준은 [docs/STRATEGY.md](docs/STRATEGY.md)에 있습니다.

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

- [Architecture](docs/ARCHITECTURE.md): 엔진 계층, hermes agent, 데이터 모델, MCP 계약, 보안
- [DEVBOT](docs/DEVBOT.md): pypo(AI 동료) 설계, 안전장치, 기억과 진화
- [Strategy](docs/STRATEGY.md): B2B·B2C 관계, 단계별 Go/No-Go
- [PRD](docs/PRD.md): 카드 실적 배분 계산기 (일시 중단)
- [CHANGELOG](CHANGELOG.md): 변경 이력
