# Product Requirements Document (PRD)

# Card Benefit Optimizer

> Version: 0.1.0  
> Status: Draft  
> Last Updated: 2026-10-30  
> Product Type: Personal Finance / Fintech  
> Platform: Responsive Web Application

---

## 1. Product Overview

### 1.1 Product Definition

Card Benefit Optimizer는 사용자가 보유한 신용카드의 혜택 조건과 현재 전월 실적을 분석하여, 예정된 결제에서 가장 유리한 카드를 추천하는 서비스다.

카드사마다 서로 다른 할인 조건, 전월 실적 구간, 할인한도 및 실적 제외 항목을 통합된 데이터 구조로 관리하고, 이를 기반으로 카드별 예상 혜택을 계산한다.

사용자는 복잡한 카드 약관을 직접 이해하지 않아도 자신의 소비 상황에 적합한 결제 수단을 선택할 수 있다.

### 1.2 Product Vision

**Spend smarter. Save more.**

사용자가 카드 혜택을 일일이 이해하거나 계산하지 않아도, 보유한 카드의 혜택을 최대한 효율적으로 활용할 수 있도록 지원한다.

단순히 할인율이 높은 카드를 추천하는 것이 아니라, 전월 실적과 잔여 할인한도, 결제 업종 및 금액을 종합적으로 고려하여 실질적인 소비 의사결정을 돕는다.

### 1.3 Core Value Proposition

"내 카드 혜택을 이해하지 않아도, 가장 유리하게 사용할 수 있도록 도와준다."

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
- 카드별 전월 실적 입력
- 실적 구간 및 할인한도 분석
- 결제 예정 정보 입력
- 카드별 예상 할인액 계산
- 예상 혜택 기준 카드 추천
- 추천 결과의 계산 근거 제공

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
> I want to compare the benefits of my registered cards before making a purchase,  
> so that I can choose the most beneficial payment method.

---

## 4. Product Goals and Non-Goals

### 4.1 Goals

- 사용자가 보유한 여러 카드의 혜택을 한곳에서 비교한다.
- 전월 실적에 따른 할인 조건과 한도를 정확하게 계산한다.
- 예정된 결제에 적용할 수 있는 예상 할인액을 제공한다.
- 가장 유리한 카드를 추천하고 추천 이유를 설명한다.
- 상품설명서 기반의 신뢰할 수 있는 카드 데이터를 제공한다.

### 4.2 Non-Goals (MVP)

다음 기능은 MVP에서 구현하지 않는다.

- 카드사 계정 연동
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

1. 사용자가 서비스에 접속한다.
2. 보유한 신용카드를 카탈로그에서 선택한다.
3. 카드별 전월 실적을 입력한다.
4. 필요한 경우 할인한도 사용 현황을 입력한다.
5. 결제 예정 업종과 금액을 입력한다.
6. 서비스가 등록된 카드별 예상 혜택을 계산한다.
7. 예상 혜택을 기준으로 카드를 정렬한다.
8. 사용자는 추천 결과와 계산 근거를 확인한다.

### 5.2 User Flow

