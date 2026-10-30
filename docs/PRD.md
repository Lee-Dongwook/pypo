# Product Requirements Document (PRD)

# Card Benefit Optimizer

> Version: 0.2.0  
> Status: Draft  
> Last Updated: 2026-10-30  
> Product Type: Personal Finance / Fintech  
> Platform: Responsive Web Application  
> Strategy: [STRATEGY.md](STRATEGY.md) 1단계. 계산 규칙 상세는 [CARD_ALLOCATION_V0.md](CARD_ALLOCATION_V0.md)

---

## 1. Product Overview

### 1.1 Product Definition

Card Benefit Optimizer는 사용자가 보유한 신용카드의 실적 구간과 현재 실적을 분석해, **이번 달 남은 지출을 어느 카드에 몰아야 다음 달 혜택이 늘어나는지, 어느 카드는 채우지 말아야 하는지** 알려주는 월 1회 배분 계산기다.

카드사마다 서로 다른 실적 구간, 할인한도, 실적 제외 항목을 통합된 데이터 구조로 관리하고, 이를 기반으로 카드별로 다음 구간까지 남은 금액과 늘어나는 한도를 계산한다.

핵심은 추천보다 **거절**이다. "3만 원 더 쓰면 2천 원 늘어납니다. 채우지 마세요"라고 말하는 서비스는 없고, 카드사 앱은 구조상 이 말을 할 수 없다.

### 1.2 Product Vision

**Spend smarter. Save more.**

사용자가 카드 혜택을 일일이 이해하거나 계산하지 않아도, 보유한 카드의 혜택을 최대한 효율적으로 활용할 수 있도록 지원한다.

단순히 할인율이 높은 카드를 추천하는 것이 아니라, 전월 실적과 잔여 할인한도, 결제 업종 및 금액을 종합적으로 고려하여 실질적인 소비 의사결정을 돕는다.

### 1.3 Core Value Proposition

"어차피 쓸 돈을 어디에 몰고, 어디는 채우지 말아야 하는지 알려준다."

### 1.4 Product Principles

1. **Accuracy First:** 계산 결과는 상품설명서의 원문 조건을 기반으로 한다.
2. **Explainability:** 모든 추천 결과에는 계산 근거를 제공한다.
3. **No Unnecessary Spending:** 카드 실적을 채우기 위한 불필요한 소비를 유도하지 않는다.
4. **Transparency:** 데이터의 출처, 확인일 및 계산상의 한계를 명시한다.
5. **Simplicity:** 복잡한 카드 혜택 조건을 일반 사용자가 이해할 수 있는 정보로 변환한다.

---

## 2. Problem Definition

### 2.1 Problems

일반적인 신용카드 사용자는 다음과 같은 문제를 경험한다.

| Problem                 | Description                                                   |
| ----------------------- | ------------------------------------------------------------- |
| 복잡한 혜택 조건        | 카드마다 전월 실적, 할인율, 할인한도가 다르다.                |
| 실적 관리의 어려움      | 현재 실적이 어느 구간에 해당하는지 파악하기 어렵다.           |
| 할인한도 인지 부족      | 이미 사용한 할인한도와 남은 한도를 알기 어렵다.               |
| 결제 카드 선택의 어려움 | 여러 카드를 보유한 경우 어떤 카드가 유리한지 판단하기 어렵다. |
| 혜택 누락               | 적절한 카드로 결제하지 못해 받을 수 있는 혜택을 놓친다.       |

### 2.2 Proposed Solution

카드 상품 정보를 표준화하고 사용자가 입력한 정보를 바탕으로 다음 기능을 제공한다.

- 보유 카드 등록 및 관리
- 카드별 이번 달 인정 실적 입력
- 이번 달 남은 예상 지출 입력
- 카드별 다음 구간까지 남은 금액과 늘어나는 한도 계산
- 남은 지출 안에서 이득이 가장 큰 배분안 제시 (채울 카드 / 채우지 말 카드)
- 배분 결과의 계산 근거 제공

### 2.3 Product Scope Boundary

