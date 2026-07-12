"""Acceptance evidence for BE-DDMRP-003, BE-DDMRP-004, BE-DDMRP-005, and BE-DDMRP-007."""

from datetime import datetime, timedelta, timezone

import pytest

from sdbr.ddmrp import (
    DecouplingPoint,
    DemandSignal,
    OpenSupply,
    evaluate_ddmrp_net_flow,
)
from sdbr.planner_view import InventoryBufferPolicy


def test_ddmrp_net_flow_uses_on_hand_supply_and_qualified_demand():
    now = datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc)

    result = evaluate_ddmrp_net_flow(
        decoupling_points=[
            DecouplingPoint(
                item_id="RM-STEEL",
                location_id="MAIN",
                buffer_profile_id="BP-MEDIUM",
                dlt_minutes=1440,
                order_multiple_qty=10,
                minimum_order_qty=20,
            )
        ],
        stock_buffers=[
            InventoryBufferPolicy(
                item_id="RM-STEEL",
                location_id="MAIN",
                on_hand_qty=50,
                red_zone_qty=30,
                yellow_zone_qty=40,
                green_zone_qty=50,
            )
        ],
        demand_signals=[
            DemandSignal("RM-STEEL", "MAIN", 15, now - timedelta(days=1)),
            DemandSignal("RM-STEEL", "MAIN", 20, now.replace(hour=18)),
            DemandSignal(
                "RM-STEEL",
                "MAIN",
                10,
                now + timedelta(hours=12),
                is_qualified_spike=True,
            ),
            DemandSignal("RM-STEEL", "MAIN", 99, now + timedelta(days=7)),
        ],
        open_supply=[
            OpenSupply("RM-STEEL", "MAIN", 25, now + timedelta(hours=2)),
            OpenSupply("RM-STEEL", "MAIN", 60, now + timedelta(days=3)),
        ],
        evaluated_at=now,
    )

    line = result["Lines"][0]
    assert line["QualifiedDemandQty"] == 45
    assert line["QualifiedOpenSupplyQty"] == 25
    assert line["NetFlowPosition"] == 30
    assert line["PlanningStatus"] == "Red"
    assert line["ExecutionStatus"] == "Yellow"
    assert line["SuggestedReplenishmentQty"] == 90
    assert result["Summary"]["ReplenishmentSuggestionCount"] == 1


def test_ddmrp_above_green_does_not_replenish():
    now = datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc)

    result = evaluate_ddmrp_net_flow(
        decoupling_points=[
            DecouplingPoint("RM-RESIN", "MAIN", "BP-LOW", dlt_minutes=480)
        ],
        stock_buffers=[
            InventoryBufferPolicy("RM-RESIN", "MAIN", 150, 20, 40, 60)
        ],
        demand_signals=[],
        open_supply=[],
        evaluated_at=now,
    )

    line = result["Lines"][0]
    assert line["PlanningStatus"] == "AboveGreen"
    assert line["ExecutionStatus"] == "AboveGreen"
    assert line["SuggestedReplenishmentQty"] == 0
    assert line["RecommendedAction"] == "Monitor"


def test_ddmrp_green_zone_does_not_replenish_until_yellow_or_red():
    now = datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc)

    result = evaluate_ddmrp_net_flow(
        decoupling_points=[
            DecouplingPoint(
                "RM-RESIN",
                "MAIN",
                "BP-LOW",
                dlt_minutes=480,
                minimum_order_qty=20,
                order_multiple_qty=10,
            )
        ],
        stock_buffers=[
            InventoryBufferPolicy("RM-RESIN", "MAIN", 130, 50, 50, 100)
        ],
        demand_signals=[],
        open_supply=[],
        evaluated_at=now,
    )

    line = result["Lines"][0]
    assert line["PlanningStatus"] == "Green"
    assert line["SuggestedReplenishmentQty"] == 0
    assert line["RecommendedAction"] == "Monitor"
    assert result["Summary"]["ReplenishmentSuggestionCount"] == 0


def test_ddmrp_missing_stock_buffer_reports_structured_issue():
    now = datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc)

    result = evaluate_ddmrp_net_flow(
        decoupling_points=[
            DecouplingPoint("RM-COPPER", "MAIN", "BP-HIGH", dlt_minutes=1440)
        ],
        stock_buffers=[],
        demand_signals=[],
        open_supply=[],
        evaluated_at=now,
    )

    assert result["Lines"] == []
    assert result["Summary"]["MissingDataCount"] == 1
    assert result["Issues"][0]["Code"] == "STOCK_BUFFER_MISSING"


def test_ddmrp_rejects_naive_evaluation_time():
    with pytest.raises(ValueError):
        evaluate_ddmrp_net_flow(
            decoupling_points=[],
            stock_buffers=[],
            demand_signals=[],
            open_supply=[],
            evaluated_at=datetime(2026, 6, 25, 9, 0),
        )
