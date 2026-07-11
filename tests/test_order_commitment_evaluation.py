"""Acceptance evidence for BE-SDBR-006 and BE-SDBR-010 MTO identity."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import inf, nan

import pytest

from sdbr.order_commitment_evaluation import (
    ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES,
    REFERENCE_CCR_PROTECTION_POLICY,
    CcrProtectionPolicy,
    OrderCommitmentConflict,
    OrderCommitmentSnapshotNotFound,
    candidate_demand_commitment_id,
    normalize_mto_order,
    normalized_policy_dict,
    select_order_commitment_operational_snapshot,
)
from sdbr.operational_state import OperationalStateSnapshot


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


def _operational_snapshot(
    snapshot_id: str,
    captured_at: datetime,
) -> OperationalStateSnapshot:
    return OperationalStateSnapshot(
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        inventory_buffers=[],
        material_availability=[],
        wip_limits=[],
    )


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
        assert str(order["PlanningOrderID"]).startswith("MTO-")
        assert candidate_demand_commitment_id(order).startswith("DC-")

    def test_planning_order_identity_isolates_delimiters_and_sources(self):
        delimiter_left = _mto_order()
        delimiter_left["OrderID"] = "A:B"
        delimiter_left["DemandLineID"] = "C"
        delimiter_right = _mto_order()
        delimiter_right["OrderID"] = "A"
        delimiter_right["DemandLineID"] = "B:C"
        other_source = _mto_order()
        other_source["SourceSystem"] = "OtherERP"

        normalized = [
            normalize_mto_order(order)
            for order in (delimiter_left, delimiter_right, other_source)
        ]

        assert len({row["PlanningOrderID"] for row in normalized}) == 3
        assert normalized[0]["LogicalOrderKey"] != normalized[1][
            "LogicalOrderKey"
        ]
        assert normalized[2]["PlanningOrderID"] != normalize_mto_order(
            _mto_order()
        )["PlanningOrderID"]

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

    def test_material_requirement_permutations_have_canonical_order(self):
        source = _mto_order()
        source["MaterialRequirements"] = [
            {
                "RequirementLineID": "30",
                "ItemID": "RM-3",
                "LocationID": "SECONDARY",
                "RequiredQty": 1,
                "Uom": "KG",
            },
            *source["MaterialRequirements"],
        ]
        reversed_source = deepcopy(source)
        reversed_source["MaterialRequirements"] = list(
            reversed(reversed_source["MaterialRequirements"])
        )

        first = normalize_mto_order(source)
        second = normalize_mto_order(reversed_source)

        assert first["MaterialRequirements"] == second["MaterialRequirements"]
        assert first["OrderContentFingerprint"] == second[
            "OrderContentFingerprint"
        ]

    def test_duplicate_requirement_line_is_rejected_across_material_keys(self):
        source = _mto_order()
        requirements = source["MaterialRequirements"]
        assert isinstance(requirements, list)
        requirements.append(
            {
                "RequirementLineID": "10",
                "ItemID": "RM-DIFFERENT",
                "LocationID": "SECONDARY",
                "RequiredQty": 1,
                "Uom": "KG",
            }
        )

        with pytest.raises(
            OrderCommitmentConflict,
            match="requirement line",
        ):
            normalize_mto_order(source)

    def test_trace_id_only_retry_replays_but_business_change_conflicts(self):
        first_source = _mto_order()
        retry_source = _mto_order()
        retry_source["TraceID"] = "TRACE-SO-100-10-V2-RETRY"
        changed_source = deepcopy(retry_source)
        changed_source["Quantity"] = 11

        first = normalize_mto_order(first_source)
        retry = normalize_mto_order(retry_source)
        changed = normalize_mto_order(changed_source)

        assert retry["TraceID"] != first["TraceID"]
        assert retry["OrderKey"] == first["OrderKey"]
        assert retry["OrderContentFingerprint"] == first[
            "OrderContentFingerprint"
        ]
        assert candidate_demand_commitment_id(retry) == (
            candidate_demand_commitment_id(first)
        )
        assert changed["OrderKey"] == first["OrderKey"]
        assert changed["OrderContentFingerprint"] != first[
            "OrderContentFingerprint"
        ]

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

    @pytest.mark.parametrize("approved", [0, 1, "true", None])
    def test_policy_approved_flag_requires_exact_bool(self, approved: object):
        policy = CcrProtectionPolicy(
            80,
            "ReferenceFallback",
            approved,  # type: ignore[arg-type]
        )

        with pytest.raises(OrderCommitmentConflict, match="boolean"):
            normalized_policy_dict(policy)

    @pytest.mark.parametrize(
        ("source", "approved", "target", "configuration_id"),
        [
            ("ApprovedOperatingModel", True, 75, 123),
            ("ApprovedOperatingModel", True, 75, ""),
            ("ApprovedOperatingModel", True, 75, "   "),
            ("ApprovedOperatingModel", True, 75, "OMC 1"),
            ("ApprovedOperatingModel", True, 75, "OMC\n1"),
            ("ReferenceFallback", False, 80, 123),
        ],
    )
    def test_policy_rejects_malformed_configuration_id(
        self,
        source: object,
        approved: bool,
        target: int,
        configuration_id: object,
    ):
        policy = CcrProtectionPolicy(
            target,
            source,  # type: ignore[arg-type]
            approved,
            configuration_id,  # type: ignore[arg-type]
        )

        with pytest.raises(OrderCommitmentConflict, match="ConfigurationID"):
            normalized_policy_dict(policy)


class TestOrderCommitmentSnapshotFreshness:
    evaluated_at = datetime(2026, 7, 12, 9, tzinfo=timezone.utc)

    def test_default_selection_uses_latest_nonfuture_snapshot_with_id_tiebreak(
        self,
    ):
        snapshots = {
            snapshot.snapshot_id: snapshot
            for snapshot in (
                _operational_snapshot(
                    "OPS-EARLIER",
                    self.evaluated_at - timedelta(minutes=30),
                ),
                _operational_snapshot(
                    "OPS-LATEST-A",
                    self.evaluated_at - timedelta(minutes=10),
                ),
                _operational_snapshot(
                    "OPS-LATEST-B",
                    self.evaluated_at - timedelta(minutes=10),
                ),
                _operational_snapshot(
                    "OPS-FUTURE",
                    self.evaluated_at + timedelta(minutes=1),
                ),
            )
        }

        result = select_order_commitment_operational_snapshot(
            snapshots=snapshots,
            evaluated_at=self.evaluated_at,
            requested_snapshot_id=None,
        )

        assert result == {
            "SnapshotSelectionMode": "LatestCurrent",
            "RequestedOperationalStateSnapshotID": None,
            "OperationalStateSnapshot": snapshots["OPS-LATEST-B"],
            "OperationalStateSnapshotID": "OPS-LATEST-B",
            "OperationalStateCapturedAt": "2026-07-12T08:50:00+00:00",
            "OperationalStateFreshnessStatus": "Fresh",
            "OperationalStateAgeMinutes": 10.0,
            "OperationalStateMaxAgeMinutes": 60,
            "OperationalStateValidThroughAt": "2026-07-12T09:50:00+00:00",
            "Acceptable": True,
        }

    def test_explicit_fresh_snapshot_is_selected_exactly(self):
        snapshots = {
            "OPS-REQUESTED": _operational_snapshot(
                "OPS-REQUESTED",
                self.evaluated_at - timedelta(minutes=20),
            ),
            "OPS-LATEST": _operational_snapshot(
                "OPS-LATEST",
                self.evaluated_at - timedelta(minutes=5),
            ),
        }

        result = select_order_commitment_operational_snapshot(
            snapshots=snapshots,
            evaluated_at=self.evaluated_at,
            requested_snapshot_id="  OPS-REQUESTED  ",
        )

        assert result["SnapshotSelectionMode"] == "Explicit"
        assert result["RequestedOperationalStateSnapshotID"] == "OPS-REQUESTED"
        assert result["OperationalStateSnapshot"] is snapshots["OPS-REQUESTED"]
        assert result["OperationalStateSnapshotID"] == "OPS-REQUESTED"
        assert result["OperationalStateFreshnessStatus"] == "Fresh"
        assert result["Acceptable"] is True

    def test_snapshot_at_sixty_minutes_is_fresh(self):
        snapshot = _operational_snapshot(
            "OPS-BOUNDARY",
            self.evaluated_at - timedelta(minutes=60),
        )

        result = select_order_commitment_operational_snapshot(
            snapshots={snapshot.snapshot_id: snapshot},
            evaluated_at=self.evaluated_at,
            requested_snapshot_id=None,
        )

        assert result["OperationalStateFreshnessStatus"] == "Fresh"
        assert result["OperationalStateAgeMinutes"] == 60.0
        assert result["OperationalStateMaxAgeMinutes"] == (
            ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES
        )
        assert result["OperationalStateValidThroughAt"] == (
            self.evaluated_at.isoformat()
        )
        assert result["Acceptable"] is True

    def test_snapshot_older_than_sixty_minutes_is_stale(self):
        snapshot = _operational_snapshot(
            "OPS-STALE",
            self.evaluated_at - timedelta(minutes=61),
        )

        result = select_order_commitment_operational_snapshot(
            snapshots={snapshot.snapshot_id: snapshot},
            evaluated_at=self.evaluated_at,
            requested_snapshot_id=None,
        )

        assert result["OperationalStateFreshnessStatus"] == "Stale"
        assert result["OperationalStateAgeMinutes"] == 61.0
        assert result["Acceptable"] is False

    def test_explicit_future_snapshot_is_future_and_unacceptable(self):
        snapshot = _operational_snapshot(
            "OPS-FUTURE",
            self.evaluated_at + timedelta(minutes=1),
        )

        result = select_order_commitment_operational_snapshot(
            snapshots={snapshot.snapshot_id: snapshot},
            evaluated_at=self.evaluated_at,
            requested_snapshot_id=snapshot.snapshot_id,
        )

        assert result["SnapshotSelectionMode"] == "Explicit"
        assert result["OperationalStateFreshnessStatus"] == "Future"
        assert result["OperationalStateAgeMinutes"] == -1.0
        assert result["Acceptable"] is False

    def test_no_nonfuture_snapshot_returns_no_current_snapshot(self):
        future = _operational_snapshot(
            "OPS-FUTURE",
            self.evaluated_at + timedelta(minutes=1),
        )

        result = select_order_commitment_operational_snapshot(
            snapshots={future.snapshot_id: future},
            evaluated_at=self.evaluated_at,
            requested_snapshot_id=None,
        )

        assert result == {
            "SnapshotSelectionMode": "LatestCurrent",
            "RequestedOperationalStateSnapshotID": None,
            "OperationalStateSnapshot": None,
            "OperationalStateSnapshotID": None,
            "OperationalStateCapturedAt": None,
            "OperationalStateFreshnessStatus": "Missing",
            "OperationalStateAgeMinutes": None,
            "OperationalStateMaxAgeMinutes": 60,
            "OperationalStateValidThroughAt": None,
            "Acceptable": False,
        }

    def test_unknown_explicit_snapshot_raises_snapshot_not_found(self):
        with pytest.raises(OrderCommitmentSnapshotNotFound) as raised:
            select_order_commitment_operational_snapshot(
                snapshots={},
                evaluated_at=self.evaluated_at,
                requested_snapshot_id="  OPS-UNKNOWN  ",
            )

        assert raised.value.status == "OperationalStateSnapshotNotFound"
        assert raised.value.snapshot_id == "OPS-UNKNOWN"
