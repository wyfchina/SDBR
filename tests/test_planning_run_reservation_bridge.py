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
            "DemandCommitmentID": "DC-1",
            "DemandClass": "MTO",
            "Status": status,
            "CapacityReservationIDs": ["CCR-1"],
            "MaterialAllocationIDs": ["MA-1"],
            "Details": {"source": "planner-confirmation"},
        },
        "PRB-2": {
            "ReservationBatchID": "PRB-2",
            "DemandCommitmentID": "DC-2",
            "DemandClass": "MTA",
            "Status": "LinkedToFormalOrder",
            "CapacityReservationIDs": ["CCR-2"],
            "MaterialAllocationIDs": ["MA-2"],
        },
    }


def _capacities(*, status: str = "ActivePlanReservation") -> dict[str, dict[str, object]]:
    return {
        "CCR-1": {
            "CapacityReservationID": "CCR-1",
            "ReservationBatchID": "PRB-1",
            "Status": status,
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
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=allocations,
        )
    return transition_planning_reservations_for_run(
        run_id="RUN-1",
        run_status="Completed",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
    )


def test_freeze_copies_only_explicit_eligible_batches_in_caller_and_ledger_order():
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
        "CCR-2",
        "CCR-1",
    ]
    assert [row["MaterialAllocationID"] for row in frozen["MaterialAllocations"]] == [
        "MA-2",
        "MA-1",
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


def test_freeze_deep_copies_selected_batches_and_declared_children_without_aliasing():
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
    assert frozen["MaterialAllocations"][0]["Details"] == {
        "item": "changed-result"
    }


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


def test_completed_recovery_restores_only_material_held_by_planning_error():
    batches = _batches(status="HeldForPlanningError")
    capacities = _capacities(status="HeldForPlanningError")
    allocations = _allocations(status="HeldForPlanningError")
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
                "Status": "LinkedToFormalOrder",
            },
            "MA-EXTERNAL": {
                "MaterialAllocationID": "MA-EXTERNAL",
                "ReservationBatchID": "PRB-1",
                "Status": "Externalized",
            },
            "MA-OTHER-AUTHORITY": {
                "MaterialAllocationID": "MA-OTHER-AUTHORITY",
                "ReservationBatchID": "PRB-1",
                "Status": "AuthorityTransferred",
            },
        }
    )

    result = transition_planning_reservations_for_run(
        run_id="RUN-RECOVERY",
        run_status="Completed",
        batch_ids=["PRB-1"],
        occurred_at=_occurred_at(),
        batches=batches,
        capacity_reservations=capacities,
        material_allocations=allocations,
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
    assert result["MaterialAllocations"]["MA-EXTERNAL"]["Status"] == "Externalized"
    assert (
        result["MaterialAllocations"]["MA-OTHER-AUTHORITY"]["Status"]
        == "AuthorityTransferred"
    )


@pytest.mark.parametrize("malformed_batch_id", [[], {"bad": "id"}])
def test_rejects_unhashable_child_batch_identity_as_reference_error(
    malformed_batch_id: object,
):
    capacities = _capacities()
    capacities["CCR-1"]["ReservationBatchID"] = malformed_batch_id

    with pytest.raises(ReservationBatchReferenceError, match="identity"):
        freeze_planning_reservations(
            batch_ids=["PRB-1"],
            batches=_batches(),
            capacity_reservations=capacities,
            material_allocations=_allocations(),
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
