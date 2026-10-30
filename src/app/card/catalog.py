"""Curated card catalog for the v0 calculator.

Card terms are hand-curated, so the catalog is a versioned JSON file rather
than a table. Override the path with `CARD_CATALOG_PATH` to point at a newer
curation without touching code. Every tier in the file carries its clause, and
the model rejects a tier that does not.
"""

from __future__ import annotations

import json
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from .schemas import Card

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[3] / "samples" / "card_products.v0.json"


class Catalog(BaseModel):
    """A curated card set with the date its terms were checked."""

    as_of: date
    note: str = ""
    cards: list[Card] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Catalog:
        ids = [card.card_id for card in self.cards]
        if len(set(ids)) != len(ids):
            raise ValueError("카드 ID가 중복되었습니다")
        return self

    def find(self, card_id: str) -> Card | None:
        return next((card for card in self.cards if card.card_id == card_id), None)


@lru_cache(maxsize=4)
def _load(path: str) -> Catalog:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"카드 카탈로그를 찾을 수 없습니다: {file}")
    return Catalog.model_validate(json.loads(file.read_text(encoding="utf-8")))


def load_catalog(path: str | Path | None = None) -> Catalog:
    """Load the curated catalog, defaulting to the bundled v0 sample."""
    selected = str(Path(path or os.getenv("CARD_CATALOG_PATH") or DEFAULT_CATALOG_PATH).resolve())
    return _load(selected)
