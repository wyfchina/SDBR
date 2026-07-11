"""Acceptance evidence for BE-SDBR-006 and BE-SDBR-010 MTO identity."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import inf, nan

import pytest

from sdbr.order_commitment_evaluation import (
    REFERENCE_CCR_PROTECTION_POLICY,
    CcrProtectionPolicy,
    OrderCommitmentConflict,
    candidate_demand_commitment_id,
    normalize_mto_order,
    normalized_policy_dict,
)


def _mto_order() -> dict[str, object]:
    return {
        "SourceSystem": "MockERP",
        "SourceObjectType": "CustomerOrder",
        "OrderID": "SO-100",
        "OrderVersion": "2",
        "DemandLineID": "10",
        "ProductID": "FG-1",
        "LocationID": "MAIN",
        "Quantity": 10,
        "Uom": "EA",
        "RequestedDueAt": datetime(
            2026,
            7,
            21,
            2,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        "BusinessPriority": 25,
        "ReceivedAt": datetime(
            2026,
            7,
            12,
            16,
            30,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        "TraceID": "TRACE-SO-100-10-V2",
        "BaselinePlanningRunID": "RUN-BASELINE-1",
        "RoutingID": "ROUTE-FG-1",
        "MaterialRequirements": [
            {
                "RequirementLineID": "20",
                "ItemID": "RM-2",
                "LocationID": "MAIN",
                "RequiredQty": 4,
                "Uom": "EA",
            },
            {
                "RequirementLineID": "10",
                "ItemID": "RM-1",
                "LocationID": "MAIN",
                "RequiredQty": 2,
                "Uom": "EA",
            },
        ],
    }


class TestMtoOrderAndProtectionPolicy:
    def test_normalize_mto_order_derives_stable_versioned_and_logical_identity(
        self,
    ):
        order = normalize_mto_order(_mto_order())
        replay = normalize_mto_order(_mto_order())
        next_version = _mto_order()
        next_version["OrderVersion"] = "3"
        next_version["ReceivedAt"] = datetime(
            2026, 7, 12, 8, 31, tzinfo=timezone.utc
        )
        successor = normalize_mto_order(next_version)

        assert order["OrderKey"] == replay["OrderKey"]
        assert order["LogicalOrderKey"] == successor["LogicalOrderKey"]
        assert order["OrderKey"] != successor["OrderKey"]
        assert order["OrderVersionRank"] == [
            "2026-07-12T08:30:00+00:00",
            "2",
        ]
        assert order["RequestedDueAt"] == "2026-07-20T18:00:00+00:00"
        assert order["PlanningOrderID"] == "SO-100:10"
        assert candidate_demand_commitment_id(order).startswith("DC-")

    def test_order_fingerprint_covers_sorted_material_requirements_but_not_evaluation_time(
        self,
    ):
        source = _mto_order()
        original = deepcopy(source)
        first = normalize_mto_order(source)
        reordered = _mto_order()
        reordered["MaterialRequirements"] = list(
            reversed(reordered["MaterialRequirements"])
        )
        second = normalize_mto_order(reordered)

        assert source == original
        assert [
            row["RequirementLineID"]
            for row in first["MaterialRequirements"]
        ] == ["10", "20"]
        assert first["OrderContentFingerprint"] == second[
            "OrderContentFingerprint"
        ]
        assert "EvaluatedAt" not in first

    def test_order_rejects_blank_identity_naive_times_duplicate_requirements_and_nonfinite_quantity(
        self,
    ):
        invalid_orders: list[dict[str, object]] = []

        blank_identity = _mto_order()
        blank_identity["OrderID"] = "  "
        invalid_orders.append(blank_identity)

        naive_requested = _mto_order()
        naive_requested["RequestedDueAt"] = datetime(2026, 7, 20, 18)
        invalid_orders.append(naive_requested)

        naive_received = _mto_order()
        naive_received["ReceivedAt"] = datetime(2026, 7, 12, 8, 30)
        invalid_orders.append(naive_received)

        duplicate_requirement = _mto_order()
        requirements = duplicate_requirement["MaterialRequirements"]
        assert isinstance(requirements, list)
        requirements.append(deepcopy(requirements[0]))
        invalid_orders.append(duplicate_requirement)

        for quantity in (nan, inf):
            nonfinite_quantity = _mto_order()
            nonfinite_quantity["Quantity"] = quantity
            invalid_orders.append(nonfinite_quantity)

        for invalid in invalid_orders:
            with pytest.raises(OrderCommitmentConflict):
                normalize_mto_order(invalid)

    def test_reference_policy_is_exactly_unapproved_80_percent(self):
        assert REFERENCE_CCR_PROTECTION_POLICY == CcrProtectionPolicy(
            target_percent=80.0,
            source="ReferenceFallback",
            approved=False,
        )
        assert normalized_policy_dict(REFERENCE_CCR_PROTECTION_POLICY) == {
            "TargetPercent": 80.0,
            "Source": "ReferenceFallback",
            "Approved": False,
            "ConfigurationID": None,
        }

    def test_approved_policy_requires_configuration_and_reference_policy_rejects_configuration(
        self,
    ):
        approved = CcrProtectionPolicy(
            target_percent=75,
            source="ApprovedOperatingModel",
            approved=True,
            configuration_id="  OMC-2026-07  ",
        )

        assert normalized_policy_dict(approved) == {
            "TargetPercent": 75.0,
            "Source": "ApprovedOperatingModel",
            "Approved": True,
            "ConfigurationID": "OMC-2026-07",
        }

        inconsistent = (
            CcrProtectionPolicy(75, "ApprovedOperatingModel", False, "OMC-1"),
            CcrProtectionPolicy(75, "ApprovedOperatingModel", True),
            CcrProtectionPolicy(101, "ApprovedOperatingModel", True, "OMC-1"),
            CcrProtectionPolicy(80, "ReferenceFallback", True),
            CcrProtectionPolicy(80, "ReferenceFallback", False, "OMC-1"),
            CcrProtectionPolicy(79, "ReferenceFallback", False),
        )
        for policy in inconsistent:
            with pytest.raises(OrderCommitmentConflict):
                normalized_policy_dict(policy)
