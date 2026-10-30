from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from pydantic import BaseModel, Field

from .schemas import AllocationPlan, CalculationStatus, Card, CardAdvice, TierAnalysis

MAX_CANDIDATE_CARDS = 20


def _current_tier_index(card: Card, recognized_spend: int) -> int | None:
    reached: int | None = None
    for index, tier in enumerate(card.tiers):
        if recognized_spend >= tier.spend_threshold:
            reached = index
        else:
            break
    return reached


def evaluate_card(card: Card, recognized_spend: int) -> CardAdvice:
    if recognized_spend < 0:
        raise ValueError("실적 금액은 0 이상이어야 합니다")

    index = _current_tier_index(card, recognized_spend)
    current_benefit = card.tiers[index].benefit(recognized_spend) if index is not None else 0

    next_index = 0 if index is None else index + 1
    if next_index >= len(card.tiers):
        return CardAdvice(
            card_id=card.card_id,
            name=card.name,
            recognized_spend=recognized_spend,
            current_benefit=current_benefit,
            action="skip",
            reason="top_tier",
        )

    next_tier = card.tiers[next_index]
    gap = next_tier.spend_threshold - recognized_spend

    # 할인율형은 실적 전체에 붙으므로, 넘기는 데 필요한 금액까지만 쓴다고 보고
    # 계산한다. 실제 지출이 더 크면 혜택도 커지므로 이 값은 하한이다.
    next_benefit = next_tier.benefit(next_tier.spend_threshold)
    gain = next_benefit - current_benefit
    gain_is_minimum = next_tier.discount_rate is not None

    if gain <= 0:
        return CardAdvice(
            card_id=card.card_id,
            name=card.name,
            recognized_spend=recognized_spend,
            current_benefit=current_benefit,
            next_threshold=next_tier.spend_threshold,
            next_benefit=next_benefit,
            gap=gap,
            action="skip",
            reason="no_gain",
        )

    return CardAdvice(
        card_id=card.card_id,
        name=card.name,
        recognized_spend=recognized_spend,
        current_benefit=current_benefit,
        next_threshold=next_tier.spend_threshold,
        next_benefit=next_benefit,
        gap=gap,
        incremental_gain=gain,
        gain_is_minimum=gain_is_minimum,
        action="fill",
        reason="reachable",
    )


def _best_selection(gaps: Sequence[int], gains: Sequence[int], budget: int) -> tuple[int, int, int]:
    best_mask = 0
    best_gain = 0
    best_spent = 0
    count = len(gaps)

    for mask in range(1 << count):
        gain = 0
        spent = 0
        for bit in range(count):
            if mask >> bit & 1:
                gain += gains[bit]
                spent += gaps[bit]
        if spent > budget:
            continue
        if gain > best_gain or (gain == best_gain and spent < best_spent):
            best_mask = mask
            best_gain = gain
            best_spent = spent

    return best_mask, best_gain, best_spent


def plan_allocation(
    cards: Sequence[Card],
    spends: Mapping[str, int],
    planned_spend: int,
) -> AllocationPlan:
    if planned_spend < 0:
        raise ValueError("남은 예상 지출은 0 이상이어야 합니다")

    card_ids = [card.card_id for card in cards]
    if len(set(card_ids)) != len(card_ids):
        raise ValueError("카드 ID가 중복되었습니다")

    # 실적을 모르는 카드를 0원으로 계산하면 "채우세요"가 잘못 나온다 (PRD 6.4).
    missing = [card.card_id for card in cards if card.card_id not in spends]
    if missing:
        raise ValueError(f"실적이 입력되지 않은 카드입니다: {', '.join(missing)}")

    advice = [evaluate_card(card, spends[card.card_id]) for card in cards]
    candidates = [item for item in advice if item.action == "fill"]

    if len(candidates) > MAX_CANDIDATE_CARDS:
        raise ValueError(f"한 번에 계산할 수 있는 카드는 {MAX_CANDIDATE_CARDS}장까지입니다")

    gaps = [item.gap or 0 for item in candidates]
    gains = [item.incremental_gain for item in candidates]
    mask, total_gain, usage = _best_selection(gaps, gains, planned_spend)

    chosen = {candidates[bit].card_id for bit in range(len(candidates)) if mask >> bit & 1}

    final: list[CardAdvice] = []
    for item in advice:
        if item.card_id in chosen:
            final.append(item)
            continue
        if item.action == "skip":
            final.append(item)
            continue
        reason = "over_budget" if (item.gap or 0) > planned_spend else "lower_priority"
        final.append(item.model_copy(update={"action": "skip", "reason": reason}))

    return AllocationPlan(
        planned_spend=planned_spend,
        advice=final,
        total_gain=total_gain,
        usage=usage,
        leftover=planned_spend - usage,
    )

class PurchaseEvaluation(BaseModel):
    card_id: str
    name: str
    status: CalculationStatus
    expected_discount: int | None = Field(default=None, ge=0, description="예상 할인액(원). 계산 불가면 None")
    current_tier_threshold: int | None = None
    applied_discount_rate: Decimal | None = None
    remaining_cap: int | None = None
    clause: str
    reason: str

