import json

import pytest
from fastapi.testclient import TestClient

from main import app
from src.app.card.catalog import _load

client = TestClient(app)


def test_products_come_from_the_curated_catalog() -> None:
    response = client.get("/card/products")

    assert response.status_code == 200
    body = response.json()
    assert body["as_of"] == "2026-10-30"
    assert len(body["cards"]) == 3
    assert {card["card_id"] for card in body["cards"]} == {"example-a", "example-b", "example-c"}
    assert all(tier["clause"] for card in body["cards"] for tier in card["tiers"])


def test_plan_picks_the_card_with_the_larger_incremental_cap() -> None:
    response = client.post(
        "/card/plan",
        json={"spends": {"example-a": 300_000, "example-b": 300_000}, "planned_spend": 400_000},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_gain"] == 15_000
    assert body["usage"] == 300_000
    assert body["leftover"] == 100_000
    assert [item["card_id"] for item in body["advice"] if item["action"] == "fill"] == ["example-b"]


def test_plan_covers_only_cards_with_entered_spend() -> None:
    response = client.post("/card/plan", json={"spends": {"example-b": 0}, "planned_spend": 100_000})

    assert response.status_code == 200
    assert [item["card_id"] for item in response.json()["advice"]] == ["example-b"]


def test_plan_needs_at_least_one_card() -> None:
    response = client.post("/card/plan", json={"spends": {}, "planned_spend": 100_000})

    assert response.status_code == 400


def test_plan_reports_unaffordable_card_as_hold_off() -> None:
    response = client.post("/card/plan", json={"spends": {"example-a": 0}, "planned_spend": 100_000})

    assert response.status_code == 200
    body = response.json()
    assert body["advice"][0]["reason"] == "over_budget"
    assert body["total_gain"] == 0


def test_unknown_card_is_rejected() -> None:
    response = client.post("/card/plan", json={"spends": {"nope": 300_000}, "planned_spend": 300_000})

    assert response.status_code == 400
    assert "nope" in response.json()["detail"]


def test_negative_spend_is_rejected() -> None:
    response = client.post("/card/plan", json={"spends": {"example-a": -1}, "planned_spend": 300_000})

    assert response.status_code == 422


def test_catalog_path_can_be_overridden(tmp_path, monkeypatch) -> None:
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "as_of": "2026-11-01",
                "cards": [
                    {
                        "card_id": "only",
                        "name": "테스트 카드",
                        "issuer": "테스트",
                        "as_of": "2026-11-01",
                        "tiers": [{"spend_threshold": 100_000, "discount_cap": 5_000, "clause": "설명서 1쪽"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CARD_CATALOG_PATH", str(catalog_file))
    _load.cache_clear()

    response = client.get("/card/products")

    assert response.status_code == 200
    assert [card["card_id"] for card in response.json()["cards"]] == ["only"]

    monkeypatch.delenv("CARD_CATALOG_PATH")
    _load.cache_clear()


def test_missing_catalog_file_raises_a_clear_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CARD_CATALOG_PATH", str(tmp_path / "missing.json"))
    _load.cache_clear()

    with pytest.raises(FileNotFoundError, match="카드 카탈로그"):
        client.get("/card/products")

    monkeypatch.delenv("CARD_CATALOG_PATH")
    _load.cache_clear()


@pytest.mark.parametrize("path", ["/card/optimize", "/card/tier-analysis"])
def test_unknown_card_is_rejected_everywhere(path: str) -> None:
    response = client.post(path, json={"spends": {"nope": 1}, "category": "cafe", "amount": 1_000})

    assert response.status_code == 400


def test_negative_remaining_cap_is_rejected() -> None:
    response = client.post(
        "/card/optimize",
        json={"spends": {"example-a": 1}, "remaining_caps": {"example-a": -1}, "category": "cafe", "amount": 1_000},
    )

    assert response.status_code == 422


def test_tier_analysis_api_reports_gap_to_next_tier():
    response = client.post(
        "/card/tier-analysis",
        json={"spends": {"example-a": 300_000}},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["analyses"]) == 1
    analysis = body["analyses"][0]
    assert analysis["next_threshold"] == 500_000
    assert analysis["remaining_spend_to_next_tier"] == 200_000
    assert analysis["incremental_cap_increase"] == 5_000


def test_tier_analysis_api_marks_top_tier():
    response = client.post(
        "/card/tier-analysis",
        json={"spends": {"example-a": 1_000_000}},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["analyses"]) == 1
    analysis = body["analyses"][0]
    assert analysis["is_top_tier"] is True


def test_tier_analysis_api_rejects_negative_spend():
    response = client.post(
        "/card/tier-analysis",
        json={"spends": {"example-a": -1}},
    )

    assert response.status_code == 422


def test_spend_over_one_hundred_million_is_rejected() -> None:
    response = client.post("/card/plan", json={"spends": {"example-a": 100_000_001}, "planned_spend": 0})

    assert response.status_code == 422
    assert "금액은 1억 원 이하여야 합니다: example-a" in response.text


def test_spend_of_exactly_one_hundred_million_is_accepted() -> None:
    response = client.post("/card/plan", json={"spends": {"example-a": 100_000_000}, "planned_spend": 0})

    assert response.status_code == 200