```text
Landing
   |
   v
My Cards
   |
   +---- Add Card
   |       |
   |       v
   |   Select Card Product
   |       |
   |       v
   |   Input Previous Month Spend
   |
   v
Optimizer
   |
   +---- Select Purchase Category
   |
   +---- Input Purchase Amount
   |
   v
Calculate Benefits
   |
   v
Compare Registered Cards
   |
   v
Recommendation Result
   |
   v
Analysis Detail
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

### 6.3 Spending Input

**Priority: P0**

사용자가 예정된 결제 정보를 입력할 수 있어야 한다.

Input Fields:

| Field        | Description    |
| ------------ | -------------- |
| category     | 결제 업종      |
| amount       | 결제 예정 금액 |
| purchaseDate | 결제 예정일    |

Requirements:

- 업종 선택
- 결제 금액 입력
- 결제 예정일 입력
- 잘못된 금액 및 입력값 검증

Acceptance Criteria:

- 유효한 결제 정보를 입력할 수 있어야 한다.
- 금액은 0보다 큰 원 단위 정수로 처리한다.
- 지원하지 않는 업종은 별도로 표시한다.

### 6.4 Benefit Calculation

**Priority: P0**

등록된 카드의 혜택 조건을 기반으로 예상 할인액을 계산한다.

Requirements:

- 전월 실적 충족 여부 확인
- 실적 구간 확인
- 결제 업종 적격성 확인
- 적용 할인율 확인
- 할인한도 확인
- 예상 할인액 계산
- 계산 근거 반환

Acceptance Criteria:

- 카드 상품에 정의된 조건에 따라 계산해야 한다.
- 할인한도를 초과하는 결과를 반환해서는 안 된다.
- 실적 미충족 카드는 혜택 미적용 상태로 표시해야 한다.
- 필요한 데이터가 부족한 경우 확정적인 계산 결과를 반환해서는 안 된다.

### 6.5 Card Optimization

**Priority: P0**

등록된 카드 중 예상 혜택이 가장 높은 카드를 추천한다.

Requirements:

- 등록 카드 전체 계산 결과 비교
- 예상 할인액 기준 정렬
- 실적 미충족 카드 구분
- 계산 불가능한 카드 구분
- 추천 근거 제공
- 동일 할인액에 대한 동률 처리

Acceptance Criteria:

- 추천 결과는 등록된 카드 범위 내에서만 제공한다.
- 계산 가능한 카드와 계산 불가능한 카드를 구분한다.
- 추천 이유를 사용자에게 설명할 수 있어야 한다.
- 단순히 데이터가 없는 카드를 0원 할인 카드로 취급해서는 안 된다.

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

### 6.7 Spending Tier Analysis

**Priority: P1**

사용자의 현재 실적을 기반으로 다음 실적 구간까지 필요한 금액을 계산한다.

Requirements:

- 현재 실적 구간 표시
- 다음 실적 구간 표시
- 다음 구간까지 필요한 금액 계산
- 다음 구간 도달 시 할인한도 증가량 계산
- 최상위 구간 도달 여부 표시

중요 정책:

다음 구간에 도달하기 위한 추가 소비를 무조건 권장하지 않는다. 사용자가 원래 계획한 소비를 기준으로 참고 정보를 제공한다.

### 6.8 Multiple Card Allocation

**Priority: P1**

여러 결제 예정 건을 복수 카드에 배분하는 기능.

- 복수 결제 계획 입력
- 카드별 혜택 계산
- 할인한도 중복 사용 방지
- 전체 예상 혜택 비교
- 카드별 결제 배분 제안

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

### 8.6 Recommendation Policy

추천 순위는 실제 계산 가능한 예상 할인액을 기준으로 한다.

1. 적용 가능한 예상 할인액이 높은 카드
2. 예상 할인액이 동일하면 적용 조건이 명확한 카드
3. 계산 불가능한 카드는 별도 그룹으로 표시

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
- 개인별 실적 입력값은 서버에 전송하지 않는 구조를 우선한다.
- 브라우저에 저장하는 정보와 삭제 방법을 명확하게 안내한다.

### 9.4 Performance

- 카드별 계산은 사용자 입력 후 즉시 실행한다.
- 초기 MVP는 별도 백엔드 없이 동작할 수 있어야 한다.
- 카드 데이터는 정적 JSON으로 제공할 수 있어야 한다.

### 9.5 Accessibility and Usability

- 모바일과 데스크톱 반응형 지원
- 금융 전문 용어에 대한 쉬운 설명
- 입력값 오류에 대한 명확한 안내
- 할인 조건 및 추천 근거를 쉽게 확인할 수 있는 UI

---

## 10. Technical Architecture

### 10.1 Technology Stack

| Layer            | Technology                    |
| ---------------- | ----------------------------- |
| Frontend         | React                         |
| Language         | TypeScript                    |
| Build Tool       | Vite                          |
| Styling          | Tailwind CSS                  |
| Validation       | Zod                           |
| State Management | Zustand or React Context      |
| Unit Testing     | Vitest                        |
| E2E Testing      | Playwright                    |
| Data Storage     | Static JSON + Browser Storage |
| Deployment       | Vercel or Cloudflare Pages    |

### 10.2 Architecture Principles

- UI와 계산 도메인을 분리한다.
- 계산 엔진은 순수 함수 중심으로 설계한다.
- 카드 상품 데이터는 정적 데이터로 관리한다.
- 입력값 검증은 도메인 경계에서 수행한다.
- 계산 결과에는 근거와 상태를 포함한다.
- 추후 백엔드 전환을 고려해 데이터 접근 계층을 분리한다.

### 10.3 Core Modules

```text
src/
├── app/
│   ├── routes/
│   └── providers/
│
├── entities/
│   ├── card/
│   ├── benefit/
│   └── spending/
│
├── features/
│   ├── card-management/
│   ├── spending-input/
│   ├── benefit-analysis/
│   └── card-optimization/
│
├── shared/
│   ├── components/
│   ├── utils/
│   └── types/
│
└── data/
    └── card-products.json