본 서비스는 카드사에서 확정한 실제 청구 할인액을 제공하는 서비스가 아니다.

사용자가 제공한 실적 및 할인한도 정보를 기반으로 예상 혜택을 계산하는 의사결정 지원 도구다.

실제 할인 여부와 금액은 카드사의 최종 승인 및 청구 기준에 따라 달라질 수 있다.

---

## 3. Target Users

### 3.1 Primary Target

신용카드 혜택에 익숙하지 않은 일반 사용자.

| Attribute           | Description                                 |
| ------------------- | ------------------------------------------- |
| Card Ownership      | 신용카드 1~3장 이상                         |
| Financial Knowledge | 일반적인 수준                               |
| Spending Pattern    | 월별 소비 패턴이 존재                       |
| Main Pain Point     | 카드별 혜택 조건을 기억하고 비교하기 어려움 |
| Expected Value      | 가장 유리한 결제 카드를 쉽게 선택           |

### 3.2 User Persona

**Persona A — 일반 직장인**

- 신용카드 2~3장 보유
- 카드별 할인 조건을 정확히 기억하지 못함
- 매월 카드 사용 실적을 확인하지만 직접 계산하지 않음
- 예정된 결제에서 더 많은 혜택을 받고 싶음
- 불필요한 소비를 늘리고 싶지는 않음

### 3.3 Primary User Story

> As a credit card user,  
> I want to know which card to put my remaining spending on this month, and which cards to stop filling,  
> so that I raise next month's benefits without spending more than I planned.

---

## 4. Product Goals and Non-Goals

### 4.1 Goals

- 사용자가 보유한 여러 카드의 실적 구간을 한곳에서 비교한다.
- 현재 실적에 따른 구간과 한도를 정확하게 계산한다.
- 남은 예상 지출 안에서 다음 달 한도가 가장 많이 늘어나는 배분안을 제시한다.
- 채울 가치가 없는 카드는 분명하게 "채우지 마세요"라고 말한다.
- 상품설명서 기반의 신뢰할 수 있는 카드 데이터를 제공한다.

### 4.2 Non-Goals (MVP)

다음 기능은 MVP에서 구현하지 않는다.

- 카드사 계정 연동
- 결제 직전 단건 카드 추천 (P1, 6.7)
- 실제 카드 결제 내역 자동 수집
- 금융 계좌 및 자산 연동
- 사용자 카드 앱 화면 OCR
- AI 기반 카드 추천
- 전체 카드 시장 대상 상품 추천
- 포인트 및 마일리지 가치 환산
- 연회비 대비 손익 분석
- 가족카드 및 법인카드 지원
- 상품설명서 자동 파싱
- 카드 발급 및 금융상품 중개

---

## 5. Core User Journey

### 5.1 Main Flow

1. 사용자가 서비스에 접속한다 (월 1회, 실적 마감 D-7 전후).
2. 보유한 신용카드를 카탈로그에서 선택한다.
3. 카드사 앱에 표시된 카드별 이번 달 인정 실적을 입력한다.
4. 이번 달 남은 예상 지출을 입력한다.
5. 서비스가 카드별 다음 구간까지 남은 금액과 늘어나는 한도를 계산한다.
6. 남은 지출 안에서 이득이 가장 큰 배분안을 만든다.
7. 사용자는 "이 카드에 쓰세요 / 이 카드는 채우지 마세요"와 계산 근거를 확인한다.

### 5.2 User Flow

```text
Landing
   |
   v
My Cards
   |
   +---- Add Card → Select Card Product
   |
   +---- Input This Month's Recognized Spend (per card)
   |
   v
Remaining Spend
   |
   +---- Input Planned Spend for the Rest of the Month
   |
   v
Allocation Result
   |
   +---- Fill: 이 카드에 N원 더 쓰면 한도 +M원
   +---- Hold off: 이번 달은 넘기지 마세요
   +---- Other: 이미 최고 구간 / 올라가도 그대로 / 다른 카드가 더 이득
   |
   v
Analysis Detail (근거 조항, 상품설명서, 확인일)
```

