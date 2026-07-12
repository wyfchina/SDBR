"""Acceptance evidence for BE-SDBR-006, BE-SDBR-009, and BE-SDBR-010 MTO identity."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import inf, nan

import pytest

from sdbr import order_commitment_evaluation
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
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_candidates import MaterialAvailability


def test_material_feasibility_evidence_cites_shared_material_allocation_ledger():
    assert "BE-SDBR-009" in __doc__


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


class TestOrderCommitmentMaterialFeasibility:
    observed_at = datetime(2026, 7, 11, 8, tzinfo=timezone.utc)

    @classmethod
    def _selection(
        cls,
        *,
        captured_at: datetime | None = None,
        buffers: list[InventoryBufferPolicy] | None = None,
        availability: list[MaterialAvailability] | None = None,
        explicit: bool = True,
    ) -> dict[str, object]:
        snapshot = OperationalStateSnapshot(
            snapshot_id="OPS-1",
            captured_at=captured_at or cls.observed_at,
            inventory_buffers=buffers
            if buffers is not None
            else [InventoryBufferPolicy("RM-1", "MAIN", 10, 0, 0, 0)],
            material_availability=availability
            if availability is not None
            else [MaterialAvailability("RM-1", "MAIN")],
            wip_limits=[],
        )
        return select_order_commitment_operational_snapshot(
            snapshots={snapshot.snapshot_id: snapshot},
            evaluated_at=cls.observed_at,
            requested_snapshot_id=snapshot.snapshot_id if explicit else None,
        )

    @classmethod
    def _evaluate(
        cls,
        requirements: list[dict[str, object]],
        *,
        selection: dict[str, object] | None = None,
        allocations: list[dict[str, object]] | None = None,
        window_minutes: int = 0,
        check: bool = True,
        skip_reason: str | None = None,
    ) -> dict[str, object]:
        return order_commitment_evaluation.evaluate_mto_material_availability(
            order={"MaterialRequirements": deepcopy(requirements)},
            snapshot_selection=selection or cls._selection(),
            active_material_allocations=allocations or [],
            current_demand_commitment_id="DC-CURRENT",
            evaluated_at=cls.observed_at,
            material_check_window_minutes=window_minutes,
            check_material_availability=check,
            skip_reason=skip_reason,
        )

    @staticmethod
    def _requirement(
        line_id: str = "L1",
        *,
        quantity: float = 5,
        item_id: str = "RM-1",
        location_id: str = "MAIN",
    ) -> dict[str, object]:
        return {
            "RequirementLineID": line_id,
            "ItemID": item_id,
            "LocationID": location_id,
            "RequiredQty": quantity,
            "Uom": "EA",
        }

    @staticmethod
    def _allocation(
        allocation_id: str,
        *,
        demand_id: str,
        quantity: object,
        item_id: str = "RM-1",
        location_id: str = "MAIN",
    ) -> dict[str, object]:
        return {
            "MaterialAllocationID": allocation_id,
            "Status": "ActivePlanReservation",
            "ItemID": item_id,
            "LocationID": location_id,
            "DemandCommitmentID": demand_id,
            "AllocatedQty": quantity,
        }

    @staticmethod
    def _same_key_material_result(requirements, *, on_hand=5.0):
        observed_at = datetime(2026, 7, 11, 8, tzinfo=timezone.utc)
        snapshot = OperationalStateSnapshot(
            snapshot_id="OPS-1",
            captured_at=observed_at,
            inventory_buffers=[
                InventoryBufferPolicy(
                    "RM-1", "MAIN", on_hand, 0.0, 0.0, 0.0
                )
            ],
            material_availability=[
                MaterialAvailability("RM-1", "MAIN")
            ],
            wip_limits=[],
        )
        selection = select_order_commitment_operational_snapshot(
            snapshots={snapshot.snapshot_id: snapshot},
            evaluated_at=observed_at,
            requested_snapshot_id=snapshot.snapshot_id,
        )
        return order_commitment_evaluation.evaluate_mto_material_availability(
            order={"MaterialRequirements": deepcopy(requirements)},
            snapshot_selection=selection,
            active_material_allocations=[],
            current_demand_commitment_id="DC-CURRENT",
            evaluated_at=observed_at,
            material_check_window_minutes=0,
        )

    def test_check_defaults_on_and_uses_uncommitted_shared_availability(self):
        selection = self._selection(
            availability=[MaterialAvailability("RM-1", "MAIN", 2)]
        )
        allocations = [
            self._allocation("MA-OTHER", demand_id="DC-OTHER", quantity=3),
        ]

        result = self._evaluate(
            [self._requirement()],
            selection=selection,
            allocations=allocations,
        )

        assert result["CheckEnabled"] is True
        assert result["Status"] == "Feasible"
        assert result["Lines"][0]["UncommittedAvailabilityQty"] == 5
        assert result["Lines"][0]["OtherPlanningAllocatedQty"] == 3
        assert result["AllocationRequests"][0]["AllocatedQty"] == 5

    def test_skip_requires_reason_records_pending_requirements_and_zero_allocations(
        self,
    ):
        requirements = [self._requirement()]
        with pytest.raises(OrderCommitmentConflict, match="skip reason"):
            self._evaluate(requirements, check=False)

        result = self._evaluate(
            requirements,
            check=False,
            skip_reason="  Planner requested capacity-only assessment.  ",
        )

        assert result["Status"] == "SkippedPendingConfirmation"
        assert result["SkipReason"] == "Planner requested capacity-only assessment."
        assert result["MaterialEligibilityCutoffAt"] is None
        assert result["PendingRequirements"] == requirements
        assert result["AllocationRequests"] == []

    def test_stale_snapshot_returns_evidence_insufficient_and_zero_allocations(
        self,
    ):
        selection = self._selection(
            captured_at=self.observed_at - timedelta(minutes=61)
        )

        result = self._evaluate([self._requirement()], selection=selection)

        assert result["Status"] == "EvidenceInsufficient"
        assert result["Issues"] == [{
            "Code": "OPERATIONAL_STATE_EVIDENCE_NOT_FRESH",
            "FreshnessStatus": "Stale",
        }]
        assert result["AllocationRequests"] == []

    def test_future_snapshot_returns_evidence_insufficient_and_zero_allocations(
        self,
    ):
        selection = self._selection(
            captured_at=self.observed_at + timedelta(minutes=1)
        )

        result = self._evaluate([self._requirement()], selection=selection)

        assert result["Status"] == "EvidenceInsufficient"
        assert result["Issues"][0]["FreshnessStatus"] == "Future"
        assert result["AllocationRequests"] == []

    def test_missing_snapshot_or_required_item_row_is_evidence_insufficient(self):
        missing_snapshot = select_order_commitment_operational_snapshot(
            snapshots={},
            evaluated_at=self.observed_at,
            requested_snapshot_id=None,
        )
        missing_row = self._selection(buffers=[], availability=[])

        results = [
            self._evaluate([self._requirement()], selection=missing_snapshot),
            self._evaluate([self._requirement()], selection=missing_row),
        ]

        assert [result["Issues"][0]["Code"] for result in results] == [
            "OPERATIONAL_STATE_EVIDENCE_NOT_FRESH",
            "REQUIRED_MATERIAL_EVIDENCE_MISSING",
        ]
        assert all(result["AllocationRequests"] == [] for result in results)

    def test_inbound_counts_only_when_aware_and_inside_frozen_material_window(self):
        requirement = [self._requirement(quantity=12)]
        inside = self._selection(
            availability=[MaterialAvailability(
                "RM-1",
                "MAIN",
                inbound_qty=2,
                inbound_available_at=self.observed_at + timedelta(minutes=30),
            )]
        )
        outside = self._selection(
            availability=[MaterialAvailability(
                "RM-1",
                "MAIN",
                inbound_qty=2,
                inbound_available_at=self.observed_at + timedelta(minutes=31),
            )]
        )
        naive = self._selection(
            availability=[MaterialAvailability(
                "RM-1",
                "MAIN",
                inbound_qty=2,
                inbound_available_at=datetime(2026, 7, 11, 8, 30),
            )]
        )

        covered = self._evaluate(requirement, selection=inside, window_minutes=30)
        late = self._evaluate(requirement, selection=outside, window_minutes=30)
        invalid = self._evaluate(requirement, selection=naive, window_minutes=30)

        assert covered["Status"] == "Feasible"
        assert covered["Lines"][0]["EligibleInboundQty"] == 2
        assert late["Status"] == "Shortage"
        assert late["Lines"][0]["EligibleInboundQty"] == 0
        assert invalid["Status"] == "EvidenceInsufficient"
        assert invalid["Issues"][0]["Code"] == "MATERIAL_EVIDENCE_INVALID"

    def test_shortage_is_all_or_nothing_and_returns_no_allocation_requests(self):
        requirements = [
            self._requirement("L1", quantity=3),
            self._requirement("L2", quantity=3),
        ]

        result = self._same_key_material_result(requirements)

        assert result["Status"] == "Shortage"
        assert result["AllocationRequests"] == []
        assert result["PendingRequirements"] == requirements

    def test_current_demand_allocation_is_not_subtracted_twice(self):
        allocations = [
            self._allocation("MA-CURRENT", demand_id="DC-CURRENT", quantity=9),
            self._allocation("MA-OTHER", demand_id="DC-OTHER", quantity=2),
        ]

        result = self._evaluate(
            [self._requirement(quantity=8)], allocations=allocations
        )

        assert result["Status"] == "Feasible"
        assert result["Lines"][0]["OtherPlanningAllocatedQty"] == 2
        assert result["Lines"][0]["UncommittedAvailabilityQty"] == 8

    def test_same_item_location_lines_use_cumulative_candidate_balance(self):
        requirements = [
            {"RequirementLineID": "L1", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
            {"RequirementLineID": "L2", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
        ]
        result = self._same_key_material_result(requirements)
        assert result["Status"] == "Shortage"
        assert [row["CoverageStatus"] for row in result["Lines"]] == [
            "Covered", "Shortage"
        ]
        assert [
            row["UncommittedAvailabilityQty"] for row in result["Lines"]
        ] == [5.0, 2.0]
        assert result["AllocationRequests"] == []

    def test_same_item_location_coverage_is_independent_of_input_line_order(self):
        requirements = [
            {"RequirementLineID": "L2", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
            {"RequirementLineID": "L1", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 3.0, "Uom": "EA"},
        ]
        forward = self._same_key_material_result(requirements)
        reverse = self._same_key_material_result(list(reversed(requirements)))
        assert forward == reverse

    def test_feasible_same_item_location_allocations_sum_to_accepted_total(self):
        requirements = [
            {"RequirementLineID": "L2", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 2.0, "Uom": "EA"},
            {"RequirementLineID": "L1", "ItemID": "RM-1",
             "LocationID": "MAIN", "RequiredQty": 2.0, "Uom": "EA"},
        ]
        result = self._same_key_material_result(requirements)
        assert result["Status"] == "Feasible"
        assert [
            row["RequirementLineID"]
            for row in result["AllocationRequests"]
        ] == ["L1", "L2"]
        assert sum(
            row["AllocatedQty"] for row in result["AllocationRequests"]
        ) == 4.0

    def test_malformed_unrelated_material_allocation_is_ignored_but_matching_malformed_row_is_insufficient(
        self,
    ):
        unrelated = {
            "Status": "ActivePlanReservation",
            "ItemID": "OTHER",
            "LocationID": "ELSEWHERE",
            "AllocatedQty": "not-a-number",
        }
        matching = {
            **unrelated,
            "ItemID": "RM-1",
            "LocationID": "MAIN",
        }

        ignored = self._evaluate(
            [self._requirement()], allocations=[unrelated]
        )
        insufficient = self._evaluate(
            [self._requirement()], allocations=[matching]
        )

        assert ignored["Status"] == "Feasible"
        assert insufficient["Status"] == "EvidenceInsufficient"
        assert insufficient["Issues"][0]["Code"] == "MATERIAL_EVIDENCE_INVALID"
        assert insufficient["AllocationRequests"] == []


class TestOrderCommitmentRecommendationMatrix:
    """BE-SDBR-010: total MTO recommendation and action matrix."""

    @staticmethod
    def _policy(threshold_state: str) -> CcrProtectionPolicy:
        if threshold_state == "ReferenceFallback":
            return REFERENCE_CCR_PROTECTION_POLICY
        return CcrProtectionPolicy(
            target_percent=75.0,
            source="ApprovedOperatingModel",
            approved=True,
            configuration_id="OMC-1",
        )

    @classmethod
    def _recommendation(
        cls,
        *,
        capacity: str,
        material: str,
        threshold_state: str,
    ) -> dict[str, object]:
        return order_commitment_evaluation.build_order_commitment_recommendation(
            shadow_schedule={
                "Status": capacity,
                "SelectedAssessment": {
                    "ThresholdExceeded": threshold_state == "ApprovedExceeded"
                },
            },
            material_assessment={"Status": material},
            protection_policy=cls._policy(threshold_state),
        )

    @pytest.mark.parametrize(
        (
            "capacity, material, threshold_state, decision, actions, "
            "requires_ccr, requires_material"
        ),
        [
            ("NotAssessable", "Feasible", "ApprovedWithin", "DoNotRecommendAccept", ["Reevaluate", "Reject"], False, False),
            ("NotAssessable", "Feasible", "ApprovedExceeded", "DoNotRecommendAccept", ["Reevaluate", "Reject"], True, False),
            ("NotAssessable", "Feasible", "ReferenceFallback", "DoNotRecommendAccept", ["Reevaluate", "Reject"], True, False),
            ("OnTime", "Feasible", "ApprovedWithin", "RecommendAccept", ["AcceptRequestedDate", "Reevaluate", "Reject"], False, False),
            ("OnTime", "Feasible", "ApprovedExceeded", "PlannerConfirmationRequired", ["AcceptRequestedDate", "Reevaluate", "Reject"], True, False),
            ("OnTime", "Feasible", "ReferenceFallback", "PlannerConfirmationRequired", ["AcceptRequestedDate", "Reevaluate", "Reject"], True, False),
            ("OnTime", "SkippedPendingConfirmation", "ApprovedWithin", "CapacityAcceptableMaterialPending", ["ConditionallyAcceptRequestedDate", "Reevaluate", "Reject"], False, True),
            ("OnTime", "SkippedPendingConfirmation", "ApprovedExceeded", "PlannerConfirmationRequired", ["ConditionallyAcceptRequestedDate", "Reevaluate", "Reject"], True, True),
            ("OnTime", "SkippedPendingConfirmation", "ReferenceFallback", "PlannerConfirmationRequired", ["ConditionallyAcceptRequestedDate", "Reevaluate", "Reject"], True, True),
            ("OnTime", "EvidenceInsufficient", "ApprovedWithin", "MaterialEvidenceRequired", ["Reevaluate", "Reject"], False, False),
            ("OnTime", "EvidenceInsufficient", "ApprovedExceeded", "MaterialEvidenceRequired", ["Reevaluate", "Reject"], True, False),
            ("OnTime", "EvidenceInsufficient", "ReferenceFallback", "MaterialEvidenceRequired", ["Reevaluate", "Reject"], True, False),
            ("OnTime", "Shortage", "ApprovedWithin", "DoNotRecommendAccept", ["Reevaluate", "Reject"], False, False),
            ("OnTime", "Shortage", "ApprovedExceeded", "DoNotRecommendAccept", ["Reevaluate", "Reject"], True, False),
            ("OnTime", "Shortage", "ReferenceFallback", "DoNotRecommendAccept", ["Reevaluate", "Reject"], True, False),
            ("LaterSafeDate", "Feasible", "ApprovedWithin", "RecommendLaterPromise", ["AcceptRecommendedDate", "Reevaluate", "Reject"], False, False),
            ("LaterSafeDate", "Feasible", "ApprovedExceeded", "PlannerConfirmationRequired", ["AcceptRecommendedDate", "Reevaluate", "Reject"], True, False),
            ("LaterSafeDate", "Feasible", "ReferenceFallback", "PlannerConfirmationRequired", ["AcceptRecommendedDate", "Reevaluate", "Reject"], True, False),
            ("LaterSafeDate", "SkippedPendingConfirmation", "ApprovedWithin", "RecommendLaterPromise", ["ConditionallyAcceptRecommendedDate", "Reevaluate", "Reject"], False, True),
            ("LaterSafeDate", "SkippedPendingConfirmation", "ApprovedExceeded", "PlannerConfirmationRequired", ["ConditionallyAcceptRecommendedDate", "Reevaluate", "Reject"], True, True),
            ("LaterSafeDate", "SkippedPendingConfirmation", "ReferenceFallback", "PlannerConfirmationRequired", ["ConditionallyAcceptRecommendedDate", "Reevaluate", "Reject"], True, True),
            ("LaterSafeDate", "EvidenceInsufficient", "ApprovedWithin", "MaterialEvidenceRequired", ["Reevaluate", "Reject"], False, False),
            ("LaterSafeDate", "EvidenceInsufficient", "ApprovedExceeded", "MaterialEvidenceRequired", ["Reevaluate", "Reject"], True, False),
            ("LaterSafeDate", "EvidenceInsufficient", "ReferenceFallback", "MaterialEvidenceRequired", ["Reevaluate", "Reject"], True, False),
            ("LaterSafeDate", "Shortage", "ApprovedWithin", "DoNotRecommendAccept", ["Reevaluate", "Reject"], False, False),
            ("LaterSafeDate", "Shortage", "ApprovedExceeded", "DoNotRecommendAccept", ["Reevaluate", "Reject"], True, False),
            ("LaterSafeDate", "Shortage", "ReferenceFallback", "DoNotRecommendAccept", ["Reevaluate", "Reject"], True, False),
        ],
    )
    def test_total_recommendation_matrix(
        self,
        capacity: str,
        material: str,
        threshold_state: str,
        decision: str,
        actions: list[str],
        requires_ccr: bool,
        requires_material: bool,
    ):
        result = self._recommendation(
            capacity=capacity,
            material=material,
            threshold_state=threshold_state,
        )

        assert result["Decision"] == decision
        assert result["AllowedActions"] == actions
        assert result["RequiresCcrAcknowledgement"] is requires_ccr
        assert result["RequiresMaterialAcknowledgement"] is requires_material
        assert result["RequiresPlannerDecision"] is True
        for action in actions:
            expected_acceptance = action.startswith("Accept") or action.startswith(
                "ConditionallyAccept"
            )
            assert result["ActionAcknowledgementRequirements"][action] == {
                "RequiresCcrAcknowledgement": expected_acceptance and requires_ccr,
                "RequiresMaterialAcknowledgement": (
                    expected_acceptance and requires_material
                ),
            }

    def test_later_safe_skipped_material_allows_conditional_recommended_date(self):
        result = self._recommendation(
            capacity="LaterSafeDate",
            material="SkippedPendingConfirmation",
            threshold_state="ApprovedWithin",
        )

        assert result["AllowedActions"] == [
            "ConditionallyAcceptRecommendedDate",
            "Reevaluate",
            "Reject",
        ]

    def test_later_safe_reference_fallback_requires_ccr_acknowledgement(self):
        result = self._recommendation(
            capacity="LaterSafeDate",
            material="Feasible",
            threshold_state="ReferenceFallback",
        )

        assert result["RequiresCcrAcknowledgement"] is True
        assert result["ActionAcknowledgementRequirements"][
            "AcceptRecommendedDate"
        ]["RequiresCcrAcknowledgement"] is True

    def test_later_safe_approved_threshold_exceeded_requires_ccr_acknowledgement(
        self,
    ):
        result = self._recommendation(
            capacity="LaterSafeDate",
            material="Feasible",
            threshold_state="ApprovedExceeded",
        )

        assert result["RequiresCcrAcknowledgement"] is True
        assert result["ActionAcknowledgementRequirements"][
            "AcceptRecommendedDate"
        ]["RequiresCcrAcknowledgement"] is True

    def test_later_safe_insufficient_material_has_no_acceptance_action(self):
        result = self._recommendation(
            capacity="LaterSafeDate",
            material="EvidenceInsufficient",
            threshold_state="ApprovedWithin",
        )

        assert result["AllowedActions"] == ["Reevaluate", "Reject"]

    @pytest.mark.parametrize(
        ("capacity", "material"),
        [
            (capacity, material)
            for capacity in ("NotAssessable", "OnTime", "LaterSafeDate")
            for material in (
                "Feasible",
                "SkippedPendingConfirmation",
                "EvidenceInsufficient",
                "Shortage",
            )
        ],
    )
    def test_every_reference_fallback_sets_ccr_acknowledgement(
        self,
        capacity: str,
        material: str,
    ):
        result = self._recommendation(
            capacity=capacity,
            material=material,
            threshold_state="ReferenceFallback",
        )

        assert result["RequiresCcrAcknowledgement"] is True

    @pytest.mark.parametrize(
        ("capacity", "threshold_state"),
        [
            (capacity, threshold_state)
            for capacity in ("NotAssessable", "OnTime", "LaterSafeDate")
            for threshold_state in (
                "ApprovedWithin",
                "ApprovedExceeded",
                "ReferenceFallback",
            )
        ],
    )
    def test_every_skipped_material_row_sets_material_acknowledgement(
        self,
        capacity: str,
        threshold_state: str,
    ):
        result = self._recommendation(
            capacity=capacity,
            material="SkippedPendingConfirmation",
            threshold_state=threshold_state,
        )

        assert result["RequiresMaterialAcknowledgement"] is True


class TestOrderCommitmentEvaluationIdentity:
    """BE-SDBR-006, BE-SDBR-010: frozen relevant-state evaluation identity."""

    evaluated_at = datetime(2026, 7, 12, 8, tzinfo=timezone.utc)

    @classmethod
    def _order(cls, *, version: str = "2") -> dict[str, object]:
        source = _mto_order()
        source["OrderVersion"] = version
        source["ReceivedAt"] = cls.evaluated_at + timedelta(
            minutes=int(version)
        )
        return normalize_mto_order(source)

    @classmethod
    def _selection(
        cls,
        *,
        freshness: str = "Fresh",
        age_minutes: int = 5,
        snapshot_id: str = "OPS-1",
    ) -> dict[str, object]:
        captured_at = cls.evaluated_at - timedelta(minutes=age_minutes)
        return {
            "OperationalStateSnapshotID": snapshot_id,
            "OperationalStateCapturedAt": captured_at.isoformat(),
            "OperationalStateFreshnessStatus": freshness,
            "OperationalStateAgeMinutes": age_minutes,
            "OperationalStateValidThroughAt": (
                captured_at + timedelta(minutes=60)
            ).isoformat(),
        }

    @classmethod
    def _capacity_row(cls, **changes: object) -> dict[str, object]:
        row = {
            "CapacityReservationID": "CR-1",
            "ReservationBatchID": "RB-1",
            "DemandCommitmentID": "DC-OTHER",
            "DemandClass": "MTO",
            "ResourceID": "CCR-1",
            "WindowStartAt": cls.evaluated_at.isoformat(),
            "WindowEndAt": (cls.evaluated_at + timedelta(hours=2)).isoformat(),
            "ReservedMinutes": 15.0,
            "LatestAllowedCompletionAt": (
                cls.evaluated_at + timedelta(hours=1)
            ).isoformat(),
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
        }
        return {**row, **changes}

    @classmethod
    def _material_row(cls, **changes: object) -> dict[str, object]:
        row = {
            "MaterialAllocationID": "MA-1",
            "ReservationBatchID": "RB-1",
            "DemandCommitmentID": "DC-OTHER",
            "DemandClass": "MTO",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 2.0,
            "MaterialSnapshotID": "OPS-1",
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
        }
        return {**row, **changes}

    @classmethod
    def _basis(cls, **changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "baseline_planning_run_id": "RUN-1",
            "baseline_operational_state_snapshot_id": "OPS-BASELINE",
            "baseline_schedule_fingerprint": "sha256:schedule",
            "master_data_version_id": "MDV-1",
            "operating_model_configuration_id": "OMC-1",
            "operating_model_fingerprint": "sha256:operating-model",
            "scheduling_configuration_id": "SC-1",
            "ddmrp_configuration_id": "DDMRP-1",
            "release_policy_version_id": "RP-1",
            "frozen_release_policy_fingerprint": "sha256:release-policy",
            "routing_fingerprint": "sha256:routing",
            "calendar_fingerprint": "sha256:calendar",
            "time_buffer_minutes": 30,
            "material_check_window_minutes": 60,
            "capacity_assessment_cutoff_at": cls.evaluated_at + timedelta(hours=1),
            "material_eligibility_cutoff_at": cls.evaluated_at + timedelta(hours=1),
            "check_material_availability": True,
            "material_skip_reason": None,
            "snapshot_selection": cls._selection(),
            "relevant_capacity_window_keys": [
                (
                    "CCR-1",
                    cls.evaluated_at.isoformat(),
                    (cls.evaluated_at + timedelta(hours=2)).isoformat(),
                )
            ],
            "capacity_ledger_rows": [cls._capacity_row()],
            "relevant_material_keys": [("RM-1", "MAIN")],
            "inventory_buffer_rows": [
                InventoryBufferPolicy("RM-1", "MAIN", 10.0, 1.0, 2.0, 3.0)
            ],
            "material_availability_rows": [
                MaterialAvailability(
                    "RM-1",
                    "MAIN",
                    allocated_qty=1.0,
                    inbound_qty=2.0,
                    inbound_available_at=cls.evaluated_at + timedelta(minutes=30),
                )
            ],
            "material_ledger_rows": [cls._material_row()],
        }
        values.update(changes)
        return order_commitment_evaluation.build_order_commitment_basis(**values)

    @classmethod
    def _shadow(cls, **changes: object) -> dict[str, object]:
        candidate = {
            "PromiseAt": (cls.evaluated_at + timedelta(hours=1)).isoformat(),
            "WindowAssessments": [{
                "RouteSequence": 1,
                "OperationID": "OP-1",
                "ResourceID": "CCR-1",
                "WindowStartAt": cls.evaluated_at.isoformat(),
                "WindowEndAt": (cls.evaluated_at + timedelta(hours=2)).isoformat(),
                "UsableWindowStartAt": cls.evaluated_at.isoformat(),
                "UsableWindowEndAt": (cls.evaluated_at + timedelta(hours=1)).isoformat(),
                "LatestAllowedCompletionAt": (cls.evaluated_at + timedelta(hours=1)).isoformat(),
                "CapacityMinutes": 120.0,
                "UsableTemporalCapacityMinutes": 60.0,
                "ScheduledLoadMinutes": 15.0,
                "ScheduledLoadBeforeDeadlineMinutes": 15.0,
                "ExistingReservationMinutes": 0.0,
                "CandidateLoadMinutes": 10.0,
                "LoadBeforeMinutes": 15.0,
                "LoadAfterMinutes": 25.0,
                "LoadAfterPercent": 20.0,
                "AggregateRemainingMinutes": 105.0,
                "TemporalRemainingMinutes": 45.0,
                "LoadStatus": "WithinCapacity",
                "ThresholdExceeded": False,
            }],
            "ReservationRequests": [{
                "ReservationLineID": "CRR-1",
                "OrderID": "SO-100",
                "OperationID": "OP-1",
                "ResourceID": "CCR-1",
                "WindowStartAt": cls.evaluated_at.isoformat(),
                "WindowEndAt": (cls.evaluated_at + timedelta(hours=2)).isoformat(),
                "ReservedMinutes": 10.0,
                "LatestAllowedCompletionAt": (cls.evaluated_at + timedelta(hours=1)).isoformat(),
            }],
        }
        shadow = {
            "Status": "OnTime",
            "Algorithm": {"Name": "CcrShadow", "Version": "1"},
            "SelectedAssessment": {"ThresholdExceeded": False},
            "RequestedDateAssessment": candidate,
        }
        return {**shadow, **changes}

    @classmethod
    def _material(cls, **changes: object) -> dict[str, object]:
        material = {
            "Status": "Feasible",
            "CheckEnabled": True,
            "SkipReason": None,
            "MaterialCheckWindowMinutes": 60,
            "SnapshotSelectionMode": "Explicit",
            "RequestedOperationalStateSnapshotID": "OPS-1",
            "OperationalStateAgeMinutes": 5,
            "AllocationRequests": [{
                "RequirementLineID": "10",
                "ItemID": "RM-1",
                "LocationID": "MAIN",
                "Uom": "EA",
                "AllocatedQty": 2.0,
                "SupplySourceType": "OnHand",
                "MaterialSnapshotID": "OPS-1",
            }],
        }
        return {**material, **changes}

    @classmethod
    def _evaluation(cls, **changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "order": cls._order(),
            "shadow_schedule": cls._shadow(),
            "material_assessment": cls._material(),
            "basis": cls._basis(),
            "protection_policy": CcrProtectionPolicy(
                75.0, "ApprovedOperatingModel", True, "OMC-1"
            ),
            "evaluated_at": cls.evaluated_at,
        }
        values.update(changes)
        return order_commitment_evaluation.create_order_commitment_evaluation(
            **values
        )

    def test_exact_replay_returns_existing_evaluation(self):
        candidate = self._evaluation()
        status, stored = order_commitment_evaluation.register_order_commitment_evaluation(
            {candidate["EvaluationID"]: candidate}, candidate
        )

        assert status == "Duplicate"
        assert stored == candidate

    def test_protection_policy_change_creates_new_evaluation(self):
        original = self._evaluation()
        changed = self._evaluation(
            protection_policy=REFERENCE_CCR_PROTECTION_POLICY
        )

        assert changed["EvaluationID"] != original["EvaluationID"]

    def test_each_frozen_configuration_reference_changes_identity(self):
        original = self._evaluation()
        fields = (
            "operating_model_configuration_id",
            "operating_model_fingerprint",
            "scheduling_configuration_id",
            "ddmrp_configuration_id",
            "release_policy_version_id",
            "frozen_release_policy_fingerprint",
            "routing_fingerprint",
            "calendar_fingerprint",
        )

        for field in fields:
            changed_basis = self._basis(**{field: "changed"})
            changed = self._evaluation(basis=changed_basis)
            assert changed["EvaluationID"] != original["EvaluationID"]

    def test_shadow_algorithm_capacity_semantics_changes_identity(self):
        original = self._evaluation()
        changed = self._evaluation(
            shadow_schedule=self._shadow(
                Algorithm={"Name": "CcrShadow", "Version": "2"}
            )
        )

        assert changed["EvaluationID"] != original["EvaluationID"]

    def test_relevant_capacity_change_in_exact_assessed_window_changes_basis(self):
        original = self._basis()
        changed = self._basis(
            capacity_ledger_rows=[self._capacity_row(ReservedMinutes=16.0)]
        )

        assert changed["AuditBasisFingerprint"] != original["AuditBasisFingerprint"]

    def test_timezone_equivalent_aware_capacity_window_is_included(self):
        local_timezone = timezone(timedelta(hours=8))
        local_row = self._capacity_row(
            WindowStartAt=self.evaluated_at.astimezone(local_timezone).isoformat(),
            WindowEndAt=(
                self.evaluated_at + timedelta(hours=2)
            ).astimezone(local_timezone).isoformat(),
            LatestAllowedCompletionAt=(
                self.evaluated_at + timedelta(hours=1)
            ).astimezone(local_timezone).isoformat(),
        )

        basis = self._basis(capacity_ledger_rows=[local_row])

        assert basis["RelevantCapacityLedger"] == [self._capacity_row()]

    def test_linked_to_formal_order_capacity_reservation_is_excluded(self):
        basis = self._basis(capacity_ledger_rows=[
            self._capacity_row(Status="LinkedToFormalOrder")
        ])

        assert basis["RelevantCapacityLedger"] == []

    def test_unrelated_capacity_resource_or_window_does_not_change_basis(self):
        original = self._basis()
        changed = self._basis(capacity_ledger_rows=[
            self._capacity_row(),
            self._capacity_row(
                CapacityReservationID="CR-OTHER",
                ResourceID="OTHER",
                ReservedMinutes="not-a-number",
            ),
        ])

        assert changed == original

    def test_relevant_material_item_location_change_changes_basis(self):
        original = self._basis()
        changed = self._basis(
            material_ledger_rows=[self._material_row(AllocatedQty=3.0)]
        )

        assert changed["AuditBasisFingerprint"] != original["AuditBasisFingerprint"]

    def test_unrelated_material_item_location_does_not_change_basis(self):
        original = self._basis()
        changed = self._basis(material_ledger_rows=[
            self._material_row(),
            self._material_row(
                MaterialAllocationID="MA-OTHER",
                ItemID="OTHER",
                LocationID="ELSEWHERE",
                AllocatedQty="not-a-number",
            ),
        ])

        assert changed == original

    def test_fresh_age_observation_change_keeps_identity_but_fresh_to_stale_changes_it(self):
        original = self._evaluation()
        same_snapshot_new_age = self._selection()
        same_snapshot_new_age["OperationalStateAgeMinutes"] = 6
        same_snapshot_stale = self._selection()
        same_snapshot_stale.update({
            "OperationalStateFreshnessStatus": "Stale",
            "OperationalStateAgeMinutes": 61,
        })
        age_changed = self._evaluation(
            basis=self._basis(snapshot_selection=same_snapshot_new_age),
            material_assessment=self._material(OperationalStateAgeMinutes=6),
        )
        stale = self._evaluation(
            basis=self._basis(snapshot_selection=same_snapshot_stale),
            material_assessment=self._material(OperationalStateAgeMinutes=61),
        )

        assert age_changed["EvaluationID"] == original["EvaluationID"]
        assert stale["EvaluationID"] != original["EvaluationID"]

    def test_capacity_cutoff_change_creates_deterministic_new_identity_not_content_conflict(self):
        original = self._evaluation()
        changed = self._evaluation(
            basis=self._basis(
                capacity_assessment_cutoff_at=self.evaluated_at + timedelta(hours=2)
            )
        )
        status, stored = order_commitment_evaluation.register_order_commitment_evaluation(
            {original["EvaluationID"]: original}, changed
        )

        assert changed["EvaluationID"] != original["EvaluationID"]
        assert status == "Created"
        assert stored == changed

    def test_material_cutoff_crossing_inbound_creates_deterministic_new_identity(self):
        original = self._evaluation()
        changed = self._evaluation(
            basis=self._basis(
                material_eligibility_cutoff_at=self.evaluated_at + timedelta(minutes=15)
            ),
            material_assessment=self._material(MaterialCheckWindowMinutes=15),
        )

        assert changed["EvaluationID"] != original["EvaluationID"]

    def test_skipped_material_decision_basis_excludes_snapshot_and_material_rows(self):
        skipped = self._basis(
            check_material_availability=False,
            material_skip_reason="Planner requested capacity-only assessment.",
        )
        changed_material = self._basis(
            check_material_availability=False,
            material_skip_reason="Planner requested capacity-only assessment.",
            snapshot_selection=self._selection(snapshot_id="OPS-2"),
            material_ledger_rows=[self._material_row(AllocatedQty=9.0)],
            material_availability_rows=[MaterialAvailability("RM-1", "MAIN", 9.0)],
        )

        assert skipped["AuditBasisFingerprint"] != changed_material["AuditBasisFingerprint"]
        assert skipped["DecisionStalenessBasisFingerprint"] == changed_material[
            "DecisionStalenessBasisFingerprint"
        ]
        assert "SelectedOperationalStateSnapshotID" not in skipped[
            "DecisionStalenessBasis"
        ]
        assert "RelevantMaterialLedger" not in skipped["DecisionStalenessBasis"]

    def test_malformed_unrelated_rows_are_ignored_after_exact_prefilter(self):
        basis = self._basis(
            capacity_ledger_rows=[self._capacity_row(), {
                "Status": "ActivePlanReservation",
                "ResourceID": "OTHER",
                "WindowStartAt": "not-a-date",
                "WindowEndAt": "still-not-a-date",
                "ReservedMinutes": "not-a-number",
            }],
            material_ledger_rows=[self._material_row(), {
                "Status": "ActivePlanReservation",
                "ItemID": "OTHER",
                "LocationID": "ELSEWHERE",
                "AllocatedQty": "not-a-number",
            }],
        )

        assert basis["RelevantCapacityLedger"] == [
            self._capacity_row()
        ]
        assert basis["RelevantMaterialLedger"] == [self._material_row()]

    def test_only_open_same_logical_order_is_superseded(self):
        prior = self._evaluation()
        candidate = self._evaluation(order=self._order(version="3"))
        updates = order_commitment_evaluation.supersede_open_order_commitment_evaluations(
            evaluations={prior["EvaluationID"]: prior},
            candidate=candidate,
            superseded_at=self.evaluated_at,
        )

        updated = updates[prior["EvaluationID"]]
        assert updated["Status"] == "Superseded"
        assert updated["SupersededByEvaluationID"] == candidate["EvaluationID"]
        assert updated["RecordVersion"] == 2

    def test_accepted_or_rejected_evidence_cannot_be_superseded(self):
        prior = self._evaluation()
        candidate = self._evaluation(order=self._order(version="3"))
        accepted = {**prior, "Status": "AcceptedPendingFormalSchedule"}
        rejected = {**prior, "Status": "Rejected"}

        with pytest.raises(OrderCommitmentConflict, match="ExplicitAmendment"):
            order_commitment_evaluation.exact_order_commitment_intake_replay(
                evaluations={accepted["EvaluationID"]: accepted},
                order=candidate["Order"],
            )
        assert order_commitment_evaluation.supersede_open_order_commitment_evaluations(
            evaluations={rejected["EvaluationID"]: rejected},
            candidate=candidate,
            superseded_at=self.evaluated_at,
        ) == {}


class TestOrderCommitmentAcceptancePreparation:
    """BE-SDBR-006 through BE-SDBR-010: MTO decision preparation."""

    evaluated_at = TestOrderCommitmentEvaluationIdentity.evaluated_at

    @classmethod
    def _evaluation(cls, **changes: object) -> dict[str, object]:
        return TestOrderCommitmentEvaluationIdentity._evaluation(**changes)

    @classmethod
    def _shadow_for_action(cls, action: str, *, threshold_exceeded: bool = False) -> dict[str, object]:
        candidate = TestOrderCommitmentEvaluationIdentity._shadow()[
            "RequestedDateAssessment"
        ]
        assert isinstance(candidate, dict)
        candidate = deepcopy(candidate)
        if action in {
            "AcceptRecommendedDate",
            "ConditionallyAcceptRecommendedDate",
        }:
            candidate["PromiseAt"] = (
                cls.evaluated_at + timedelta(hours=2)
            ).isoformat()
            return TestOrderCommitmentEvaluationIdentity._shadow(
                Status="LaterSafeDate",
                SelectedAssessment={"ThresholdExceeded": threshold_exceeded},
                EarliestSafeAssessment=candidate,
            )
        return TestOrderCommitmentEvaluationIdentity._shadow(
            SelectedAssessment={"ThresholdExceeded": threshold_exceeded}
        )

    @classmethod
    def _material_for_action(cls, action: str) -> dict[str, object]:
        if action in {
            "ConditionallyAcceptRequestedDate",
            "ConditionallyAcceptRecommendedDate",
        }:
            return TestOrderCommitmentEvaluationIdentity._material(
                Status="SkippedPendingConfirmation",
                CheckEnabled=False,
                SkipReason="Planner requested capacity-only assessment.",
                AllocationRequests=[],
                PendingRequirements=[{
                    "RequirementLineID": "10",
                    "ItemID": "RM-1",
                    "LocationID": "MAIN",
                    "RequiredQty": 2.0,
                    "Uom": "EA",
                }],
            )
        return TestOrderCommitmentEvaluationIdentity._material()

    @classmethod
    def _evaluation_for_action(
        cls,
        action: str,
        *,
        policy: CcrProtectionPolicy | None = None,
        threshold_exceeded: bool = False,
    ) -> dict[str, object]:
        return cls._evaluation(
            shadow_schedule=cls._shadow_for_action(
                action,
                threshold_exceeded=threshold_exceeded,
            ),
            material_assessment=cls._material_for_action(action),
            protection_policy=policy or CcrProtectionPolicy(
                75.0, "ApprovedOperatingModel", True, "OMC-1"
            ),
        )

    @classmethod
    def _prepare(
        cls,
        evaluation: dict[str, object],
        action: str,
        **changes: object,
    ) -> object:
        values: dict[str, object] = {
            "evaluation": evaluation,
            "existing_commitments": {},
            "decision_id": "DEC-MTO-1",
            "decision": action,
            "decided_by": "planner-1",
            "decided_at": cls.evaluated_at,
            "reason": "Planner reviewed frozen evidence.",
            "ccr_risk_acknowledged": False,
            "material_risk_acknowledged": False,
        }
        values.update(changes)
        return order_commitment_evaluation.prepare_mto_acceptance(**values)  # type: ignore[arg-type]

    def test_requested_feasible_builds_canonical_mto_demand_and_material_rows(self):
        evaluation = self._evaluation_for_action("AcceptRequestedDate")

        write_set = self._prepare(
            evaluation,
            "AcceptRequestedDate",
        )

        assert write_set.demand_commitment["DemandSourceType"] == "MTOCustomerOrder"
        assert write_set.demand_commitment["DemandClass"] == "MTO"
        assert write_set.demand_commitment["Status"] == "Active"
        assert write_set.demand_commitment["AcceptedPromiseAt"] == (
            self.evaluated_at + timedelta(hours=1)
        ).isoformat()
        assert len(write_set.capacity_reservations) == 1
        assert len(write_set.material_allocations) == 1
        assert write_set.batch["DemandCommitmentID"] == write_set.demand_commitment[
            "DemandCommitmentID"
        ]

    def test_requested_skipped_builds_pending_material_and_zero_allocations(self):
        evaluation = self._evaluation_for_action(
            "ConditionallyAcceptRequestedDate"
        )

        write_set = self._prepare(
            evaluation,
            "ConditionallyAcceptRequestedDate",
            material_risk_acknowledged=True,
        )

        assert write_set.demand_commitment["MaterialCommitmentStatus"] == "PendingConfirmation"
        assert write_set.demand_commitment["PendingMaterialRequirements"] == [{
            "RequirementLineID": "10",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "RequiredQty": 2.0,
            "Uom": "EA",
        }]
        assert len(write_set.capacity_reservations) == 1
        assert write_set.material_allocations == ()

    def test_later_feasible_uses_recommended_promise(self):
        evaluation = self._evaluation_for_action("AcceptRecommendedDate")

        write_set = self._prepare(evaluation, "AcceptRecommendedDate")

        assert write_set.demand_commitment["AcceptedPromiseAt"] == (
            self.evaluated_at + timedelta(hours=2)
        ).isoformat()
        assert write_set.demand_commitment["RequiredAt"] == (
            self.evaluated_at + timedelta(hours=2)
        ).isoformat()

    def test_later_skipped_uses_conditional_recommended_action_and_zero_allocations(self):
        evaluation = self._evaluation_for_action(
            "ConditionallyAcceptRecommendedDate"
        )

        write_set = self._prepare(
            evaluation,
            "ConditionallyAcceptRecommendedDate",
            material_risk_acknowledged=True,
        )

        assert write_set.demand_commitment["AcceptedPromiseAt"] == (
            self.evaluated_at + timedelta(hours=2)
        ).isoformat()
        assert write_set.material_allocations == ()

    def test_all_reference_and_exceeded_selected_candidates_require_ccr_ack(self):
        for action in order_commitment_evaluation.ACCEPTANCE_DECISIONS:
            for policy, threshold_exceeded in (
                (REFERENCE_CCR_PROTECTION_POLICY, False),
                (CcrProtectionPolicy(75.0, "ApprovedOperatingModel", True, "OMC-1"), True),
            ):
                evaluation = self._evaluation_for_action(
                    action,
                    policy=policy,
                    threshold_exceeded=threshold_exceeded,
                )
                with pytest.raises(OrderCommitmentConflict, match="CCR risk"):
                    self._prepare(
                        evaluation,
                        action,
                        material_risk_acknowledged=(
                            action.startswith("Conditionally")
                        ),
                    )

    def test_all_skipped_acceptance_actions_require_material_ack(self):
        for action in (
            "ConditionallyAcceptRequestedDate",
            "ConditionallyAcceptRecommendedDate",
        ):
            with pytest.raises(OrderCommitmentConflict, match="Material risk"):
                self._prepare(self._evaluation_for_action(action), action)

    def test_reject_never_requires_ccr_or_material_acknowledgement(self):
        assert order_commitment_evaluation.action_acknowledgement_requirements(
            action="Reject",
            requires_ccr_acknowledgement=True,
            requires_material_acknowledgement=True,
        ) == {
            "RequiresCcrAcknowledgement": False,
            "RequiresMaterialAcknowledgement": False,
        }

    def test_insufficient_shortage_and_not_assessable_reject_acceptance(self):
        for capacity_status, material_status in (
            ("NotAssessable", "Feasible"),
            ("OnTime", "EvidenceInsufficient"),
            ("OnTime", "Shortage"),
        ):
            evaluation = self._evaluation(
                shadow_schedule=TestOrderCommitmentEvaluationIdentity._shadow(
                    Status=capacity_status
                ),
                material_assessment=TestOrderCommitmentEvaluationIdentity._material(
                    Status=material_status
                ),
            )
            with pytest.raises(OrderCommitmentConflict, match="Decision is not allowed"):
                self._prepare(evaluation, "AcceptRequestedDate")

    def test_expired_latest_completion_rejects_acceptance(self):
        evaluation = self._evaluation_for_action("AcceptRequestedDate")

        with pytest.raises(OrderCommitmentConflict, match="window has expired"):
            self._prepare(
                evaluation,
                "AcceptRequestedDate",
                decided_at=self.evaluated_at + timedelta(hours=1),
            )

    def test_decision_fingerprint_excludes_decided_at_and_covers_every_canonical_field(self):
        evaluation = self._evaluation_for_action("AcceptRequestedDate")
        base = {
            "evaluation": evaluation,
            "decision_id": "DEC-MTO-1",
            "decision": "AcceptRequestedDate",
            "actor_id": "planner-1",
            "reason": "Planner reviewed frozen evidence.",
            "ccr_risk_acknowledged": False,
            "material_risk_acknowledged": False,
        }
        fingerprint = order_commitment_evaluation.canonical_decision_fingerprint(
            **base
        )

        assert fingerprint == order_commitment_evaluation.canonical_decision_fingerprint(
            **base
        )
        changed_evaluation_id = deepcopy(evaluation)
        changed_evaluation_id["EvaluationID"] = "OCE-CHANGED"
        changed_evaluation_fingerprint = deepcopy(evaluation)
        changed_evaluation_fingerprint["EvaluationFingerprint"] = "sha256:changed"
        variations = (
            {**base, "evaluation": changed_evaluation_id},
            {**base, "evaluation": changed_evaluation_fingerprint},
            {**base, "decision_id": "DEC-MTO-2"},
            {**base, "decision": "Reject"},
            {**base, "actor_id": "planner-2"},
            {**base, "reason": "Different reason."},
            {**base, "ccr_risk_acknowledged": True},
            {**base, "material_risk_acknowledged": True},
        )
        assert all(
            order_commitment_evaluation.canonical_decision_fingerprint(**variant)
            != fingerprint
            for variant in variations
        )
        write_set = self._prepare(evaluation, "AcceptRequestedDate")
        accepted = order_commitment_evaluation.accepted_evaluation_record(
            evaluation=evaluation,
            write_set=write_set,
            decision_id="DEC-MTO-1",
            decision="AcceptRequestedDate",
            decided_by="planner-1",
            decided_at=self.evaluated_at,
            reason="Planner reviewed frozen evidence.",
            ccr_risk_acknowledged=False,
            material_risk_acknowledged=False,
        )
        rejected = order_commitment_evaluation.rejected_evaluation_record(
            evaluation=evaluation,
            decision_id="DEC-MTO-REJECT",
            decision="Reject",
            decided_by="planner-1",
            decided_at=self.evaluated_at,
            reason="Planner rejected the recommendation.",
            ccr_risk_acknowledged=False,
            material_risk_acknowledged=False,
        )
        accepted_observed_later = order_commitment_evaluation.accepted_evaluation_record(
            evaluation=evaluation,
            write_set=write_set,
            decision_id="DEC-MTO-1",
            decision="AcceptRequestedDate",
            decided_by="planner-1",
            decided_at=self.evaluated_at + timedelta(minutes=1),
            reason="Planner reviewed frozen evidence.",
            ccr_risk_acknowledged=False,
            material_risk_acknowledged=False,
        )

        assert "Decision" not in evaluation
        assert accepted["Status"] == "AcceptedPendingFormalSchedule"
        assert accepted["RecordVersion"] == evaluation["RecordVersion"] + 1
        assert accepted["Decision"]["DecisionFingerprint"] == fingerprint
        assert accepted["Decision"]["ReservationBatchID"] == write_set.batch[
            "ReservationBatchID"
        ]
        assert accepted["Decision"]["ExternalOrderAcceptance"] == "NotPerformed"
        assert accepted["Decision"]["PlanningRunCreation"] == "NotPerformed"
        assert accepted["Decision"]["ProductionMutation"] == "NotPerformed"
        assert accepted_observed_later["Decision"]["DecidedAt"] != accepted[
            "Decision"
        ]["DecidedAt"]
        assert accepted_observed_later["Decision"]["DecisionFingerprint"] == accepted[
            "Decision"
        ]["DecisionFingerprint"]
        assert rejected["Status"] == "Rejected"
        assert rejected["RecordVersion"] == evaluation["RecordVersion"] + 1
        assert rejected["Decision"]["CcrRiskAcknowledged"] is False
        assert rejected["Decision"]["MaterialRiskAcknowledged"] is False

    def test_acceptance_uses_normalize_demand_commitment_and_preserves_mto_context(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        evaluation = self._evaluation_for_action("AcceptRequestedDate")
        calls: list[dict[str, object]] = []
        original = order_commitment_evaluation.normalize_demand_commitment

        def record_normalization(value: object) -> dict[str, object]:
            assert isinstance(value, dict)
            calls.append(deepcopy(value))
            return original(value)

        monkeypatch.setattr(
            order_commitment_evaluation,
            "normalize_demand_commitment",
            record_normalization,
        )

        write_set = self._prepare(evaluation, "AcceptRequestedDate")

        assert len(calls) == 1
        assert calls[0]["OrderCommitmentEvaluationID"] == evaluation["EvaluationID"]
        assert calls[0]["BaselinePlanningRunID"] == evaluation["Basis"][
            "BaselinePlanningRunID"
        ]
        assert write_set.demand_commitment["ExternalOrderAcceptance"] == "NotPerformed"
        assert write_set.demand_commitment["PlanningRunCreation"] == "NotPerformed"
        assert write_set.demand_commitment["ProductionMutation"] == "NotPerformed"