def analyze_card_tier(
    card: Card,
    recognized_spend: int,
    used_discount: int = 0,
) -> TierAnalysis:
    if recognized_spend < 0:
        raise ValueError("실적 금액은 0 이상이어야 합니다")

    index = _current_tier_index(card, recognized_spend)
    
    # 1. 현재 구간 세팅
    current_tier = card.tiers[index] if index is not None else None
    current_threshold = current_tier.spend_threshold if current_tier else 0
    current_cap = current_tier.discount_cap if current_tier else 0
    clause = current_tier.clause if current_tier else (card.tiers[0].clause if card.tiers else "")

    # 2. 다음 구간 세팅
    next_index = 0 if index is None else index + 1
    is_top_tier = next_index >= len(card.tiers)

    if is_top_tier:
        return TierAnalysis(
            card_id=card.card_id,
            name=card.name,
            recognized_spend=recognized_spend,
            current_tier_index=index,
            current_threshold=current_threshold,
            current_discount_cap=current_cap,
            next_tier_index=None,
            next_threshold=None,
            remaining_spend_to_next_tier=0,
            next_discount_cap=None,
            incremental_cap_increase=0,
            is_top_tier=True,
            clause=clause,
        )

    next_tier = card.tiers[next_index]
    remaining_spend = next_tier.spend_threshold - recognized_spend
    
    # 3. 한도 증가량 계산 (한도가 무제한이거나 None인 경우 분기 처리)
    next_cap = next_tier.discount_cap
    if current_cap is not None and next_cap is not None:
        cap_increase = next_cap - current_cap
    else:
        cap_increase = None  # 무제한 한도이거나 산출 불가의 경우

    return TierAnalysis(
        card_id=card.card_id,
        name=card.name,
        recognized_spend=recognized_spend,
        current_tier_index=index,
        current_threshold=current_threshold,
        current_discount_cap=current_cap,
        next_tier_index=next_index,
        next_threshold=next_tier.spend_threshold,
        remaining_spend_to_next_tier=max(0, remaining_spend),
        next_discount_cap=next_cap,
        incremental_cap_increase=cap_increase,
        is_top_tier=False,
        clause=clause,
    )

def evaluate_single_purchase(
    card: Card,
    recognized_spend: int,
    category: str,
    amount: int,
    remaining_cap: int | None = None,
) -> PurchaseEvaluation:
    if amount <= 0:
        raise ValueError("결제 금액은 0보다 커야 합니다")

    index = _current_tier_index(card, recognized_spend)
    if index is None:
        return PurchaseEvaluation(
            card_id=card.card_id,
            name=card.name,
            status="ineligible",
            expected_discount=0,
            clause=card.tiers[0].clause,
            reason="전월 실적 미달로 혜택 구간에 미치지 않습니다.",
        )

    tier = card.tiers[index]
    base = {
        "card_id": card.card_id,
        "name": card.name,
        "current_tier_threshold": tier.spend_threshold,
        "applied_discount_rate": tier.discount_rate,
        "clause": tier.clause,
    }

    if tier.eligible_categories and category not in tier.eligible_categories:
        return PurchaseEvaluation(
            **base,
            status="ineligible",
            expected_discount=0,
            reason=f"결제 업종({category})이 해당 카드의 혜택 적용 대상이 아닙니다.",
        )

    # 구간 고정 한도형은 결제 한 건에 얼마가 붙는지 약관만으로 알 수 없다.
    if tier.discount_rate is None:
        return PurchaseEvaluation(
            **base,
            status="unsupported",
            reason="할인율이 정의되지 않은 한도형 혜택이라 결제 건별 할인액을 계산할 수 없습니다.",
        )

    # PRD 8.4: 잔여 한도를 모르면 전체 한도를 잔여 한도로 간주하지 않는다.
    if tier.discount_cap is not None and remaining_cap is None:
        return PurchaseEvaluation(
            **base,
            status="insufficient_data",
            reason="잔여 할인한도를 입력해야 예상 할인액을 계산할 수 있습니다.",
        )

    theoretical = int(Decimal(amount) * tier.discount_rate)
    cap = None if tier.discount_cap is None else min(remaining_cap, tier.discount_cap)
    return PurchaseEvaluation(
        **base,
        status="eligible",
        expected_discount=theoretical if cap is None else min(theoretical, cap),
        remaining_cap=cap,
        reason="전월 실적 및 업종 조건을 충족하며, 잔여 한도 내에서 할인이 적용됩니다.",
    )


_STATUS_ORDER = {"eligible": 0, "ineligible": 1, "insufficient_data": 2, "unsupported": 3}


def rank_purchase_evaluations(evaluations: Sequence[PurchaseEvaluation]) -> list[PurchaseEvaluation]:
    """PRD 8.6: 계산 가능한 카드를 할인액순으로, 계산 불가 카드는 뒤에 따로 둔다. 동률은 입력 순서 유지."""
    return sorted(evaluations, key=lambda e: (_STATUS_ORDER[e.status], -(e.expected_discount or 0)))