---

## 6. Functional Requirements

우선순위 정의:

- P0: MVP 필수 기능
- P1: MVP 이후 확장 기능
- P2: 장기적인 제품 확장 기능

### 6.1 Card Catalog

**Priority: P0**

사용자가 지원하는 카드 상품을 조회하고 선택할 수 있어야 한다.

Requirements:

- 카드 상품 목록 조회
- 카드명 및 발급사 표시
- 카드 혜택 요약 표시
- 상품설명서 출처 제공
- 상품 정보 최종 확인일 표시
- 지원하지 않는 혜택 유형 명시

Acceptance Criteria:

- 최소 3개 이상의 카드 상품을 조회할 수 있어야 한다.
- 모든 상품은 원본 상품설명서 URL을 보유해야 한다.
- 모든 상품은 데이터 확인일을 보유해야 한다.

### 6.2 My Cards

**Priority: P0**

사용자가 보유한 카드를 등록하고 관리할 수 있어야 한다.

Requirements:

- 카드 등록
- 카드 삭제
- 동일 상품의 복수 카드 등록 가능
- 카드별 전월 인정 실적 입력
- 카드별 잔여 할인한도 입력 또는 미확인 상태 관리
- 카드별 혜택 조건 확인

Acceptance Criteria:

- 여러 카드를 등록할 수 있어야 한다.
- 카드별 실적을 독립적으로 관리해야 한다.
- 카드 상품 정보와 사용자 입력 정보를 분리해야 한다.
- 실적 정보가 없거나 불완전하면 계산 결과에 이를 표시해야 한다.

### 6.3 Remaining Spend Input

**Priority: P0**

사용자가 이번 달 남은 예상 지출을 입력할 수 있어야 한다.

Input Fields:

| Field         | Description                           |
| ------------- | ------------------------------------- |
| spends        | 카드별 이번 달 인정 실적              |
| planned_spend | 이번 달 남은 예상 지출 (어차피 쓸 돈) |

Requirements:

- 카드별 인정 실적 입력 (총 사용액과 다르다는 안내 포함)
- 남은 예상 지출 입력
- 잘못된 금액 검증

Acceptance Criteria:

- 금액은 0 이상 원 단위 정수로 처리한다.
- 남은 예상 지출은 "더 쓸 돈"이 아니라 "어차피 쓸 돈"이라고 안내한다.

### 6.4 Tier and Gain Calculation

**Priority: P0**

카드별 현재 구간, 다음 구간까지 남은 금액, 늘어나는 한도를 계산한다.

Requirements:

- 현재 실적 구간 확인 (경계값 포함)
- 다음 구간까지 남은 금액 계산
- 다음 구간 도달 시 늘어나는 혜택 계산
- 할인율형 구간은 늘어나는 혜택을 하한으로 표시
- 최상위 구간 도달 여부 표시
- 계산 근거 반환

Acceptance Criteria:

- 카드 상품에 정의된 구간에 따라 계산해야 한다.
- 구간이 올라가도 혜택이 늘지 않으면 "채울 이유 없음"으로 표시해야 한다.
- 실적 정보가 없는 카드는 실적 0원으로 보지 않고 미입력으로 구분해야 한다.

### 6.5 Allocation

**Priority: P0**

남은 예상 지출 안에서 늘어나는 혜택 합이 가장 큰 카드 조합을 고른다.

Requirements:

- 남은 예상 지출을 넘지 않는 범위에서 최적 조합 선택
- 동률이면 쓰는 금액이 적은 조합 선택 (남은 돈은 사용자에게 남긴다)
- 선택되지 않은 카드는 이유와 함께 분류: 예산 초과(`over_budget`), 다른 카드가 더 이득(`lower_priority`), 올라가도 그대로(`no_gain`), 최고 구간(`top_tier`)
- 채울 카드가 없으면 "추가로 쓰지 않는 것이 이득"이라고 명시

Acceptance Criteria:

- 배분에 쓰는 금액 합은 남은 예상 지출을 넘지 않는다.
- 남은 예상 지출을 넘는 지출을 권하지 않는다.
- 결과는 등록된 카드 범위 안에서만 제공한다.