```

---

## 11. MVP Scope

### 11.1 Included

- 카드 상품 카탈로그
- 보유 카드 등록 및 삭제
- 카드별 전월 실적 입력
- 결제 업종 및 금액 입력
- 지원하는 혜택 규칙 계산
- 예상 할인액 계산
- 카드별 혜택 비교
- 최적 카드 추천
- 추천 근거 표시
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

초기 사용자 테스트를 위한 가설적 목표:

| Metric                       |               Target |
| ---------------------------- | -------------------: |
| Card Registration Rate       |             60% 이상 |
| Optimization Completion Rate |             70% 이상 |
| Calculation Accuracy         |   지원 규칙에서 100% |
| User Satisfaction            | 사용자 테스트로 측정 |

위 수치는 검증된 시장 평균이 아닌 초기 제품 검증 목표다.

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

- [ ] 최소 3개 카드 상품 등록
- [ ] 카드 상품 카탈로그 조회
- [ ] 보유 카드 등록 및 삭제
- [ ] 카드별 전월 실적 입력
- [ ] 결제 업종 및 금액 입력
- [ ] 카드별 예상 할인액 계산
- [ ] 추천 카드 순위 표시
- [ ] 추천 근거 제공
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

### v0 — Card Benefit Calculator

목표: 카드 혜택 계산의 정확성과 사용자 경험 검증.

- 수동 카드 데이터 3~10개
- 전월 실적 분석
- 할인한도 계산
- 단일 결제 기준 카드 비교
- 규칙 기반 추천

### v1 — Card Benefit Optimizer

목표: 실제 소비 패턴을 반영한 혜택 최적화.

- 여러 결제 계획 관리
- 업종별 혜택 계산
- 복수 카드 결제 배분
- 포인트 및 캐시백 환산
- 카드별 소비 패턴 분석
- 상품 데이터 개정 감지

### v2 — Personal Finance Assistant

목표: 개인 소비 패턴에 기반한 지속적인 카드 사용 전략 지원.

- 소비 내역 관리
- 개인화된 카드 사용 전략
- 신규 카드 추천
- 상품설명서 자동 수집 및 변경 감지
- 문서 자동 추출 및 사람의 검수
- 장기적인 혜택 분석

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

Card Benefit Optimizer는 복잡한 신용카드 혜택을 사용자의 소비 의사결정으로 전환하는 서비스다.

카드 상품 데이터를 표준화하고, 사용자가 입력한 전월 실적과 예정된 결제 정보를 분석하여 가장 유리한 결제 카드를 추천한다.

초기에는 검증된 소수의 카드 상품을 기반으로 계산 정확성과 사용자 경험을 확보한다.

이후 실제 소비 패턴 분석, 복수 카드 최적화, 상품 데이터 자동 갱신을 단계적으로 확장한다.

**The goal is not to make users spend more. The goal is to help them get more value from what they already spend.**
