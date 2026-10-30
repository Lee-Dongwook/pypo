"""HTTP surface for the card allocation calculator.

Two endpoints only. The product list feeds the picker, and the plan endpoint
answers the one question the screen asks. No state is stored: the same request
always returns the same plan.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .calculator import (
    PurchaseEvaluation,
    analyze_card_tier,
    evaluate_single_purchase,
    plan_allocation,
    rank_purchase_evaluations,
)
from .catalog import Catalog, load_catalog
from .schemas import AllocationPlan, TierAnalysis

router = APIRouter()

MAX_PLANNED_SPEND = 100_000_000


def _check_amounts(amounts: dict[str, int]) -> dict[str, int]:
    for card_id, amount in amounts.items():
        if amount < 0:
            raise ValueError(f"금액은 0 이상이어야 합니다: {card_id}")
    return amounts


def _require_known(catalog: Catalog, card_ids: set[str]) -> None:
    unknown = sorted(card_ids - {card.card_id for card in catalog.cards})
    if unknown:
        raise HTTPException(status_code=400, detail=f"카탈로그에 없는 카드입니다: {', '.join(unknown)}")


class PlanRequest(BaseModel):
    spends: dict[str, int] = Field(default_factory=dict, description="카드 ID별 이번 달 실적 인정 금액")
    planned_spend: int = Field(ge=0, le=MAX_PLANNED_SPEND, description="이번 달 남은 예상 지출")

    _check_spends = field_validator("spends")(_check_amounts)


@router.get("/products", response_model=Catalog)
def list_products() -> Catalog:
    return load_catalog()


@router.post("/plan", response_model=AllocationPlan)
def create_plan(request: PlanRequest) -> AllocationPlan:
    catalog = load_catalog()

    _require_known(catalog, set(request.spends))

    try:
        return plan_allocation(catalog.cards, request.spends, request.planned_spend)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


class OptimizePurchaseRequest(BaseModel):
    spends: dict[str, int] = Field(default_factory=dict, description="카드 ID별 전월 인정 실적")
    remaining_caps: dict[str, int] = Field(default_factory=dict, description="카드 ID별 잔여 할인한도 (선택)")
    category: str = Field(min_length=1, description="결제 예정 업종")
    amount: int = Field(gt=0, le=MAX_PLANNED_SPEND, description="결제 예정 금액")

    _check_amounts = field_validator("spends", "remaining_caps")(_check_amounts)

class OptimizePurchaseResponse(BaseModel):
    category: str
    amount: int
    recommendations: list[PurchaseEvaluation]

@router.post("/optimize", response_model=OptimizePurchaseResponse)
def optimize_purchase(request: OptimizePurchaseRequest) -> OptimizePurchaseResponse:
    catalog = load_catalog()
    _require_known(catalog, set(request.spends) | set(request.remaining_caps))

    evaluations = [
        evaluate_single_purchase(
            card=catalog.find(card_id),
            recognized_spend=recognized_spend,
            category=request.category,
            amount=request.amount,
            remaining_cap=request.remaining_caps.get(card_id),
        )
        for card_id, recognized_spend in request.spends.items()
    ]

    return OptimizePurchaseResponse(
        category=request.category,
        amount=request.amount,
        recommendations=rank_purchase_evaluations(evaluations),
    )


class TierAnalysisRequest(BaseModel):
    spends: dict[str, int] = Field(default_factory=dict, description="카드 ID별 전월 인정 실적")

    _check_spends = field_validator("spends")(_check_amounts)


class TierAnalysisResponse(BaseModel):
    analyses: list[TierAnalysis]

@router.post("/tier-analysis", response_model=TierAnalysisResponse)
def analyze_tiers(request: TierAnalysisRequest) -> TierAnalysisResponse:
    catalog = load_catalog()
    _require_known(catalog, set(request.spends))
    return TierAnalysisResponse(
        analyses=[analyze_card_tier(catalog.find(card_id), spend) for card_id, spend in request.spends.items()]
    )