### 6.6 Analysis Detail

**Priority: P0**

사용자가 추천 결과의 근거를 확인할 수 있어야 한다.

Requirements:

- 현재 전월 실적
- 적용 실적 구간
- 적용 할인율
- 할인 대상 결제 금액
- 현재 할인한도
- 잔여 할인한도
- 예상 할인액
- 상품설명서 근거 조항
- 상품설명서 URL 및 확인일

### 6.7 Single Purchase Recommendation

**Priority: P1**

결제 한 건(업종, 금액)을 입력하면 등록된 카드별 예상 할인액을 비교한다. 배분 결과를 보조하는 기능이며, 주력 기능으로 내세우지 않는다 (경쟁 서비스가 이미 제공하는 영역).

Requirements:

- 업종 적격성, 할인율, 잔여 할인한도 확인
- 잔여 할인한도를 모르면 계산 불가로 표시 (8.4)
- 계산 가능한 카드와 계산 불가 카드를 분리해 정렬 (8.6)

현재 구현: `POST /card/optimize` (화면 미연결).

### 6.8 Multiple Purchase Allocation

**Priority: P2**

여러 결제 예정 건을 할인한도 중복 없이 복수 카드에 배분하는 기능.

### 6.9 Card Recommendation

**Priority: P2**

사용자의 소비 패턴을 기반으로 미보유 카드까지 추천한다.

MVP에서는 지원하지 않는다.

---

## 7. Domain Model Requirements

### 7.1 Core Entities

| Entity             | Responsibility           |
| ------------------ | ------------------------ |
| CardProduct        | 카드 상품 기본 정보      |
| CardBenefit        | 카드별 혜택 정보         |
| BenefitRule        | 혜택 계산 규칙           |
| BenefitTier        | 실적 구간 및 할인한도    |
| BenefitCategory    | 혜택 적용 업종           |
| UserCard           | 사용자가 등록한 카드     |
| SpendingProfile    | 카드별 전월 실적 정보    |
| PurchasePlan       | 예정된 결제 정보         |
| OptimizationResult | 카드별 계산 및 추천 결과 |

### 7.2 Domain Separation

카드 상품 데이터와 사용자 데이터를 분리한다.

- CardProduct: 공통 상품 정보
- UserCard: 사용자가 보유한 카드 정보
- SpendingProfile: 사용자가 입력한 실적 정보
- PurchasePlan: 예정된 소비 정보

동일한 카드 상품을 여러 사용자가 등록할 수 있어야 한다.

### 7.3 Benefit Rule Types

MVP에서 우선 지원할 규칙 유형:

**Tiered Benefit**

전월 실적 구간에 따라 할인한도가 달라지는 유형.

```typescript
type TieredBenefitRule = {
  type: "tiered";
  tiers: {
    spendThreshold: number;
    discountCap: number;
  }[];
};
```

**Flat Rate Benefit**

일정 실적을 충족하면 고정 할인율을 제공하는 유형.

```typescript
type FlatRateBenefitRule = {
  type: "flat_rate";
  minimumSpend: number;
  discountRate: number;
  discountCap: number | null;
};
```

단, 실제 계산을 위해 할인 대상 업종, 할인 적용 조건 및 할인율은 별도 혜택 데이터로 관리해야 한다.

### 7.4 Data Source

카드 상품 데이터의 원본은 카드사 공식 상품설명서다.

각 상품은 다음 정보를 보유해야 한다.

- 상품명
- 발급사
- 상품설명서 URL
- 데이터 확인일 (`as_of`)
- 원본 문서 해시 (추후 적용)
- 실적 기준
- 할인율 및 할인한도
- 실적 제외 항목
- 근거 조항

MVP 데이터 관리 정책:

- 최소 3개, 목표 10개 상품
- 수동 데이터 큐레이션
- 원문 기반 교차 검수
- 공공 API 연동 없음
- 자동 문서 파싱 없음

---

## 8. Calculation Policy

