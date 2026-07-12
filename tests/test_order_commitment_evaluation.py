"""Acceptance evidence for BE-SDBR-006 and BE-SDBR-010 MTO identity."""

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
