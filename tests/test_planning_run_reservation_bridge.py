"""Acceptance evidence for BE-RUN-011 and BE-SDBR-007, BE-SDBR-008, BE-SDBR-009."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from sdbr.planning_run_reservation_bridge import (
    ReservationBatchReferenceError,
    freeze_planning_reservations,
    transition_planning_reservations_for_run,
)


def _batches(*, status: str = "ActivePlanReservation") -> dict[str, dict[str, object]]:
    return {
        "PRB-1": {
            "ReservationBatchID": "PRB-1",
            "Status": status,
            "Details": {"source": "planner-confirmation"},
        },
        "PRB-2": {
            "ReservationBatchID": "PRB-2",
            "Status": "LinkedToFormalOrder",
        },
    }


def _capacities() -> dict[str, dict[str, object]]:
    return {
        "CCR-1": {
            "CapacityReservationID": "CCR-1",
            "ReservationBatchID": "PRB-1",
            "Status": "ActivePlanReservation",
            "Details": {"resource": "CCR-A"},
        },
        "CCR-2": {
            "CapacityReservationID": "CCR-2",
            "ReservationBatchID": "PRB-2",
            "Status": "LinkedToFormalOrder",
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
            "Status": status,
            "Details": {"item": "RM-1"},
        },
        "MA-2": {
            "MaterialAllocationID": "MA-2",
            "ReservationBatchID": "PRB-2",
            "Status": "LinkedToFormalOrder",
        },
        "MA-OTHER": {
            "MaterialAllocationID": "MA-OTHER",
            "ReservationBatchID": "OTHER",
            "Status": "ActivePlanReservation",
        },
    }


def _occurred_at() -> datetime:
    return datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


def test_freeze_copies_only_explicit_eligible_batches_in_caller_order():
    frozen = freeze_planning_reservations(
        batch_ids=["PRB-2", "PRB-1"],
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
        "CCR-1",
        "CCR-2",
    ]
    assert [row["MaterialAllocationID"] for row in frozen["MaterialAllocations"]] == [
        "MA-1",
        "MA-2",
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
            batches=batches,
            capacity_reservations=_capacities(),
            material_allocations=_allocations(),
        )


def test_freeze_deep_copies_selected_batches_and_linked_children_without_aliasing():
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()

    frozen = freeze_planning_reservations(
        batch_ids=["PRB-1"],
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
    assert frozen["MaterialAllocations"][0]["Details"] == {"item": "changed-result"}


def test_completed_run_converts_capacity_but_keeps_material_until_authority_handoff():
    result = transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Completed",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        batches=_batches(),
        capacity_reservations=_capacities(),
        material_allocations=_allocations(),
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


def test_queued_run_returns_linked_record_copies_without_premature_transition():
    batches = _batches()
    capacities = _capacities()
    allocations = _allocations()

    result = transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Queued",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )

    assert result["Batches"]["PRB-1"]["Status"] == "ActivePlanReservation"
    assert result["CapacityReservations"]["CCR-1"]["Status"] == "ActivePlanReservation"
    assert result["MaterialAllocations"]["MA-1"]["Status"] == "ActivePlanReservation"
    assert "PlanningRunID" not in result["Batches"]["PRB-1"]
    result["Batches"]["PRB-1"]["Details"]["source"] = "changed-result"  # type: ignore[index]
    assert batches["PRB-1"]["Details"] == {"source": "planner-confirmation"}
    assert capacities == _capacities()
    assert allocations == _allocations()


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
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )
    result["Batches"]["PRB-1"]["Details"]["source"] = "changed-result"  # type: ignore[index]
    result["CapacityReservations"]["CCR-1"]["Details"]["resource"] = "changed-result"  # type: ignore[index]
    result["MaterialAllocations"]["MA-1"]["Details"]["item"] = "changed-result"  # type: ignore[index]

    assert (batches, capacities, allocations) == before