### 8.1 Previous Month Eligible Spend

전월 실적은 사용자의 총 이용금액과 구분한다.

카드사가 인정하는 실적을 기준으로 계산한다.

실적 제외 항목은 상품설명서 원문을 기준으로 안내한다.

### 8.2 Tier Calculation

현재 실적이 충족하는 가장 높은 실적 구간을 찾는다.

다음 구간이 존재하면 필요한 추가 실적을 계산한다.

```text
Remaining Spend =
Next Tier Threshold - Current Eligible Spend
```

최상위 구간에 도달한 경우 다음 구간이 없음을 표시한다.

### 8.3 Discount Calculation

기본 예상 할인액 계산:

```text
Theoretical Discount =
Eligible Purchase Amount × Discount Rate

Estimated Discount =
MIN(
  Theoretical Discount,
  Remaining Discount Cap
)
```

다음 조건을 반드시 고려한다.

- 실적 조건 충족 여부
- 할인 적용 업종
- 할인 대상 금액
- 할인율
- 잔여 할인한도
- 상품별 할인 적용 조건

할인한도가 무제한인 경우 별도로 처리한다.

### 8.4 Discount Cap

다음 두 값을 구분한다.

- Total Discount Cap: 해당 기간에 받을 수 있는 전체 할인한도
- Remaining Discount Cap: 이미 사용한 할인액을 제외한 잔여 할인한도

잔여 할인한도를 확인할 수 없는 경우 전체 한도를 잔여 한도로 간주하지 않는다.

### 8.5 Calculation Result Types

| Result            | Meaning                          |
| ----------------- | -------------------------------- |
| Eligible          | 혜택 조건 충족                   |
| Ineligible        | 혜택 조건 미충족                 |
| Insufficient Data | 계산에 필요한 데이터 부족        |
| Unsupported       | 현재 엔진에서 지원하지 않는 규칙 |

### 8.6 Allocation Policy

배분은 다음 문제를 푼다 (상세: CARD_ALLOCATION_V0.md 2.3).

```text
maximize   Σ 늘어나는 혜택
subject to Σ 다음 구간까지 남은 금액 <= 남은 예상 지출
```

1. 늘어나는 혜택 합이 큰 조합을 고른다.
2. 동률이면 쓰는 금액이 적은 조합을 고른다.
3. 선택되지 않은 카드는 이유와 함께 표시한다.

단건 추천(6.7)의 정렬은 계산 가능한 카드를 할인액순으로, 실적 미충족 카드, 데이터 부족·계산 불가 카드 순으로 둔다. 동률이면 입력 순서를 유지한다.

추천 결과는 실제 카드사 청구 결과를 보장하지 않는다.

---

## 9. Non-Functional Requirements

### 9.1 Accuracy

- 핵심 계산 로직은 단위 테스트를 제공한다.
- 실적 구간 경계값을 검증한다.
- 할인한도 초과 여부를 검증한다.
- 계산 결과에 근거 조항을 제공한다.
- 원 단위 정수 연산을 기본으로 한다.

### 9.2 Reliability

- 잘못된 카드 데이터는 계산에 사용하지 않는다.
- 데이터가 부족하면 계산 불가 상태를 표시한다.
- 상품 데이터의 출처와 확인일을 제공한다.
- 계산 실패 시 잘못된 추천을 제공하지 않는다.

### 9.3 Privacy

- MVP에서는 금융 계정 및 카드사 계정 연동을 지원하지 않는다.
- 카드번호, CVC, 비밀번호를 수집하지 않는다.
- 개인별 실적 입력값은 계산 요청에만 사용하고 서버에 저장하지 않는다 (API는 상태를 갖지 않는다).
- 브라우저에 저장하는 정보와 삭제 방법을 명확하게 안내한다.

### 9.4 Performance

- 카드별 계산은 사용자 입력 후 즉시 실행한다.
- 계산 API는 데이터베이스 조회 없이 동작한다.
- 카드 데이터는 큐레이션된 JSON 파일로 제공한다.

### 9.5 Accessibility and Usability

