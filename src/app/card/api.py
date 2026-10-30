"""HTTP surface for the card allocation calculator.

Two endpoints only. The product list feeds the picker, and the plan endpoint
answers the one question the screen asks. No state is stored: the same request
always returns the same plan.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .calculator import plan_allocation
from .catalog import Catalog, load_catalog
from .schemas import AllocationPlan

router = APIRouter()

MAX_PLANNED_SPEND = 100_000_000


class PlanRequest(BaseModel):
    spends: dict[str, int] = Field(default_factory=dict, description="카드 ID별 이번 달 실적 인정 금액")
    planned_spend: int = Field(ge=0, le=MAX_PLANNED_SPEND, description="이번 달 남은 예상 지출")

    @field_validator("spends")
    @classmethod
    def _check_spends(cls, spends: dict[str, int]) -> dict[str, int]:
        for card_id, amount in spends.items():
            if amount < 0:
                raise ValueError(f"실적 금액은 0 이상이어야 합니다: {card_id}")
        return spends


@router.get("/products", response_model=Catalog)
def list_products() -> Catalog:
    return load_catalog()


@router.post("/plan", response_model=AllocationPlan)
def create_plan(request: PlanRequest) -> AllocationPlan:
    catalog = load_catalog()

    unknown = sorted(set(request.spends) - {card.card_id for card in catalog.cards})
    if unknown:
        raise HTTPException(status_code=400, detail=f"카탈로그에 없는 카드입니다: {', '.join(unknown)}")

    try:
        return plan_allocation(catalog.cards, request.spends, request.planned_spend)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
