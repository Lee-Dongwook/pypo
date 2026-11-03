# Changelog

이 저장소의 주요 변경 이력입니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르고, 버전은 릴리스가 생길 때부터 붙입니다. 그 이전 이력은 `git log`를 참고하세요.

## [Unreleased]

### Added

- hermes 범용 자율 에이전트의 실행 체계 (`ef29e64`)
  - `src/app/agents/react.py`: ReAct(생각→행동→관찰) JSON 프로토콜 공통 파서. 펜스·설명이 섞인 응답에서도 첫 유효 JSON 객체를 찾는다.
  - `src/app/agents/agent_loop.py`: hermes 독립 실행 루프. `max_steps` 제한, `model`/`registry` 주입 가능.
  - `src/app/agents/supervisor/workflow.py`: 감독자 LangGraph (`build_supervisor_graph`). `agent` ↔ `tools` 두 노드, `finish` 시 `structured_response.answer` 반환, 파싱 실패 시 피드백 후 재시도.
  - `src/app/agents/supervisor/tools/search.py`: `tool_search` / `tool_describe`. BM25(`Bm25Index`)로 도구 검색, 상세는 JSON Schema로 반환. 프롬프트에는 메타 도구만 노출.
  - `src/app/agents/supervisor/agent_call.py`: slug로 서브에이전트를 찾아 실행하는 `agent_call` 도구. `SubAgentInvoker` 주입형, `tool_call_id` 발급, 조회·실행 실패를 한국어로 매핑.
  - `src/app/agents/tools/catalog.py`: 기본 도구 카탈로그 빌더.
  - `settings.hermes_model` (기본 `ollama:qwen2.5-coder:7b`).

### Changed

- `AgentLoop`이 하드코딩된 Ollama HTTP 호출 대신 기존 `resolve_chat_model("provider:model")`로 LLM을 호출한다.
- `ToolRegistry`를 재작성: 타입 힌트에서 JSON Schema(required 포함)를 생성하고, 알 수 없는 도구·잘못된 인자·실행 예외를 한국어 메시지로 반환한다. 전역 싱글턴 제거.
- README를 hermes agent 체계 중심으로 재구성하고 엔진·카드 내용은 문서 링크로 이동.

### Fixed

- `builtin_tools`가 존재하지 않던 `validate_ast`를 import하던 문제 → `ASTGatekeeper` 사용으로 수정.
- `metric_logger.py`에 클래스 밖으로 빠져 있던 `log_evaluation_run` 제거, deprecated `datetime.utcnow()` 정리.

## [0.1.0] - 2026-11-03

### Added

- pypo(AI 동료) devbot 하네스: 작업 고르기 → 구현 → 검증 → PR 생성 → 회고 루프 (`src/app/agents/devbot/`)
- 코드 작성 평가 벤치마크와 AST 관문(`ASTGatekeeper`), 반복 실행기, 성공 궤적 로깅(`MetricLogger`, `AgentEvaluator`)
- 카드 실적 배분 계산기 API (`src/app/card/`) 및 단위 테스트
- User/Agent 모델, LangGraph·MCP·Neo4j 투영 등 플랫폼 스캐폴딩
