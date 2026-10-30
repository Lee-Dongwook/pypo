"""Models for the v0 card benefit allocation calculator.

The calculator only reads what a product disclosure states: monthly spend
tiers, the integrated discount cap for each tier, and the note about spend
that does not count. Card data is curated by hand, so every tier keeps the
clause it came from. A tier without a clause cannot be constructed.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AdviceAction = Literal["fill", "skip"]

AdviceReason = Literal[
    "reachable",
    "over_budget",
    "lower_priority",
    "no_gain",
    "top_tier",
]


class Tier(BaseModel):
    """One monthly spend tier of a card product."""

    model_config = ConfigDict(frozen=True)

    spend_threshold: int = Field(ge=0, description="이 구간에 들어가는 전월 실적 기준 금액(원)")
    discount_cap: int = Field(ge=0, description="이 구간의 통합 할인한도(원)")
    clause: str = Field(min_length=1, description="상품설명서 조항 또는 약관 근거")


class Card(BaseModel):
    """A card product and its monthly spend tiers."""

    model_config = ConfigDict(frozen=True)

    card_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    tiers: list[Tier] = Field(min_length=1)
    as_of: date = Field(description="약관 확인 기준일")
    excluded_spend_note: str = Field(default="", description="실적에서 빠지는 항목 안내")

    @model_validator(mode="after")
    def _check_tiers(self) -> Card:
        thresholds = [tier.spend_threshold for tier in self.tiers]
        if len(set(thresholds)) != len(thresholds) or thresholds != sorted(thresholds):
            raise ValueError("구간 기준 금액은 중복 없이 오름차순이어야 합니다")

        caps = [tier.discount_cap for tier in self.tiers]
        if caps != sorted(caps):
            raise ValueError("할인한도는 구간이 올라갈수록 줄어들 수 없습니다")
        return self


class CardAdvice(BaseModel):
    """What to do with one card for the rest of this month."""

    card_id: str
    name: str
    recognized_spend: int = Field(ge=0, description="이번 달 실적 인정 금액(원)")
    current_cap: int = Field(ge=0, description="현재 구간의 통합 할인한도(원)")
    next_threshold: int | None = Field(default=None, description="다음 구간 기준 금액(원)")
    gap: int | None = Field(default=None, ge=0, description="다음 구간까지 남은 금액(원)")
    incremental_cap: int = Field(default=0, ge=0, description="다음 구간에서 늘어나는 한도(원)")
    action: AdviceAction
    reason: AdviceReason


class AllocationPlan(BaseModel):
    """The allocation result shown on the single result screen."""

    planned_spend: int = Field(ge=0, description="이번 달 남은 예상 지출(원)")
    advice: list[CardAdvice]
    total_gain: int = Field(default=0, ge=0, description="배분으로 늘어나는 한도 합계(원)")
    usage: int = Field(default=0, ge=0, description="배분에 쓴 금액(원)")
    leftover: int = Field(default=0, ge=0, description="배분하고 남은 금액(원)")

    @property
    def fill(self) -> list[CardAdvice]:
        return [item for item in self.advice if item.action == "fill"]

    @property
    def hold_off(self) -> list[CardAdvice]:
        """Cards with a real gain that this month's budget cannot cover."""
        return [item for item in self.advice if item.action == "skip" and item.reason == "over_budget"]
