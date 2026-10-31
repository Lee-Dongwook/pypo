import pytest
from pydantic import ValidationError

from src.app.card.calculator import (
    analyze_card_tier,
    evaluate_card,
    evaluate_single_purchase,
    plan_allocation,
    rank_purchase_evaluations,
)
from src.app.card.schemas import Card, Tier


def make_card(
    card_id: str = "c1",
    tiers: list[tuple[int, int]] | None = None,
    name: str = "테스트 카드",
) -> Card:
    rows = tiers or [(300_000, 15_000), (500_000, 20_000), (1_000_000, 30_000)]
    return Card(
        card_id=card_id,
        name=name,
        issuer="테스트",
        tiers=[Tier(spend_threshold=t, discount_cap=c, clause=f"상품설명서 {t}원 구간") for t, c in rows],
        as_of="2026-10-30",
    )


def test_below_first_tier_targets_the_first_threshold() -> None:
    advice = evaluate_card(make_card(), 0)

    assert advice.current_benefit == 0
    assert advice.next_threshold == 300_000
    assert advice.gap == 300_000
    assert advice.incremental_gain == 15_000
    assert advice.action == "fill"


def test_exactly_at_threshold_moves_to_the_next_gap() -> None:
    advice = evaluate_card(make_card(), 300_000)

    assert advice.current_benefit == 15_000
    assert advice.gap == 200_000
    assert advice.incremental_gain == 5_000


def test_top_tier_needs_no_action() -> None:
    advice = evaluate_card(make_card(), 1_000_000)

    assert advice.action == "skip"
    assert advice.reason == "top_tier"
    assert advice.gap is None
    assert advice.incremental_gain == 0


def test_flat_cap_between_tiers_is_not_worth_filling() -> None:
    card = make_card(tiers=[(300_000, 15_000), (600_000, 15_000)])

    advice = evaluate_card(card, 350_000)

    assert advice.gap == 250_000
    assert advice.incremental_gain == 0
    assert advice.reason == "no_gain"


def test_budget_goes_to_the_larger_gain() -> None:
    cards = [
        make_card("a", tiers=[(300_000, 15_000), (500_000, 20_000)]),
        make_card("b", tiers=[(300_000, 15_000), (600_000, 30_000)]),
    ]
    spends = {"a": 300_000, "b": 300_000}

    plan = plan_allocation(cards, spends, planned_spend=400_000)

    assert plan.total_gain == 15_000
    assert plan.usage == 300_000
    assert plan.leftover == 100_000
    assert [item.card_id for item in plan.fill] == ["b"]
    by_id = {item.card_id: item for item in plan.advice}
    assert by_id["a"].reason == "lower_priority"


def test_both_cards_filled_when_budget_covers_both() -> None:
    cards = [
        make_card("a", tiers=[(300_000, 15_000), (500_000, 20_000)]),
        make_card("b", tiers=[(300_000, 15_000), (600_000, 30_000)]),
    ]

    plan = plan_allocation(cards, {"a": 300_000, "b": 300_000}, planned_spend=500_000)

    assert len(plan.fill) == 2
    assert plan.total_gain == 20_000
    assert plan.usage == 500_000
    assert plan.leftover == 0


def test_unaffordable_card_is_held_off_not_recommended() -> None:
    cards = [make_card("a")]

    plan = plan_allocation(cards, {"a": 0}, planned_spend=100_000)

    assert plan.fill == []
    assert [item.card_id for item in plan.hold_off] == ["a"]
    assert plan.total_gain == 0


def test_cheaper_combination_wins_a_tie() -> None:
    cards = [
        make_card("far", tiers=[(60_000, 5_000)]),
        make_card("near", tiers=[(50_000, 5_000)]),
    ]

    plan = plan_allocation(cards, {"far": 0, "near": 0}, planned_spend=60_000)

    assert [item.card_id for item in plan.fill] == ["near"]
    assert plan.total_gain == 5_000
    assert plan.leftover == 10_000


def test_missing_spend_is_rejected_not_treated_as_zero() -> None:
    with pytest.raises(ValueError, match="실적이 입력되지 않은"):
        plan_allocation([make_card("a")], {}, planned_spend=300_000)


def test_zero_budget_fills_nothing() -> None:
    plan = plan_allocation([make_card("a")], {"a": 100_000}, planned_spend=0)

    assert plan.fill == []
    assert plan.total_gain == 0
    assert plan.leftover == 0