- 모바일과 데스크톱 반응형 지원
- 금융 전문 용어에 대한 쉬운 설명
- 입력값 오류에 대한 명확한 안내
- 할인 조건 및 추천 근거를 쉽게 확인할 수 있는 UI

---

## 10. Technical Architecture

### 10.1 Technology Stack

| Layer         | Technology                                      |
| ------------- | ----------------------------------------------- |
| Frontend      | Next.js (App Router) + React                    |
| Frontend Lang | TypeScript                                      |
| Styling       | Tailwind CSS                                    |
| Server State  | TanStack Query                                  |
| Client State  | Zustand                                         |
| Backend       | FastAPI                                         |
| Backend Lang  | Python                                          |
| Validation    | Pydantic (도메인 경계)                          |
| Unit Testing  | pytest                                          |
| E2E Testing   | Playwright                                      |
| Card Data     | 큐레이션 JSON (`samples/card_products.v0.json`) |
| Monorepo      | pnpm workspace (web) + uv (Python)              |
| Deployment    | 미정                                            |

### 10.2 Architecture Principles

- UI와 계산 도메인을 분리한다. 계산은 백엔드에서만 수행한다.
- 계산 엔진은 순수 함수 중심으로 설계한다.
- 카드 상품 데이터는 버전이 붙은 JSON 파일로 관리한다 (`CARD_CATALOG_PATH`로 교체 가능).
- 입력값 검증은 API 경계(Pydantic)에서 수행한다.
- 계산 결과에는 근거와 상태를 포함한다.
- 계산 API는 사용자 데이터를 저장하지 않는다.
- 프론트엔드 타입은 `packages/api-client`에서 백엔드 스키마를 수동으로 따라간다.

### 10.3 Core Modules

```text
src/app/card/           # 카드 도메인 (백엔드)
├── schemas.py          # Card, Tier 등 도메인 모델
├── catalog.py          # 카드 카탈로그 로딩
├── calculator.py       # 계산 엔진 (순수 함수)
└── api.py              # HTTP 엔드포인트

apps/web/               # Next.js 프론트엔드
├── app/
├── components/
└── store/

packages/api-client/    # 프론트엔드용 API 타입 및 클라이언트

samples/
└── card_products.v0.json
```

---

## 11. MVP Scope

### 11.1 Included

- 카드 상품 카탈로그
- 보유 카드 등록 및 삭제
- 카드별 이번 달 인정 실적 입력
- 이번 달 남은 예상 지출 입력
- 카드별 다음 구간까지 남은 금액과 늘어나는 혜택 계산
- 남은 지출 기준 배분안 ("채우세요 / 채우지 마세요")
- 배분 근거 표시
- 상품설명서 출처 표시
- 모바일 및 데스크톱 지원

### 11.2 Excluded

- 회원가입 및 로그인
- 서버 기반 사용자 데이터 저장
- 카드사 API 연동
- OCR
- AI 추천
- 포인트 및 마일리지
- 연회비 손익 계산
- 결제 직전 단건 추천 화면 (P1)
- 복수 결제 자동 배분
- 카드 상품 자동 수집

### 11.3 MVP Dataset

초기에는 3개 상품으로 계산 엔진을 검증하고, 이후 10개까지 확대한다.

상품 선정 기준:

- 신용카드
- 실적 구간이 2개 이상인 상품을 우선
- 할인한도가 명확한 상품
- 원 단위 할인 또는 캐시백형
- 옵션 선택이 없는 상품
- 공식 상품설명서 확보 가능

---

## 12. Success Metrics

### 12.1 Product Metrics

| Metric                         | Purpose                             |
| ------------------------------ | ----------------------------------- |
| Card Registration Rate         | 카드 등록 완료 비율                 |
| Optimization Completion Rate   | 카드 분석 완료 비율                 |
| Recommendation Acceptance Rate | 추천 결과에 대한 사용자 유용성 평가 |
| Repeat Usage Rate              | 재방문율                            |
| Calculation Accuracy           | 계산 정확도                         |

### 12.2 Initial Validation Targets

