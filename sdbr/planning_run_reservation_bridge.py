from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Iterable, Mapping


ELIGIBLE_FREEZE_STATUSES = {"ActivePlanReservation", "LinkedToFormalOrder"}
ELIGIBLE_TRANSITION_STATUSES = ELIGIBLE_FREEZE_STATUSES | {"HeldForPlanningError"}
SUPPORTED_RUN_STATUSES = {"Queued", "Completed", "Failed", "DeadLetter"}


class ReservationBatchReferenceError(ValueError):
    """Raised when a planning run refers to an invalid reservation batch graph."""


def _require_identity(value: object, field_name: str, record_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReservationBatchReferenceError(
            f"{record_name} identity field {field_name} is required."
        )
    return value


def _selected_batch_ids(
    batch_ids: Iterable[str],
    batches: Mapping[str, Mapping[str, object]],
    *,
    require_freeze_eligibility: bool,
) -> list[str]:
    selected_ids: list[str] = []
    seen_ids: set[str] = set()
    eligible_statuses = (
        ELIGIBLE_FREEZE_STATUSES
        if require_freeze_eligibility
        else ELIGIBLE_TRANSITION_STATUSES
    )
    for batch_id in batch_ids:
        if not isinstance(batch_id, str) or not batch_id:
            raise ReservationBatchReferenceError(
                "Reservation batch ID must be a non-empty string."
            )
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
        if not isinstance(batch, Mapping):
            raise ReservationBatchReferenceError(
                f"Reservation batch identity is invalid: {batch_id}."
            )
        canonical_batch_id = _require_identity(
            batch.get("ReservationBatchID"), "ReservationBatchID", "Reservation batch"
        )
        if canonical_batch_id != batch_id:
            raise ReservationBatchReferenceError(
                f"Reservation batch canonical ID does not match mapping key: {batch_id}."
            )
        if batch.get("Status") not in eligible_statuses:
            raise ReservationBatchReferenceError(
                f"Requested reservation batch ID is not eligible: {batch_id}."
            )
        selected_ids.append(batch_id)
    return selected_ids


def _declared_child_ids(
    batch: Mapping[str, object],
    *,
    batch_id: str,
    list_field: str,
    record_name: str,
) -> list[str]:
    child_ids = batch.get(list_field)
    if not isinstance(child_ids, list):
        raise ReservationBatchReferenceError(
            f"Reservation batch {batch_id} {list_field} must be a list."
        )

    declared_ids: list[str] = []
    seen_ids: set[str] = set()
    for child_id in child_ids:
        canonical_child_id = _require_identity(
            child_id, list_field, f"Reservation batch {batch_id} {record_name}"
        )
        if canonical_child_id in seen_ids:
            raise ReservationBatchReferenceError(
                f"Reservation batch {batch_id} has duplicate canonical {record_name} ID: "
                f"{canonical_child_id}."
            )
        seen_ids.add(canonical_child_id)
        declared_ids.append(canonical_child_id)
    return declared_ids


def _resolve_declared_child_ids(
    *,
    records: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    selected_batch_ids: list[str],
    list_field: str,
    child_id_field: str,
    record_name: str,
) -> list[str]:
    declared_children: list[tuple[str, str]] = []
    declared_ids_by_batch: dict[str, set[str]] = {}
    seen_declared_ids: set[str] = set()
    for batch_id in selected_batch_ids:
        declared_ids = _declared_child_ids(
            batches[batch_id],
            batch_id=batch_id,
            list_field=list_field,
            record_name=record_name,
        )
        declared_ids_by_batch[batch_id] = set(declared_ids)
        for child_id in declared_ids:
            if child_id in seen_declared_ids:
                raise ReservationBatchReferenceError(
                    f"Selected batches have duplicate canonical {record_name} ID: {child_id}."
                )
            seen_declared_ids.add(child_id)
            declared_children.append((batch_id, child_id))

    selected_batch_id_set = set(selected_batch_ids)
    canonical_ids: set[str] = set()
    for mapping_key, record in records.items():
        if not isinstance(record, Mapping):
            continue
        child_batch_id = record.get("ReservationBatchID")
        if not isinstance(child_batch_id, str) or not child_batch_id:
            continue
        if child_batch_id not in selected_batch_id_set:
            continue
        canonical_child_id = _require_identity(
            record.get(child_id_field), child_id_field, record_name
        )
        if canonical_child_id in canonical_ids:
            raise ReservationBatchReferenceError(
                f"Selected {record_name} records have duplicate canonical ID: "
                f"{canonical_child_id}."
            )
        canonical_ids.add(canonical_child_id)
        if mapping_key != canonical_child_id:
            raise ReservationBatchReferenceError(
                f"{record_name} canonical ID must match its mapping key and batch ledger ID: "
                f"{canonical_child_id}."
            )
        if canonical_child_id not in declared_ids_by_batch[child_batch_id]:
            raise ReservationBatchReferenceError(
                f"{record_name} is an orphan for selected ReservationBatchID: "
                f"{child_batch_id}."
            )

    resolved_ids: list[str] = []
    for batch_id, child_id in declared_children:
        record = records.get(child_id)
        if record is None:
            raise ReservationBatchReferenceError(
                f"Declared {record_name} child is missing: {child_id}."
            )
        if not isinstance(record, Mapping):
            raise ReservationBatchReferenceError(
                f"{record_name} identity is invalid for declared child: {child_id}."
            )
        canonical_child_id = _require_identity(
            record.get(child_id_field), child_id_field, record_name
        )
        child_batch_id = _require_identity(
            record.get("ReservationBatchID"), "ReservationBatchID", record_name
        )
        if canonical_child_id != child_id:
            raise ReservationBatchReferenceError(
                f"{record_name} canonical ID must match its mapping key and batch ledger ID: "
                f"{child_id}."
            )
        if child_batch_id != batch_id:
            raise ReservationBatchReferenceError(
                f"{record_name} has wrong ReservationBatchID for declared child: "
                f"{child_id}."
            )
        resolved_ids.append(child_id)
    return resolved_ids


def _resolve_batch_graph(
    *,
    batch_ids: Iterable[str],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
    require_freeze_eligibility: bool,
) -> tuple[list[str], list[str], list[str]]:
    selected_ids = _selected_batch_ids(
        batch_ids,
        batches,
        require_freeze_eligibility=require_freeze_eligibility,
    )
    capacity_ids = _resolve_declared_child_ids(
        records=capacity_reservations,
        batches=batches,
        selected_batch_ids=selected_ids,
        list_field="CapacityReservationIDs",
        child_id_field="CapacityReservationID",
        record_name="Capacity reservation",
    )
    material_ids = _resolve_declared_child_ids(
        records=material_allocations,
        batches=batches,
        selected_batch_ids=selected_ids,
        list_field="MaterialAllocationIDs",
        child_id_field="MaterialAllocationID",
        record_name="Material allocation",
    )
    return selected_ids, capacity_ids, material_ids


def freeze_planning_reservations(
    *,
    batch_ids: Iterable[str],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Return an isolated snapshot of complete, explicit eligible reservation batches."""
    selected_ids, capacity_ids, material_ids = _resolve_batch_graph(
        batch_ids=batch_ids,
        batches=batches,
        capacity_reservations=capacity_reservations,
        material_allocations=material_allocations,
        require_freeze_eligibility=True,
    )
    return {
        "ReservationBatchIDs": deepcopy(selected_ids),
        "Batches": [deepcopy(batches[batch_id]) for batch_id in selected_ids],
        "CapacityReservations": [
            deepcopy(capacity_reservations[capacity_id]) for capacity_id in capacity_ids
        ],
        "MaterialAllocations": [
            deepcopy(material_allocations[material_id]) for material_id in material_ids
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
    """Copy a complete reservation batch graph and apply its planning-run lifecycle."""
    _validate_transition_inputs(run_status, occurred_at)
    selected_ids, capacity_ids, material_ids = _resolve_batch_graph(
        batch_ids=batch_ids,
        batches=batches,
        capacity_reservations=capacity_reservations,
        material_allocations=material_allocations,
        require_freeze_eligibility=False,
    )
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
        batch["Status"] = (
            "ConvertedToScheduledOccupancy"
            if run_status == "Completed"
            else "HeldForPlanningError"
        )
        _trace_run_record(
            batch, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    for capacity_id in capacity_ids:
        capacity = capacity_records[capacity_id]
        capacity["Status"] = (
            "ConvertedToScheduledOccupancy"
            if run_status == "Completed"
            else "HeldForPlanningError"
        )
        _trace_run_record(
            capacity, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    for material_id in material_ids:
        material = material_records[material_id]
        if run_status in {"Failed", "DeadLetter"} and material.get(
            "Status"
        ) == "ActivePlanReservation":
            material["Status"] = "HeldForPlanningError"
        elif (
            run_status == "Completed"
            and material.get("Status") == "HeldForPlanningError"
        ):
            material["Status"] = "ActivePlanReservation"
        _trace_run_record(
            material, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    return result