def test_duplicate_card_ids_are_rejected() -> None:
    cards = [make_card("c1"), make_card("c1")]

    with pytest.raises(ValueError, match="중복"):
        plan_allocation(cards, {}, planned_spend=0)


def test_tiers_must_be_sorted() -> None:
    with pytest.raises(ValidationError, match="오름차순"):
        make_card(tiers=[(500_000, 20_000), (300_000, 15_000)])


def test_discount_cap_cannot_shrink() -> None:
    with pytest.raises(ValidationError, match="줄어들"):
        make_card(tiers=[(300_000, 20_000), (500_000, 15_000)])


def test_tier_without_clause_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Tier(spend_threshold=300_000, discount_cap=15_000, clause="")



def make_rate_card(card_id: str = "r1", rate: str = "0.1", cap: int | None = 10_000) -> Card:
    return Card(
        card_id=card_id,
        name="할인율 카드",
        issuer="테스트",
        tiers=[Tier(spend_threshold=300_000, discount_rate=rate, discount_cap=cap, clause="상품설명서 30만 원 구간")],
        as_of="2026-10-30",
    )


def test_purchase_discount_is_capped_by_remaining_cap() -> None:
    result = evaluate_single_purchase(make_rate_card(), 300_000, "cafe", 50_000, remaining_cap=3_000)

    assert result.status == "eligible"
    assert result.expected_discount == 3_000


def test_remaining_cap_cannot_exceed_tier_cap() -> None:
    result = evaluate_single_purchase(make_rate_card(), 300_000, "cafe", 500_000, remaining_cap=99_999)

    assert result.expected_discount == 10_000


def test_unknown_remaining_cap_is_insufficient_data() -> None:
    result = evaluate_single_purchase(make_rate_card(), 300_000, "cafe", 50_000)

    assert result.status == "insufficient_data"
    assert result.expected_discount is None


def test_unlimited_cap_needs_no_remaining_cap() -> None:
    result = evaluate_single_purchase(make_rate_card(cap=None), 300_000, "cafe", 50_000)

    assert result.status == "eligible"
    assert result.expected_discount == 5_000


def test_cap_only_tier_is_unsupported_for_single_purchase() -> None:
    result = evaluate_single_purchase(make_card(), 300_000, "cafe", 1_000, remaining_cap=15_000)

    assert result.status == "unsupported"
    assert result.expected_discount is None


def test_below_first_tier_is_ineligible() -> None:
    result = evaluate_single_purchase(make_rate_card(), 299_999, "cafe", 50_000, remaining_cap=10_000)

    assert result.status == "ineligible"
    assert result.expected_discount == 0


def test_ranking_puts_uncomputable_cards_last() -> None:
    evaluations = [
        evaluate_single_purchase(make_card("flat"), 300_000, "cafe", 50_000),
        evaluate_single_purchase(make_rate_card("low", rate="0.01"), 300_000, "cafe", 50_000, remaining_cap=10_000),
        evaluate_single_purchase(make_rate_card("none"), 0, "cafe", 50_000),
        evaluate_single_purchase(make_rate_card("high"), 300_000, "cafe", 50_000, remaining_cap=10_000),
    ]

    ranked = [e.card_id for e in rank_purchase_evaluations(evaluations)]

    assert ranked == ["high", "low", "none", "flat"]


def test_tier_analysis_at_zero_spend_targets_first_threshold():
    card = make_card()
    result = analyze_card_tier(card, 0)

    assert result.current_tier_index is None
    assert result.next_threshold == 300_000
    assert result.remaining_spend_to_next_tier == 300_000


def test_tier_analysis_exactly_at_threshold_moves_to_next():
    card = make_card()
    result = analyze_card_tier(card, 300_000)

    assert result.current_tier_index == 0
    assert result.next_threshold == 500_000
    assert result.incremental_cap_increase == 5_000


def test_tier_analysis_at_top_tier_has_no_next():
    card = make_card()
    result = analyze_card_tier(card, 1_000_000)

    assert result.is_top_tier is True
    assert result.next_threshold is None
    assert result.remaining_spend_to_next_tier == 0


def test_tier_analysis_rejects_negative_spend():
    card = make_card()
    with pytest.raises(ValueError, match="실적 금액은 0 이상이어야 합니다"):
        analyze_card_tier(card, -1)
