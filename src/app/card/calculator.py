from __future__ import annotations

from collections.abc import Mapping, Sequence
from pydantic import BaseModel, Field
from decimal import Decimal

from .schemas import AllocationPlan, CalculationStatus, Card, CardAdvice

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

    advice = [evaluate_card(card, spends.get(card.card_id, 0)) for card in cards]
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
    expected_discount: int = Field(ge=0, description="예상 할인액(원)")
    current_tier_threshold: int | None = None
    applied_discount_rate: Decimal | None = None
    remaining_cap: int | None = None
    clause: str
    reason: str

def evaluate_single_purchase(
    card: Card,
    recognized_spend: int,
    category: str,
    amount: int,
    remaining_cap: int | None = None,
) -> PurchaseEvaluation:
    if amount <= 0:
        raise ValueError("결제 금액은 0보다 커야 합니다")
    
    # 1. 전월 실적 구간 확인
    index = _current_tier_index(card, recognized_spend)
    if index is None:
        return PurchaseEvaluation(
            card_id=card.card_id,
            name=card.name,
            status="ineligible",
            expected_discount=0,
            clause=card.tiers[0].clause if card.tiers else "",
            reason="전월 실적 미달로 혜택 구간에 미치지 않습니다.",
        )

    tier = card.tiers[index]

    # 2. 업종 적격성 확인 (지정된 업종이 있고 해당 업종에 포함되지 않으면 제외)
    if tier.eligible_categories and category not in tier.eligible_categories:
        return PurchaseEvaluation(
            card_id=card.card_id,
            name=card.name,
            status="ineligible",
            expected_discount=0,
            current_tier_threshold=tier.spend_threshold,
            clause=tier.clause,
            reason=f"결제 업종({category})이 해당 카드의 혜택 적용 대상이 아닙니다.",
        )
    
    # 3. 할인액 계산
    if tier.discount_rate is None:
        # 정액/고정 한도형인 경우 (단일 결제 할인 적용 방식에 따라 다름)
        theoretical = tier.discount_cap or 0
    else:
        theoretical = int(Decimal(amount) * tier.discount_rate)
    
    # 4. 할인한도 제한 적용
    cap_limit = remaining_cap if remaining_cap is not None else tier.discount_cap
    expected_discount = theoretical if cap_limit is None else min(theoretical, cap_limit)

    return PurchaseEvaluation(
        card_id=card.card_id,
        name=card.name,
        status="eligible",
        expected_discount=max(0, expected_discount),
        current_tier_threshold=tier.spend_threshold,
        applied_discount_rate=tier.discount_rate,
        remaining_cap=cap_limit,
        clause=tier.clause,
        reason="조건을 충족하여 예상 할인이 적용됩니다.",
    )
    

