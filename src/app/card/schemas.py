from __future__ import annotations

from datetime import date
from decimal import Decimal
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

CalculationStatus = Literal["eligible", "ineligible", "insufficient_data", "unsupported"]

class Tier(BaseModel):
    model_config = ConfigDict(frozen=True)

    spend_threshold: int = Field(ge=0, description="이 구간에 들어가는 전월 실적 기준 금액(원)")
    discount_rate: Decimal | None = Field(
        default=None,
        gt=0,
        le=1,
        description="실적 인정 금액에 적용되는 할인율(0~1). 없으면 구간 고정 한도형",
    )
    discount_cap: int | None = Field(
        default=None,
        ge=0,
        description="이 구간의 월 할인한도(원). None이면 한도 없음",
    )
    eligible_categories: list[str] = Field(default_factory=list, description="혜택 적용 업종 목록 (비어있으면 전 업종)")
    clause: str = Field(min_length=1, description="상품설명서 조항 또는 약관 근거")

    @model_validator(mode="after")
    def _check_reward(self) -> Tier:
        if self.discount_rate is None and self.discount_cap is None:
            raise ValueError("할인율과 할인한도 중 하나는 있어야 합니다")
        return self

    def benefit(self, spend: int) -> int:
        """What this tier pays for a given recognized spend."""
        if self.discount_rate is None:
            return self.discount_cap or 0
        gross = int(Decimal(spend) * self.discount_rate)
        return gross if self.discount_cap is None else min(gross, self.discount_cap)

    @property
    def unlimited(self) -> bool:
        """True when the issuer states no monthly ceiling."""
        return self.discount_rate is not None and self.discount_cap is None

    def nominal_benefit(self) -> int:
        """Benefit at the tier's own threshold, used to order tiers."""
        return self.benefit(self.spend_threshold)


class Card(BaseModel):
    model_config = ConfigDict(frozen=True)

    card_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    tiers: list[Tier] = Field(min_length=1)
    as_of: date = Field(description="약관 확인 기준일")
    excluded_spend_note: str = Field(default="", description="실적에서 빠지는 항목 안내")
    source_url: str | None = Field(default=None, description="상품설명서 원문 주소")

    @model_validator(mode="after")
    def _check_tiers(self) -> Card:
        thresholds = [tier.spend_threshold for tier in self.tiers]
        if len(set(thresholds)) != len(thresholds) or thresholds != sorted(thresholds):
            raise ValueError("구간 기준 금액은 중복 없이 오름차순이어야 합니다")

        benefits = [tier.nominal_benefit() for tier in self.tiers]
        if benefits != sorted(benefits):
            raise ValueError("구간이 올라갈수록 혜택이 줄어들 수 없습니다")
        return self


class CardAdvice(BaseModel):
    card_id: str
    name: str
    recognized_spend: int = Field(ge=0, description="이번 달 실적 인정 금액(원)")
    current_benefit: int = Field(ge=0, description="현재 구간에서 받는 혜택(원)")
    next_threshold: int | None = Field(default=None, description="다음 구간 기준 금액(원)")
    next_benefit: int | None = Field(default=None, ge=0, description="다음 구간에서 받는 혜택(원)")
    gap: int | None = Field(default=None, ge=0, description="다음 구간까지 남은 금액(원)")
    incremental_gain: int = Field(default=0, ge=0, description="다음 구간에서 늘어나는 혜택(원)")
    gain_is_minimum: bool = Field(
        default=False,
        description="혜택이 할인율 기반이라 실제 금액이 이 값보다 클 수 있음",
    )
    action: AdviceAction
    reason: AdviceReason


class AllocationPlan(BaseModel):
    planned_spend: int = Field(ge=0, description="이번 달 남은 예상 지출(원)")
    advice: list[CardAdvice]
    total_gain: int = Field(default=0, ge=0, description="배분으로 늘어나는 혜택 합계(원)")
    usage: int = Field(default=0, ge=0, description="배분에 쓴 금액(원)")
    leftover: int = Field(default=0, ge=0, description="배분하고 남은 금액(원)")

    @property
    def fill(self) -> list[CardAdvice]:
        return [item for item in self.advice if item.action == "fill"]

    @property
    def hold_off(self) -> list[CardAdvice]:
        """Cards with a real gain that this month's budget cannot cover."""
        return [item for item in self.advice if item.action == "skip" and item.reason == "over_budget"]