STRATEGY.md 1단계 Go/No-Go 기준과 같다.

| Metric                    |   Target |
| ------------------------- | -------: |
| 입력 완료율               | 80% 이상 |
| 다음 달 재입력률          | 30% 이상 |
| 예측 오차 (명세서 대조)   |  1% 미만 |
| "채우지 마세요" 노출 비율 | 20% 이상 |

재입력률이 30%를 밑돌면 카드 계산기를 접고 STRATEGY.md 2단계(지원금)로 넘어간다.

### 12.3 Core Validation Questions

- 사용자는 자신의 카드 혜택을 더 쉽게 이해하는가?
- 추천 결과를 실제 결제 결정에 활용하는가?
- 추천 근거를 신뢰하는가?
- 기존 카드 관리 방식보다 편리하다고 느끼는가?
- 반복적으로 사용할 이유가 있는가?

---

## 13. Definition of Done

MVP는 다음 조건을 충족하면 완료된 것으로 판단한다.

### Product

- [ ] 최소 3개 실제 카드 상품 등록 (상품설명서 URL 포함)
- [ ] 카드 상품 카탈로그 조회
- [x] 보유 카드 등록 및 삭제 (같은 상품 여러 장은 미지원)
- [x] 카드별 이번 달 인정 실적 입력
- [x] 남은 예상 지출 입력
- [x] 배분 결과 표시 (채우세요 / 채우지 마세요)
- [x] 근거 조항 제공
- [ ] 상품설명서 URL 및 확인일 표시

### Calculation Engine

- [ ] 실적 구간 계산
- [ ] 할인율 계산
- [ ] 할인한도 계산
- [ ] 실적 미충족 처리
- [ ] 할인 대상 업종 검증
- [ ] 잔여 할인한도 검증
- [ ] 계산 불가능한 상품 처리
- [ ] 경계값 단위 테스트

### Quality

- [ ] 핵심 계산 로직 Vitest 테스트 통과
- [ ] 주요 사용자 플로우 Playwright 테스트 통과
- [ ] 모바일 반응형 확인
- [ ] 원문 기준 카드 데이터 검수
- [ ] 개인정보 처리 방식 안내
- [ ] 프로덕션 배포

---

## 14. Future Roadmap

이 제품 이후의 단계(카드 + 지원금 충돌 지도, 근거 있는 혜택 질의, B2B 파일럿)는 [STRATEGY.md](STRATEGY.md) 3절을 따른다.

---

## 15. Open Questions

MVP 구현 전 확정해야 할 사항.

| Question         | Decision Required                          |
| ---------------- | ------------------------------------------ |
| 할인한도 사용량  | 사용자가 직접 입력할 것인지                |
| 카드별 실적 기간 | 전월 실적 기준으로 고정할 것인지           |
| 결제 업종        | 초기 지원 카테고리 범위                    |
| 복합 할인        | 여러 할인 조건이 적용되는 경우의 계산 순서 |
| 할인 반올림      | 카드사별 원 단위 처리 방식                 |
| 신규 회원        | 발급월 및 실적 유예 조건 처리              |
| 데이터 갱신      | 상품설명서 개정 확인 프로세스              |
| 로컬 저장        | 브라우저 데이터 보존 및 삭제 정책          |

위 항목은 추측으로 구현하지 않고 실제 상품설명서와 검증 사례를 기준으로 결정한다.

---

## 16. Final Product Statement

Card Benefit Optimizer는 이번 달 남은 지출을 어디에 몰고, 어디는 채우지 말아야 하는지를 근거와 함께 알려주는 서비스다.

카드 상품 데이터를 표준화하고, 사용자가 입력한 현재 실적과 남은 예상 지출을 분석해 다음 달 혜택이 가장 많이 늘어나는 배분안을 제시한다.

이 제품은 pypo 엔진의 첫 계단이다. 여기서 검증한 계산 정확도와 근거 구조를 다음 단계의 혜택 충돌 지도와 B2B 엔진으로 넓힌다.

**The goal is not to make users spend more. The goal is to help them get more value from what they already spend.**
