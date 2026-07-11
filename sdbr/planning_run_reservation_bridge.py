from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Iterable, Mapping


ELIGIBLE_FREEZE_STATUSES = {"ActivePlanReservation", "LinkedToFormalOrder"}
SUPPORTED_RUN_STATUSES = {"Queued", "Completed", "Failed", "DeadLetter"}


class ReservationBatchReferenceError(ValueError):
    """Raised when a planning run refers to invalid reservation batches."""


def _selected_batch_ids(
    batch_ids: Iterable[str], batches: Mapping[str, Mapping[str, object]]
) -> list[str]:
    selected_ids: list[str] = []
    seen_ids: set[str] = set()
    for batch_id in batch_ids:
        if not isinstance(batch_id, str) or not batch_id:
            raise ReservationBatchReferenceError("Reservation batch ID must be a non-empty string.")
        if batch_id in seen_ids:
            raise ReservationBatchReferenceError(
                f"Requested reservation batch ID is duplicate: {batch_id}."
            )
        seen_ids.add(batch_id)
        batch = batches.get(batch_id)
        if batch is None:
            raise ReservationBatchReferenceError(
                f"Requested reservation batch ID does not exist: {batch_id}."
            )
        if batch.get("Status") not in ELIGIBLE_FREEZE_STATUSES:
            raise ReservationBatchReferenceError(
                f"Requested reservation batch ID is not eligible: {batch_id}."
            )
        selected_ids.append(batch_id)
    return selected_ids


def _linked_record_ids(
    records: Mapping[str, Mapping[str, object]], batch_ids: set[str]
) -> list[str]:
    return [
        record_id
        for record_id, record in records.items()
        if record.get("ReservationBatchID") in batch_ids
    ]


def freeze_planning_reservations(
    *,
    batch_ids: Iterable[str],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Return an isolated planning-run snapshot for explicit eligible batches."""
    selected_ids = _selected_batch_ids(batch_ids, batches)
    selected_id_set = set(selected_ids)
    return {
        "ReservationBatchIDs": deepcopy(selected_ids),
        "Batches": [deepcopy(batches[batch_id]) for batch_id in selected_ids],
        "CapacityReservations": [
            deepcopy(record)
            for record in capacity_reservations.values()
            if record.get("ReservationBatchID") in selected_id_set
        ],
        "MaterialAllocations": [
            deepcopy(record)
            for record in material_allocations.values()
            if record.get("ReservationBatchID") in selected_id_set
        ],
    }


def _validate_transition_inputs(run_status: str, occurred_at: object) -> None:
    if run_status not in SUPPORTED_RUN_STATUSES:
        raise ValueError(f"Unsupported planning run status: {run_status}.")
    if (
        not isinstance(occurred_at, datetime)
        or occurred_at.tzinfo is None
        or occurred_at.utcoffset() is None
    ):
        raise ValueError("Planning run transition time must be timezone-aware.")


def _trace_run_record(
    record: dict[str, object], *, run_id: str, run_status: str, occurred_at: datetime
) -> None:
    record.update(
        {
            "PlanningRunID": run_id,
            "LastTransitionAt": occurred_at.isoformat(),
            "EventType": f"PlanningRun{run_status}",
        }
    )


def transition_planning_reservations_for_run(
    *,
    run_id: str,
    run_status: str,
    batch_ids: Iterable[str],
    occurred_at: datetime,
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, dict[str, object]]]:
    """Copy reservation collections and apply the requested planning-run lifecycle state."""
    _validate_transition_inputs(run_status, occurred_at)
    selected_ids = _selected_batch_ids(batch_ids, batches)
    selected_id_set = set(selected_ids)
    result = {
        "Batches": deepcopy(dict(batches)),
        "CapacityReservations": deepcopy(dict(capacity_reservations)),
        "MaterialAllocations": deepcopy(dict(material_allocations)),
    }
    if run_status == "Queued":
        return result

    batch_records = result["Batches"]
    capacity_records = result["CapacityReservations"]
    material_records = result["MaterialAllocations"]
    for batch_id in selected_ids:
        batch = batch_records[batch_id]
        if run_status == "Completed":
            batch["Status"] = "ConvertedToScheduledOccupancy"
        else:
            batch["Status"] = "HeldForPlanningError"
        _trace_run_record(
            batch, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    for record_id in _linked_record_ids(capacity_records, selected_id_set):
        capacity = capacity_records[record_id]
        if run_status == "Completed":
            capacity["Status"] = "ConvertedToScheduledOccupancy"
        else:
            capacity["Status"] = "HeldForPlanningError"
        _trace_run_record(
            capacity, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    for record_id in _linked_record_ids(material_records, selected_id_set):
        material = material_records[record_id]
        if run_status in {"Failed", "DeadLetter"} and material.get(
            "Status"
        ) == "ActivePlanReservation":
            material["Status"] = "HeldForPlanningError"
        _trace_run_record(
            material, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    return result
