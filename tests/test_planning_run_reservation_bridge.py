"""Acceptance evidence for BE-RUN-011 and BE-SDBR-007, BE-SDBR-008, BE-SDBR-009."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from sdbr.planning_commitments import BUSINESS_CONTENT_FIELDS, create_demand_commitment
from sdbr.order_commitment_evaluation import prepare_mto_acceptance
from sdbr.planning_reservations import apply_reservation_write_set
from sdbr.planning_run_reservation_bridge import (
    ReservationBatchReferenceError,
    ReservationGraphDriftError,
    ScheduledOccupancyEvidenceError,
    freeze_planning_reservations,
    transition_planning_reservations_for_run,
)


def _canonical_demands() -> dict[str, dict[str, object]]:
    first = create_demand_commitment(
        demand_source_type="MTOCustomerOrder",
        source_system="MockERP",
        source_object_type="CustomerOrder",
        source_object_id="SO-1",
        source_object_version="1",
        demand_line_id="1",
        item_or_product_id="FG-1",
        location_id="MAIN",
        quantity=1,
        uom="EA",
        required_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
        demand_class="MTO",
        trace_id="TRACE-DC-1",
    )
    second = create_demand_commitment(
        demand_source_type="MTAReplenishment",
        source_system="SDBR",
        source_object_type="ReplenishmentRecommendation",
        source_object_id="REC-2",
        source_object_version="1",
        demand_line_id="1",
        item_or_product_id="FG-2",
        location_id="MAIN",
        quantity=1,
        uom="EA",
        required_at=datetime(2026, 7, 20, 10, tzinfo=timezone.utc),
        demand_class="MTA",
        trace_id="TRACE-DC-2",
    )
    first.update({"Status": "Active", "RecordVersion": 1})
    second.update({"Status": "Active", "RecordVersion": 1})
    return {
        str(first["DemandCommitmentID"]): first,
        str(second["DemandCommitmentID"]): second,
    }


_CANONICAL_DEMANDS = _canonical_demands()
DEMAND_1_ID, DEMAND_2_ID = tuple(_CANONICAL_DEMANDS)


def _demands() -> dict[str, dict[str, object]]:
    return deepcopy(_CANONICAL_DEMANDS)


def _batches(*, status: str = "ActivePlanReservation") -> dict[str, dict[str, object]]:
    return {
        "PRB-1": {
            "ReservationBatchID": "PRB-1",
            "DemandCommitmentID": DEMAND_1_ID,
            "DemandClass": "MTO",
            "Status": status,
            "CapacityReservationIDs": ["CCR-1"],
            "MaterialAllocationIDs": ["MA-1"],
            "Details": {"source": "planner-confirmation"},
            "RecordVersion": 1,
        },
        "PRB-2": {
            "ReservationBatchID": "PRB-2",
            "DemandCommitmentID": DEMAND_2_ID,
            "DemandClass": "MTA",
            "Status": "LinkedToFormalOrder",
            "CapacityReservationIDs": ["CCR-2"],
            "MaterialAllocationIDs": ["MA-2"],
            "RecordVersion": 1,
        },
    }


def _capacities(*, status: str = "ActivePlanReservation") -> dict[str, dict[str, object]]:
    return {
        "CCR-1": {
            "CapacityReservationID": "CCR-1",
            "ReservationBatchID": "PRB-1",
            "DemandCommitmentID": DEMAND_1_ID,
            "DemandClass": "MTO",
            "ReservationLineID": "CAP-1",
            "OrderID": "WO-1",
            "OperationID": "WO-1:CCR",
            "ResourceID": "CCR-A",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "WindowEndAt": "2026-07-20T10:00:00+00:00",
            "ReservedMinutes": 120,
            "LatestAllowedCompletionAt": "2026-07-20T10:00:00+00:00",
            "Status": status,
            "Details": {"resource": "CCR-A"},
            "RecordVersion": 1,
        },
        "CCR-2": {
            "CapacityReservationID": "CCR-2",
            "ReservationBatchID": "PRB-2",
            "DemandCommitmentID": DEMAND_2_ID,
            "DemandClass": "MTA",
            "ReservationLineID": "CAP-2",
            "OrderID": "WO-2",
            "OperationID": "WO-2:CCR",
            "ResourceID": "CCR-B",
            "WindowStartAt": "2026-07-20T10:00:00+00:00",
            "WindowEndAt": "2026-07-20T11:00:00+00:00",
            "ReservedMinutes": 60,
            "LatestAllowedCompletionAt": "2026-07-20T11:00:00+00:00",
            "Status": "LinkedToFormalOrder",
            "RecordVersion": 1,
        },
        "CCR-OTHER": {
            "CapacityReservationID": "CCR-OTHER",
            "ReservationBatchID": "OTHER",
            "Status": "ActivePlanReservation",
        },
    }


def _allocations(
    *, status: str = "ActivePlanReservation"
) -> dict[str, dict[str, object]]:
    return {
        "MA-1": {
            "MaterialAllocationID": "MA-1",
            "ReservationBatchID": "PRB-1",
            "DemandCommitmentID": DEMAND_1_ID,
            "DemandClass": "MTO",
            "Status": status,
            "Details": {"item": "RM-1"},
            "RecordVersion": 1,
        },
        "MA-2": {
            "MaterialAllocationID": "MA-2",
            "ReservationBatchID": "PRB-2",
            "DemandCommitmentID": DEMAND_2_ID,
            "DemandClass": "MTA",
            "Status": "LinkedToFormalOrder",
            "RecordVersion": 1,
        },
        "MA-OTHER": {
            "MaterialAllocationID": "MA-OTHER",
            "ReservationBatchID": "OTHER",
            "Status": "ActivePlanReservation",
        },
    }


def _occurred_at() -> datetime:
    return datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("latest_allowed_completion_at", "message"),
    [
        (None, "LatestAllowedCompletionAt"),
        ("2026-07-20T09:30:00", "timezone-aware"),
        ("2026-07-20T07:59:00+00:00", "inside the reservation window"),
        ("2026-07-20T10:01:00+00:00", "inside the reservation window"),
    ],
)
def test_freeze_requires_aware_latest_completion_inside_capacity_window(
    latest_allowed_completion_at: object,
    message: str,
):
    capacities = _capacities()
    if latest_allowed_completion_at is None:
        capacities["CCR-1"].pop("LatestAllowedCompletionAt")
    else:
        capacities["CCR-1"]["LatestAllowedCompletionAt"] = (
            latest_allowed_completion_at
        )

    with pytest.raises(ReservationBatchReferenceError, match=message):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=_allocations(),
        )


def test_freeze_rejects_self_consistent_unsupported_demand_source():
    demands = _demands()
    demand = demands[DEMAND_1_ID]
    demand["DemandSourceType"] = "Forecast"
    content = {field: demand[field] for field in BUSINESS_CONTENT_FIELDS}
    encoded = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    demand["ContentFingerprint"] = f"sha256:{sha256(encoded).hexdigest()}"

    with pytest.raises(ReservationBatchReferenceError, match="source type"):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=demands,
            batches=_batches(),
            capacity_reservations=_capacities(),
            material_allocations=_allocations(),
        )


def _exact_schedule(*, include_second: bool = False) -> dict[str, object]:
    rows = [
        {
            "ResourceID": "CCR-A",
            "Bars": [
                {
                    "OrderID": "WO-1",
                    "OperationID": "WO-1:CCR",
                    "Start": "2026-07-20T08:00:00+00:00",
                    "End": "2026-07-20T10:00:00+00:00",
                    "DurationMinutes": 120,
                }
            ],
        }
    ]
    if include_second:
        rows.append(
            {
                "ResourceID": "CCR-B",
                "Bars": [
                    {
                        "OrderID": "WO-2",
                        "OperationID": "WO-2:CCR",
                        "Start": "2026-07-20T10:00:00+00:00",
                        "End": "2026-07-20T11:00:00+00:00",
                        "DurationMinutes": 60,
                    }
                ],
            }
        )
    return {"GanttRows": rows}


def _run_graph_operation(
    operation: str,
    *,
    batches: dict[str, dict[str, object]],
    capacities: dict[str, dict[str, object]],
    allocations: dict[str, dict[str, object]],
) -> object:
    if operation == "freeze":
        return freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )
    return transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Completed",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
        schedule=_exact_schedule(),
    )


def test_freeze_copies_only_explicit_eligible_batches_in_caller_and_ledger_order():
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-2", "PRB-1"],
        demand_commitments=_demands(),
        batches=_batches(),
        capacity_reservations=_capacities(),
        material_allocations=_allocations(),
    )

    assert frozen["ReservationBatchIDs"] == ["PRB-2", "PRB-1"]
    assert [row["ReservationBatchID"] for row in frozen["Batches"]] == [
        "PRB-2",
        "PRB-1",
    ]
    assert [row["CapacityReservationID"] for row in frozen["CapacityReservations"]] == [
        "CCR-2",
        "CCR-1",
    ]
    assert [row["MaterialAllocationID"] for row in frozen["MaterialAllocations"]] == [
        "MA-2",
        "MA-1",
    ]


def test_empty_selection_ignores_malformed_unrelated_child_batch_references():
    capacities = _capacities()
    allocations = _allocations()
    capacities["CCR-OTHER"]["ReservationBatchID"] = []
    allocations["MA-OTHER"]["ReservationBatchID"] = {"bad": "id"}

    frozen = freeze_planning_reservations(
        batch_ids=[],
        demand_commitments=_demands(),
        batches=_batches(),
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    assert frozen["ReservationBatchIDs"] == []
    assert frozen["Batches"] == []
    assert frozen["CapacityReservations"] == []
    assert frozen["MaterialAllocations"] == []
    assert frozen["GraphFormat"] == "SDBRPlanningReservationGraphV2"
    assert frozen["GraphVersion"] == 2
    assert frozen["DemandCommitments"] == []
    assert str(frozen["GraphFingerprint"]).startswith("sha256:")


def test_selected_batch_ignores_malformed_unrelated_child_batch_references():
    capacities = _capacities()
    allocations = _allocations()
    capacities["CCR-OTHER"]["ReservationBatchID"] = []
    allocations["MA-OTHER"]["ReservationBatchID"] = {"bad": "id"}

    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=_batches(),
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    assert frozen["ReservationBatchIDs"] == ["PRB-1"]
    assert [row["CapacityReservationID"] for row in frozen["CapacityReservations"]] == [
        "CCR-1"
    ]
    assert [row["MaterialAllocationID"] for row in frozen["MaterialAllocations"]] == [
        "MA-1"
    ]


@pytest.mark.parametrize(
    ("batch_ids", "batches", "message"),
    [
        (["PRB-1", "PRB-1"], _batches(), "duplicate"),
        (["MISSING"], _batches(), "does not exist"),
        (["PRB-1"], _batches(status="HeldForPlanningError"), "not eligible"),
    ],
)
def test_freeze_rejects_duplicate_missing_or_ineligible_batch_references(
    batch_ids: list[str], batches: dict[str, dict[str, object]], message: str
):
    with pytest.raises(ReservationBatchReferenceError, match=message):
        freeze_planning_reservations(
            batch_ids=batch_ids,
            demand_commitments=_demands(),
            batches=batches,
            capacity_reservations=_capacities(),
            material_allocations=_allocations(),
        )


def test_freeze_deep_copies_selected_batches_and_declared_children_without_aliasing():
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()

    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    batches["PRB-1"]["Details"]["source"] = "changed-input"  # type: ignore[index]
    capacities["CCR-1"]["Details"]["resource"] = "changed-input"  # type: ignore[index]
    allocations["MA-1"]["Details"]["item"] = "changed-input"  # type: ignore[index]
    frozen["Batches"][0]["Details"]["source"] = "changed-result"  # type: ignore[index]
    frozen["CapacityReservations"][0]["Details"]["resource"] = "changed-result"  # type: ignore[index]
    frozen["MaterialAllocations"][0]["Details"]["item"] = "changed-result"  # type: ignore[index]

    assert batches["PRB-1"]["Details"] == {"source": "changed-input"}
    assert capacities["CCR-1"]["Details"] == {"resource": "changed-input"}
    assert allocations["MA-1"]["Details"] == {"item": "changed-input"}
    assert frozen["Batches"][0]["Details"] == {"source": "changed-result"}
    assert frozen["CapacityReservations"][0]["Details"] == {
        "resource": "changed-result"
    }
    assert frozen["MaterialAllocations"][0]["Details"] == {
        "item": "changed-result"
    }


def test_completed_run_converts_capacity_but_keeps_material_until_authority_handoff():
    result = transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Completed",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        demand_commitments=_demands(),
        batches=_batches(),
        capacity_reservations=_capacities(),
        material_allocations=_allocations(),
        schedule=_exact_schedule(),
    )

    assert result["Batches"]["PRB-1"]["Status"] == "ConvertedToScheduledOccupancy"
    assert (
        result["CapacityReservations"]["CCR-1"]["Status"]
        == "ConvertedToScheduledOccupancy"
    )
    assert result["MaterialAllocations"]["MA-1"]["Status"] == "ActivePlanReservation"
    for record in (
        result["Batches"]["PRB-1"],
        result["CapacityReservations"]["CCR-1"],
        result["MaterialAllocations"]["MA-1"],
    ):
        assert record["PlanningRunID"] == "RUN-1"
        assert record["LastTransitionAt"] == "2026-07-20T12:00:00+00:00"
        assert record["EventType"] == "PlanningRunCompleted"


@pytest.mark.parametrize("run_status", ["Failed", "DeadLetter"])
def test_failed_or_dead_letter_run_holds_batch_capacity_and_still_active_material(
    run_status: str,
):
    result = transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status=run_status,
        batch_ids=["PRB-1", "PRB-2"],
        occurred_at=_occurred_at(),
        demand_commitments=_demands(),
        batches=_batches(),
        capacity_reservations=_capacities(),
        material_allocations=_allocations(),
    )

    assert result["Batches"]["PRB-1"]["Status"] == "HeldForPlanningError"
    assert result["CapacityReservations"]["CCR-1"]["Status"] == "HeldForPlanningError"
    assert result["MaterialAllocations"]["MA-1"]["Status"] == "HeldForPlanningError"
    assert result["MaterialAllocations"]["MA-2"]["Status"] == "LinkedToFormalOrder"
    assert result["MaterialAllocations"]["MA-2"]["PlanningRunID"] == "RUN-1"
    assert result["MaterialAllocations"]["MA-2"]["EventType"] == f"PlanningRun{run_status}"


def test_queued_recovery_from_held_batch_returns_unchanged_deep_copies():
    batches = _batches(status="HeldForPlanningError")
    capacities = _capacities(status="HeldForPlanningError")
    allocations = _allocations(status="HeldForPlanningError")
    before = deepcopy((batches, capacities, allocations))

    result = transition_planning_reservations_for_run(
        run_id="RUN-RECOVERY",
        run_status="Queued",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    assert (batches, capacities, allocations) == before
    assert result["Batches"] == batches
    assert result["CapacityReservations"] == capacities
    assert result["MaterialAllocations"] == allocations
    assert "PlanningRunID" not in result["Batches"]["PRB-1"]
    result["Batches"]["PRB-1"]["Details"]["source"] = "changed-result"  # type: ignore[index]
    assert batches["PRB-1"]["Details"] == {"source": "planner-confirmation"}


def test_frozen_recovery_preserves_monotonic_material_authority_handoff():
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    batches["PRB-1"]["MaterialAllocationIDs"] = [
        "MA-1",
        "MA-LINKED",
        "MA-EXTERNAL",
        "MA-OTHER-AUTHORITY",
    ]
    allocations.update(
        {
            "MA-LINKED": {
                "MaterialAllocationID": "MA-LINKED",
                "ReservationBatchID": "PRB-1",
                "DemandCommitmentID": DEMAND_1_ID,
                "DemandClass": "MTO",
                "Status": "LinkedToFormalOrder",
                "RecordVersion": 1,
            },
            "MA-EXTERNAL": {
                "MaterialAllocationID": "MA-EXTERNAL",
                "ReservationBatchID": "PRB-1",
                "DemandCommitmentID": DEMAND_1_ID,
                "DemandClass": "MTO",
                "Status": "ActivePlanReservation",
                "MaterialSnapshotID": "OPS-1",
                "RecordVersion": 1,
            },
            "MA-OTHER-AUTHORITY": {
                "MaterialAllocationID": "MA-OTHER-AUTHORITY",
                "ReservationBatchID": "PRB-1",
                "DemandCommitmentID": DEMAND_1_ID,
                "DemandClass": "MTO",
                "Status": "ActivePlanReservation",
                "MaterialSnapshotID": "OPS-1",
                "RecordVersion": 1,
            },
        }
    )
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    failed = transition_planning_reservations_for_run(
        run_id="RUN-RECOVERY",
        run_status="Failed",
        occurred_at=_occurred_at(),
        frozen_reservations=frozen,
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    batches = failed["Batches"]
    capacities = failed["CapacityReservations"]
    allocations = failed["MaterialAllocations"]
    allocations["MA-EXTERNAL"].update(
        {
            "Status": "Externalized",
            "RecordVersion": int(allocations["MA-EXTERNAL"]["RecordVersion"]) + 1,
            "ExternalAllocationRef": "ERP-ALLOC-1",
            "MaterialSnapshotID": "OPS-AUTHORITY-2",
            "EventType": "AuthorityAllocationExternalized",
        }
    )
    allocations["MA-OTHER-AUTHORITY"].update(
        {
            "Status": "AuthorityTransferred",
            "RecordVersion": int(
                allocations["MA-OTHER-AUTHORITY"]["RecordVersion"]
            )
            + 1,
            "ExternalAllocationRef": "WMS-ALLOC-2",
            "MaterialSnapshotID": "OPS-AUTHORITY-2",
            "EventType": "AuthorityAllocationTransferred",
        }
    )
    external_before = deepcopy(allocations["MA-EXTERNAL"])
    transferred_before = deepcopy(allocations["MA-OTHER-AUTHORITY"])

    result = transition_planning_reservations_for_run(
        run_id="RUN-RECOVERY",
        run_status="Completed",
        occurred_at=_occurred_at(),
        frozen_reservations=frozen,
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
        schedule=_exact_schedule(),
    )

    assert result["Batches"]["PRB-1"]["Status"] == "ConvertedToScheduledOccupancy"
    assert (
        result["CapacityReservations"]["CCR-1"]["Status"]
        == "ConvertedToScheduledOccupancy"
    )
    assert result["MaterialAllocations"]["MA-1"]["Status"] == "ActivePlanReservation"
    assert result["MaterialAllocations"]["MA-1"]["EventType"] == "PlanningRunCompleted"
    assert result["MaterialAllocations"]["MA-1"]["PlanningRunID"] == "RUN-RECOVERY"
    assert result["MaterialAllocations"]["MA-LINKED"]["Status"] == "LinkedToFormalOrder"
    assert result["MaterialAllocations"]["MA-EXTERNAL"] == external_before
    assert result["MaterialAllocations"]["MA-OTHER-AUTHORITY"] == transferred_before


@pytest.mark.parametrize(
    ("collection", "record_id"),
    [("capacity", "CCR-1"), ("material", "MA-1")],
)
@pytest.mark.parametrize("malformed_batch_id", [[], {"bad": "id"}])
def test_rejects_unhashable_child_batch_identity_as_reference_error(
    collection: str,
    record_id: str,
    malformed_batch_id: object,
):
    capacities = _capacities()
    allocations = _allocations()
    records = capacities if collection == "capacity" else allocations
    records[record_id]["ReservationBatchID"] = malformed_batch_id

    with pytest.raises(ReservationBatchReferenceError, match="identity"):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=allocations,
        )


@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_rejects_missing_declared_child_before_freeze_or_transition(operation: str):
    batches = _batches()
    capacities = _capacities()
    capacities.pop("CCR-1")

    with pytest.raises(ReservationBatchReferenceError, match="missing"):
        _run_graph_operation(
            operation,
            batches=batches,
            capacities=capacities,
            allocations=_allocations(),
        )


@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_rejects_orphan_child_linked_to_selected_batch(operation: str):
    capacities = _capacities()
    capacities["CCR-ORPHAN"] = {
        "CapacityReservationID": "CCR-ORPHAN",
        "ReservationBatchID": "PRB-1",
        "Status": "ActivePlanReservation",
    }

    with pytest.raises(ReservationBatchReferenceError, match="orphan"):
        _run_graph_operation(
            operation,
            batches=_batches(),
            capacities=capacities,
            allocations=_allocations(),
        )


@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_rejects_child_canonical_id_that_differs_from_mapping_key_or_ledger_id(
    operation: str,
):
    capacities = _capacities()
    capacities["CCR-1"]["CapacityReservationID"] = "CCR-MISMATCH"

    with pytest.raises(ReservationBatchReferenceError, match="canonical ID"):
        _run_graph_operation(
            operation,
            batches=_batches(),
            capacities=capacities,
            allocations=_allocations(),
        )


@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_rejects_duplicate_canonical_child_identity(operation: str):
    batches = _batches()
    batches["PRB-1"]["CapacityReservationIDs"] = ["CCR-1", "CCR-DUP"]
    capacities = _capacities()
    capacities["CCR-DUP"] = {
        "CapacityReservationID": "CCR-1",
        "ReservationBatchID": "PRB-1",
        "Status": "ActivePlanReservation",
    }

    with pytest.raises(ReservationBatchReferenceError, match="duplicate canonical"):
        _run_graph_operation(
            operation,
            batches=batches,
            capacities=capacities,
            allocations=_allocations(),
        )


@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_rejects_declared_child_with_wrong_batch_link(operation: str):
    capacities = _capacities()
    capacities["CCR-1"]["ReservationBatchID"] = "PRB-2"

    with pytest.raises(ReservationBatchReferenceError, match="wrong ReservationBatchID"):
        _run_graph_operation(
            operation,
            batches=_batches(),
            capacities=capacities,
            allocations=_allocations(),
        )


@pytest.mark.parametrize("field", ["CapacityReservationIDs", "MaterialAllocationIDs"])
@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_rejects_malformed_authoritative_child_lists(field: str, operation: str):
    batches = _batches()
    batches["PRB-1"][field] = "not-a-list"

    with pytest.raises(ReservationBatchReferenceError, match="must be a list"):
        _run_graph_operation(
            operation,
            batches=batches,
            capacities=_capacities(),
            allocations=_allocations(),
        )


@pytest.mark.parametrize(
    ("collection", "record_id", "field"),
    [
        ("capacities", "CCR-1", "CapacityReservationID"),
        ("allocations", "MA-1", "MaterialAllocationID"),
        ("capacities", "CCR-1", "ReservationBatchID"),
        ("allocations", "MA-1", "ReservationBatchID"),
    ],
)
def test_rejects_declared_children_with_missing_identity_fields(
    collection: str, record_id: str, field: str
):
    capacities = _capacities()
    allocations = _allocations()
    records = capacities if collection == "capacities" else allocations
    records[record_id].pop(field)

    with pytest.raises(ReservationBatchReferenceError, match="identity"):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=allocations,
        )


@pytest.mark.parametrize("operation", ["freeze", "transition"])
def test_invalid_graph_never_mutates_inputs_or_returns_partial_results(operation: str):
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    capacities.pop("CCR-1")
    before = deepcopy((batches, capacities, allocations))

    with pytest.raises(ReservationBatchReferenceError, match="missing"):
        _run_graph_operation(
            operation,
            batches=batches,
            capacities=capacities,
            allocations=allocations,
        )

    assert (batches, capacities, allocations) == before


@pytest.mark.parametrize(
    ("occurred_at", "run_status", "message"),
    [
        (datetime(2026, 7, 20, 12), "Completed", "timezone-aware"),
        ("2026-07-20T12:00:00+00:00", "Completed", "timezone-aware"),
        (_occurred_at(), "Cancelled", "Unsupported planning run status"),
    ],
)
def test_transition_rejects_naive_timestamp_or_unsupported_run_status(
    occurred_at: object, run_status: str, message: str
):
    with pytest.raises(ValueError, match=message):
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status=run_status,
            batch_ids=["PRB-1"],
            occurred_at=occurred_at,
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=_capacities(),
            material_allocations=_allocations(),
        )


def test_transition_does_not_mutate_inputs_or_alias_transitioned_records():
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    before = deepcopy((batches, capacities, allocations))

    result = transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Completed",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
        schedule=_exact_schedule(),
    )
    result["Batches"]["PRB-1"]["Details"]["source"] = "changed-result"  # type: ignore[index]
    result["CapacityReservations"]["CCR-1"]["Details"]["resource"] = "changed-result"  # type: ignore[index]
    result["MaterialAllocations"]["MA-1"]["Details"]["item"] = "changed-result"  # type: ignore[index]

    assert (batches, capacities, allocations) == before


def test_freeze_records_versioned_graph_identity_and_fingerprint():
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=_batches(),
        capacity_reservations=_capacities(),
        material_allocations=_allocations(),
    )

    assert frozen["GraphFormat"] == "SDBRPlanningReservationGraphV2"
    assert frozen["GraphVersion"] == 2
    assert str(frozen["GraphID"]).startswith("PRG-")
    assert str(frozen["GraphFingerprint"]).startswith("sha256:")
    assert frozen["DemandCommitments"][0]["DemandCommitmentID"] == DEMAND_1_ID
    assert frozen["DemandCommitments"][0]["RecordVersion"] == 1
    assert str(frozen["DemandCommitments"][0]["ContentFingerprint"]).startswith(
        "sha256:"
    )
    assert frozen["Batches"][0]["RecordVersion"] == 1
    assert frozen["CapacityReservations"][0]["RecordVersion"] == 1
    assert frozen["MaterialAllocations"][0]["RecordVersion"] == 1


@pytest.mark.parametrize(
    ("collection", "field", "value"),
    [
        ("capacity", "DemandCommitmentID", "DC-WRONG"),
        ("capacity", "DemandClass", "MTA"),
        ("material", "DemandCommitmentID", "DC-WRONG"),
        ("material", "DemandClass", "MTA"),
    ],
)
def test_freeze_rejects_child_demand_or_class_inconsistent_with_batch(
    collection: str,
    field: str,
    value: str,
):
    capacities = _capacities()
    allocations = _allocations()
    record = capacities["CCR-1"] if collection == "capacity" else allocations["MA-1"]
    record[field] = value

    with pytest.raises(ReservationBatchReferenceError, match=field):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=allocations,
        )


@pytest.mark.parametrize("field", ["ReservationLineID", "OrderID", "OperationID"])
def test_freeze_requires_stable_capacity_line_and_schedule_correlation(field: str):
    capacities = _capacities()
    capacities["CCR-1"].pop(field)

    with pytest.raises(ReservationBatchReferenceError, match=field):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=_allocations(),
        )


@pytest.mark.parametrize("collection", ["capacity", "material"])
@pytest.mark.parametrize("status", [[], {"bad": "status"}])
def test_freeze_maps_non_string_child_status_to_reference_error(
    collection: str,
    status: object,
):
    capacities = _capacities()
    allocations = _allocations()
    target = capacities["CCR-1"] if collection == "capacity" else allocations["MA-1"]
    target["Status"] = status

    with pytest.raises(ReservationBatchReferenceError, match="Status must be a string"):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=allocations,
        )


def test_freeze_rejects_non_increasing_reserved_capacity_window():
    capacities = _capacities()
    capacities["CCR-1"]["WindowEndAt"] = capacities["CCR-1"]["WindowStartAt"]

    with pytest.raises(ReservationBatchReferenceError, match="strictly after"):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            demand_commitments=_demands(),
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=_allocations(),
        )


@pytest.mark.parametrize("schedule", [{}, {"GanttRows": []}])
def test_completed_run_rejects_empty_scheduled_occupancy_evidence(schedule):
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    with pytest.raises(ScheduledOccupancyEvidenceError) as error:
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=schedule,
            demand_commitments=_demands(),
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert error.value.capacity_reservation_ids == ("CCR-1",)
    assert batches["PRB-1"]["Status"] == "ActivePlanReservation"
    assert capacities["CCR-1"]["Status"] == "ActivePlanReservation"


@pytest.mark.parametrize(
    "schedule",
    [
        {"GanttRows": None},
        {"GanttRows": [{"ResourceID": "CCR-A", "Bars": None}]},
        {"GanttRows": [{"ResourceID": "CCR-A", "Bars": ["not-an-object"]}]},
        {
            "GanttRows": [{
                "ResourceID": "CCR-A",
                "Bars": [{
                    "OrderID": "WO-1",
                    "OperationID": "WO-1:CCR",
                    "Start": "2026-07-20T08:00:00+00:00",
                    "End": "2026-07-20T10:00:00+00:00",
                    "DurationMinutes": "120",
                }],
            }]
        },
    ],
)
def test_completed_run_maps_all_malformed_schedule_shapes_to_evidence_error(schedule):
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    with pytest.raises(ScheduledOccupancyEvidenceError) as error:
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=schedule,
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert error.value.capacity_reservation_ids == ("CCR-1",)
    assert "malformed" in error.value.reasons["CCR-1"].lower()


def test_completed_run_rejects_declared_duration_inconsistent_with_timestamps():
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    schedule = _exact_schedule()
    schedule["GanttRows"][0]["Bars"][0]["End"] = "2026-07-20T08:01:00+00:00"
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    with pytest.raises(ScheduledOccupancyEvidenceError) as error:
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=schedule,
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert "timestamp duration" in error.value.reasons["CCR-1"].lower()


def test_completed_run_rejects_schedule_after_latest_allowed_completion():
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    capacities["CCR-1"]["LatestAllowedCompletionAt"] = (
        "2026-07-20T09:30:00+00:00"
    )
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    with pytest.raises(ScheduledOccupancyEvidenceError) as error:
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert "latest allowed completion" in error.value.reasons["CCR-1"].lower()


def test_transition_requires_top_level_selected_ids_to_match_frozen_graph():
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    with pytest.raises(ReservationGraphDriftError, match="selected batch"):
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Failed",
            occurred_at=_occurred_at(),
            batch_ids=[],
            frozen_reservations=frozen,
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )


def test_completed_run_rejects_partial_scheduled_occupancy_evidence():
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    batches["PRB-1"]["CapacityReservationIDs"] = ["CCR-1", "CCR-PARTIAL"]
    capacities["CCR-PARTIAL"] = {
        **capacities["CCR-1"],
        "CapacityReservationID": "CCR-PARTIAL",
        "ReservationLineID": "CAP-PARTIAL",
        "OrderID": "WO-PARTIAL",
        "OperationID": "WO-PARTIAL:CCR",
    }
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    with pytest.raises(ScheduledOccupancyEvidenceError) as error:
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=_demands(),
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert error.value.capacity_reservation_ids == ("CCR-PARTIAL",)


def test_completed_run_converts_only_after_exact_frozen_occupancy_replacement():
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    result = transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Completed",
        occurred_at=_occurred_at(),
        frozen_reservations=frozen,
        schedule=_exact_schedule(),
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    assert result["CapacityReservations"]["CCR-1"]["Status"] == (
        "ConvertedToScheduledOccupancy"
    )
    assert result["CapacityReservations"]["CCR-1"]["RecordVersion"] == 2
    assert result["CapacityReservations"]["CCR-OTHER"] == capacities["CCR-OTHER"]


@pytest.mark.parametrize(
    "drift", ["content", "child_set", "demand", "class", "version"]
)
def test_transition_compare_and_set_rejects_live_graph_drift(drift: str):
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=_demands(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    if drift == "content":
        capacities["CCR-1"]["ReservedMinutes"] = 119
    elif drift == "child_set":
        batches["PRB-1"]["CapacityReservationIDs"].append("CCR-LATE")
        capacities["CCR-LATE"] = {
            **capacities["CCR-1"],
            "CapacityReservationID": "CCR-LATE",
            "ReservationLineID": "CAP-LATE",
            "OperationID": "WO-1:LATE",
        }
    elif drift == "demand":
        capacities["CCR-1"]["DemandCommitmentID"] = "DC-WRONG"
    elif drift == "class":
        allocations["MA-1"]["DemandClass"] = "MTA"
    else:
        capacities["CCR-1"]["RecordVersion"] = 2
    before = deepcopy((batches, capacities, allocations))

    with pytest.raises(ReservationGraphDriftError):
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=_demands(),
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert (batches, capacities, allocations) == before


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    [
        ("PlanningRunID", "RUN-OTHER"),
        ("LastTransitionAt", "2026-07-20T11:59:00+00:00"),
        ("EventType", "PlanningRunCompleted"),
    ],
)
def test_transition_rejects_same_version_lifecycle_provenance_drift(
    field: str,
    drifted_value: str,
):
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    batches["PRB-1"][field] = drifted_value
    before = deepcopy((demands, batches, capacities, allocations))

    with pytest.raises(ReservationGraphDriftError, match="lifecycle provenance"):
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert (demands, batches, capacities, allocations) == before


@pytest.mark.parametrize("drift", ["status", "content", "version", "fingerprint", "missing"])
def test_transition_compare_and_set_rejects_demand_commitment_drift(drift: str):
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    if drift == "status":
        demands[DEMAND_1_ID]["Status"] = "Cancelled"
    elif drift == "content":
        demands[DEMAND_1_ID]["Quantity"] = 2.0
    elif drift == "version":
        demands[DEMAND_1_ID]["RecordVersion"] = 2
    elif drift == "fingerprint":
        demands[DEMAND_1_ID]["ContentFingerprint"] = "sha256:changed"
    else:
        demands.pop(DEMAND_1_ID)
    before = deepcopy((demands, batches, capacities, allocations))

    with pytest.raises(ReservationGraphDriftError):
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert (demands, batches, capacities, allocations) == before


@pytest.mark.parametrize("field", ["GraphID", "GraphVersion", "GraphFingerprint"])
def test_current_frozen_graph_requires_all_integrity_metadata(field: str):
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    frozen.pop(field)

    with pytest.raises(ReservationGraphDriftError, match=field):
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )


def test_explicit_legacy_frozen_graph_fails_closed_with_migration_requirement():
    demands = _demands()
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
        demand_commitments=demands,
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    frozen["GraphFormat"] = "LegacyUnversionedPlanningReservationGraph"

    with pytest.raises(ReservationBatchReferenceError) as error:
        transition_planning_reservations_for_run(
            run_id="RUN-1",
            run_status="Completed",
            occurred_at=_occurred_at(),
            frozen_reservations=frozen,
            schedule=_exact_schedule(),
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )

    assert error.value.status == "PlanningReservationGraphMigrationRequired"
    assert batches["PRB-1"]["Status"] == "ActivePlanReservation"
    assert capacities["CCR-1"]["Status"] == "ActivePlanReservation"


class TestMtoAcceptancePlanningRunBridge:
    """BE-SDBR-006 through BE-SDBR-010 and BE-RUN-011 acceptance evidence."""

    expected_context = {
        "OrderCommitmentEvaluationID": "OCE-MTO-BRIDGE",
        "BaselinePlanningRunID": "RUN-BASELINE",
        "OperatingModelConfigurationID": None,
        "OperatingModelFingerprint": None,
        "SchedulingConfigurationID": None,
        "DDMRPConfigurationID": None,
        "ReleasePolicyVersionID": "RELEASE-BRIDGE",
        "RoutingID": "PRIMARY",
        "BusinessPriority": 10,
        "AcceptedPromiseAt": "2026-07-20T18:00:00+00:00",
        "MaterialCommitmentStatus": "PlannedAllocationPrepared",
        "PendingMaterialRequirements": [],
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    }

    @staticmethod
    def _write_set():
        evaluation = {
            "EvaluationID": "OCE-MTO-BRIDGE",
            "EvaluationFingerprint": "sha256:mto-bridge",
            "Status": "AwaitingPlannerDecision",
            "Order": {
                "SourceSystem": "MockERP",
                "SourceObjectType": "CustomerOrder",
                "OrderID": "SO-BRIDGE",
                "OrderVersion": "1",
                "DemandLineID": "10",
                "PlanningOrderID": "SO-BRIDGE:10",
                "ProductID": "FG-1",
                "LocationID": "MAIN",
                "Quantity": 1.0,
                "Uom": "EA",
                "RequestedDueAt": "2026-07-20T18:00:00+00:00",
                "BusinessPriority": 10,
                "RoutingID": "PRIMARY",
                "TraceID": "TRACE-SO-BRIDGE-10",
            },
            "Basis": {
                "BaselinePlanningRunID": "RUN-BASELINE",
                "OperatingModelConfigurationID": None,
                "OperatingModelFingerprint": None,
                "SchedulingConfigurationID": None,
                "DDMRPConfigurationID": None,
                "ReleasePolicyVersionID": "RELEASE-BRIDGE",
            },
            "ShadowSchedule": {
                "Status": "OnTime",
                "RequestedDateAssessment": {
                    "Feasible": True,
                    "PromiseAt": "2026-07-20T18:00:00+00:00",
                    "ReservationRequests": [
                        {
                            "ReservationLineID": (
                                "SO-BRIDGE:10:CCR-CUT:"
                                "2026-07-20T08:00:00+00:00"
                            ),
                            "OrderID": "SO-BRIDGE:10",
                            "OperationID": "SO-BRIDGE:10:CCR-CUT",
                            "ResourceID": "CCR-1",
                            "WindowStartAt": "2026-07-20T08:00:00+00:00",
                            "WindowEndAt": "2026-07-20T16:00:00+00:00",
                            "ReservedMinutes": 60,
                            "LatestAllowedCompletionAt": (
                                "2026-07-20T16:00:00+00:00"
                            ),
                        }
                    ],
                },
            },
            "MaterialAssessment": {
                "Status": "Feasible",
                "AllocationRequests": [
                    {
                        "RequirementLineID": "SO-BRIDGE:10:RM-1",
                        "ItemID": "RM-1",
                        "LocationID": "MAIN",
                        "Uom": "EA",
                        "AllocatedQty": 5.0,
                        "SupplySourceType": "OnHand",
                        "MaterialSnapshotID": "OPS-BRIDGE",
                    }
                ],
                "PendingRequirements": [],
            },
            "Recommendation": {
                "AllowedActions": [
                    "AcceptRequestedDate",
                    "Reevaluate",
                    "Reject",
                ],
                "RequiresCcrAcknowledgement": False,
                "RequiresMaterialAcknowledgement": False,
            },
        }
        return prepare_mto_acceptance(
            evaluation=evaluation,
            existing_commitments={},
            decision_id="DEC-MTO-BRIDGE",
            decision="AcceptRequestedDate",
            decided_by="planner-bridge",
            decided_at=datetime(2026, 7, 11, 8, tzinfo=timezone.utc),
            reason="Bridge compatibility acceptance.",
            ccr_risk_acknowledged=False,
            material_risk_acknowledged=False,
        )

    @staticmethod
    def _schedule() -> dict[str, object]:
        return {
            "GanttRows": [
                {
                    "ResourceID": "CCR-1",
                    "Bars": [
                        {
                            "OrderID": "SO-BRIDGE:10",
                            "OperationID": "SO-BRIDGE:10:CCR-CUT",
                            "Start": "2026-07-20T08:00:00+00:00",
                            "End": "2026-07-20T09:00:00+00:00",
                            "DurationMinutes": 60,
                        }
                    ],
                }
            ]
        }

    def _accepted_graph(self):
        write_set = self._write_set()
        commitments: dict[str, dict[str, object]] = {}
        batches: dict[str, dict[str, object]] = {}
        capacities: dict[str, dict[str, object]] = {}
        materials: dict[str, dict[str, object]] = {}
        events: list[dict[str, object]] = []
        processed_keys: set[str] = set()
        planning_runs: dict[str, dict[str, object]] = {}
        apply_reservation_write_set(
            write_set=write_set,
            commitments=commitments,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=materials,
            events=events,
            processed_event_keys=processed_keys,
        )
        assert planning_runs == {}
        planning_run = {
            "RunID": "RUN-MTO-BRIDGE",
            "PlanningReservationBatchIDs": [
                write_set.batch["ReservationBatchID"]
            ],
        }
        frozen = freeze_planning_reservations(
            batch_ids=planning_run["PlanningReservationBatchIDs"],
            demand_commitments=commitments,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=materials,
        )
        return write_set, commitments, batches, capacities, materials, planning_run, frozen

    def test_explicit_planning_run_selection_freezes_and_converts_mto_acceptance(
        self,
    ):
        (
            write_set,
            commitments,
            batches,
            capacities,
            materials,
            planning_run,
            frozen,
        ) = self._accepted_graph()

        frozen_demand = frozen["DemandCommitments"][0]
        assert {
            key: frozen_demand.get(key) for key in self.expected_context
        } == self.expected_context

        completed = transition_planning_reservations_for_run(
            run_id=planning_run["RunID"],
            run_status="Completed",
            occurred_at=_occurred_at(),
            batch_ids=planning_run["PlanningReservationBatchIDs"],
            frozen_reservations=frozen,
            schedule=self._schedule(),
            demand_commitments=commitments,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=materials,
        )

        batch_id = write_set.batch["ReservationBatchID"]
        capacity_id = write_set.batch["CapacityReservationIDs"][0]
        material_id = write_set.batch["MaterialAllocationIDs"][0]
        assert completed["Batches"][batch_id]["Status"] == (
            "ConvertedToScheduledOccupancy"
        )
        assert completed["CapacityReservations"][capacity_id]["Status"] == (
            "ConvertedToScheduledOccupancy"
        )
        assert completed["MaterialAllocations"][material_id]["Status"] == (
            "ActivePlanReservation"
        )
        assert completed["Batches"][batch_id]["DemandCommitmentID"] == (
            write_set.demand_commitment["DemandCommitmentID"]
        )
        assert completed["CapacityReservations"][capacity_id]["ReservationBatchID"] == (
            batch_id
        )
        assert completed["MaterialAllocations"][material_id]["ReservationBatchID"] == (
            batch_id
        )
        assert {
            key: commitments[write_set.demand_commitment["DemandCommitmentID"]].get(key)
            for key in self.expected_context
        } == self.expected_context
        assert "DemandCommitments" not in completed

    def test_explicit_planning_run_failure_preserves_mto_reservation_as_held(self):
        (
            write_set,
            commitments,
            batches,
            capacities,
            materials,
            planning_run,
            frozen,
        ) = self._accepted_graph()
        failed_commitments = deepcopy(commitments)
        failed_batches = deepcopy(batches)
        failed_capacities = deepcopy(capacities)
        failed_materials = deepcopy(materials)

        failed = transition_planning_reservations_for_run(
            run_id=planning_run["RunID"],
            run_status="Failed",
            occurred_at=_occurred_at(),
            batch_ids=planning_run["PlanningReservationBatchIDs"],
            frozen_reservations=frozen,
            demand_commitments=failed_commitments,
            batches=failed_batches,
            capacity_reservations=failed_capacities,
            material_allocations=failed_materials,
        )

        batch_id = write_set.batch["ReservationBatchID"]
        capacity_id = write_set.batch["CapacityReservationIDs"][0]
        material_id = write_set.batch["MaterialAllocationIDs"][0]
        assert failed["Batches"][batch_id]["Status"] == "HeldForPlanningError"
        assert failed["CapacityReservations"][capacity_id]["Status"] == (
            "HeldForPlanningError"
        )
        assert failed["MaterialAllocations"][material_id]["Status"] == (
            "HeldForPlanningError"
        )
        assert {
            key: failed_commitments[write_set.demand_commitment["DemandCommitmentID"]].get(key)
            for key in self.expected_context
        } == self.expected_context
        assert "DemandCommitments" not in failed
