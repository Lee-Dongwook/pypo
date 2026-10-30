# AGENTS.md

이 저장소에서 일하는 에이전트(pypo 포함)와 사람을 위한 규칙입니다. 짧게 유지합니다.

## 저장소

- 백엔드: Python 3.13, FastAPI, Pydantic v2. 코드는 `src/app/`, 테스트는 `tests/`.
- 프론트엔드: Next.js, TypeScript, Tailwind. `apps/web/`, API 타입은 `packages/api-client/`.
- 카드 계산기: `src/app/card/` (`schemas.py` 모델, `calculator.py` 순수 함수, `api.py` 엔드포인트).
- 제품 방향: `docs/STRATEGY.md`. 카드 앱 요구사항: `docs/PRD.md`.

## 명령

```bash
uv run ruff check .        # lint
uv run pytest              # 테스트 (DB가 필요한 통합 테스트는 환경 변수가 없으면 자동 skip)
pnpm typecheck             # apps/web 또는 packages를 건드렸을 때
```

세 가지가 모두 통과해야 끝난 작업입니다.

## 코드 규칙

- 한 줄 최대 120자. import 순서는 ruff가 정합니다.
- 금액은 원 단위 `int`. 비율은 `Decimal`. `float`로 돈을 계산하지 않습니다.
- 사용자에게 보이는 메시지(에러 포함)는 한국어. 식별자는 영어.
- 검증은 경계(Pydantic 모델, API)에서 합니다. 계산 함수는 순수 함수로 둡니다.
- 새 동작에는 테스트를 붙입니다. 테스트 이름은 동작을 문장으로 씁니다: `test_missing_spend_is_rejected_not_treated_as_zero`.
- 테스트에서 import는 `from src.app.card.calculator import ...` 형태입니다.
- 쓰지 않는 코드, 쓰지 않는 import, 미래를 위한 추상화는 남기지 않습니다.

## 작업 규칙

- 이슈에 적힌 파일만 수정합니다. 범위를 벗어나야 하면 수정하지 말고 이슈에 질문을 남깁니다.
- 수정 금지: `migrations/`, `.github/`, `.env*`, `uv.lock`, `pnpm-lock.yaml`, `agent/persona.md`, `agent/evals/`, `src/app/agents/devbot/guards.py`.
- main에 직접 푸시하지 않습니다. 브랜치는 `pypo/<이슈번호>-<slug>`.
- 커밋 메시지: `feat(card): ...`, `fix(web): ...`처럼 영어 소문자, 무엇이 바뀌었는지 한 줄.
- 추측해서 만들지 않습니다. 모르면 묻습니다.
