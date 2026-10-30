"""Deterministic allocation of the rest of this month's card spend.

The question the calculator answers is narrow on purpose:

    "남은 지출을 어느 카드에 몰아야 이번 달 구간을 넘기고, 넘기면 얼마가 느는가?"

There is no model here. Given the tiers from a product disclosure and the
amount the user already spent, the answer is a small subset-sum problem over
at most a handful of cards, so we solve it exactly instead of approximating.
Every number in the result traces back to a tier that carries its clause.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .schemas import AllocationPlan, Card, CardAdvice

MAX_CANDIDATE_CARDS = 20


def _current_tier_index(card: Card, recognized_spend: int) -> int | None:
    """Index of the highest tier the spend already reaches, or None below the first."""
    reached: int | None = None
    for index, tier in enumerate(card.tiers):
        if recognized_spend >= tier.spend_threshold:
            reached = index
        else:
            break
    return reached


def evaluate_card(card: Card, recognized_spend: int) -> CardAdvice:
    """Evaluate one card. The returned action is provisional until the budget is known."""
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
    """Exact subset search.

    Returns (mask, gain, spent). Ties prefer the cheaper combination, because
    unspent budget stays with the user.
    """
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
    """Decide which cards to fill with the remaining planned spend.

    A card is filled only when the spend is already planned. The calculator never
    suggests spending extra money to reach a tier, so a card that is individually
    unaffordable is reported as `hold_off` instead of a recommendation.
    """
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
