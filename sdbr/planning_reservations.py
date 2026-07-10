from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite
from numbers import Real
from typing import Iterable, Mapping, MutableMapping, MutableSequence, MutableSet

from sdbr.planning_commitments import assert_no_active_predecessor


ACTIVE_CAPACITY_RESERVATION_STATUSES = {
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError"
}
ACTIVE_MATERIAL_ALLOCATION_STATUSES = {
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError"
}


class ReservationConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlanningReservationWriteSet:
    idempotency_key: str
    demand_commitment: dict[str, object]
    batch: dict[str, object]
    capacity_reservations: tuple[dict[str, object], ...]
    material_allocations: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{sha256(value.encode('utf-8')).hexdigest()[:20]}"


def _require_positive(value: object, message: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ReservationConflict(message)
    try:
        normalized_value = float(value)
    except OverflowError as error:
        raise ReservationConflict(message) from error
    if not isfinite(normalized_value) or normalized_value <= 0:
        raise ReservationConflict(message)


def _validate_capacity_requests(rows: tuple[dict[str, object], ...]) -> None:
    for row in rows:
        _require_positive(
            row.get("ReservedMinutes"),
            "Capacity request must have positive reserved minutes.",
        )
        if not row.get("ResourceID") or not row.get("WindowStartAt") or not row.get(
            "WindowEndAt"
        ):
            raise ReservationConflict("Capacity request resource and window are required.")
        window_start = _parse_timezone_aware_iso_datetime(
            row["WindowStartAt"], "WindowStartAt"
        )
        window_end = _parse_timezone_aware_iso_datetime(row["WindowEndAt"], "WindowEndAt")
        if window_end <= window_start:
            raise ReservationConflict(
                "Capacity request window end must be strictly after start."
            )


def _parse_timezone_aware_iso_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ReservationConflict(
            f"Capacity request {field_name} must be an ISO datetime."
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ReservationConflict(
            f"Capacity request {field_name} must be an ISO datetime."
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReservationConflict(
            f"Capacity request {field_name} must be timezone-aware."
        )
    return parsed


def _validate_material_requests(rows: tuple[dict[str, object], ...]) -> None:
    for row in rows:
        _require_positive(
            row.get("AllocatedQty"),
            "Material request must have positive allocated quantity.",
        )
        if not row.get("RequirementLineID") or not row.get("ItemID") or not row.get(
            "LocationID"
        ):
            raise ReservationConflict("Material request identity is required.")


def prepare_reservation_confirmation(
    *,
    demand_commitment: dict[str, object],
    existing_commitments: Mapping[str, dict[str, object]],
    confirmation_id: str,
    confirmed_by: str,
    confirmed_at: datetime,
    capacity_requests: Iterable[Mapping[str, object]],
    material_requests: Iterable[Mapping[str, object]],
) -> PlanningReservationWriteSet:
    demand_id = str(demand_commitment.get("DemandCommitmentID") or "")
    if not demand_id:
        raise ReservationConflict("Demand commitment ID is required.")
    if demand_commitment.get("Status") != "PendingConfirmation":
        raise ReservationConflict("Demand commitment must await confirmation.")
    if confirmed_at.tzinfo is None or confirmed_at.utcoffset() is None:
        raise ReservationConflict("Confirmation time must be timezone-aware.")
    assert_no_active_predecessor(existing_commitments, demand_commitment)

    demand_snapshot = deepcopy(demand_commitment)
    capacity_rows = tuple(deepcopy(dict(row)) for row in capacity_requests)
    material_rows = tuple(deepcopy(dict(row)) for row in material_requests)
    _validate_capacity_requests(capacity_rows)
    _validate_material_requests(material_rows)

    batch_id = _stable_id("PRB", confirmation_id)
    demand_class = demand_snapshot["DemandClass"]
    capacity_records = tuple(
        {
            **row,
            "CapacityReservationID": _stable_id(
                "CCR",
                f"{confirmation_id}|{index}|{row['ResourceID']}|{row['WindowStartAt']}",
            ),
            "ReservationBatchID": batch_id,
            "DemandCommitmentID": demand_id,
            "DemandClass": demand_class,
            "Status": "ActivePlanReservation",
        }
        for index, row in enumerate(capacity_rows, start=1)
    )
    material_records = tuple(
        {
            **row,
            "MaterialAllocationID": _stable_id(
                "MPA", f"{confirmation_id}|{index}|{row['RequirementLineID']}"
            ),
            "ReservationBatchID": batch_id,
            "DemandCommitmentID": demand_id,
            "DemandClass": demand_class,
            "Status": "ActivePlanReservation",
        }
        for index, row in enumerate(material_rows, start=1)
    )
    confirmed_at_value = confirmed_at.isoformat()
    activated_demand = deepcopy(demand_snapshot)
    activated_demand.update(
        {
            "Status": "Active",
            "ConfirmedBy": confirmed_by,
            "ConfirmedAt": confirmed_at_value,
        }
    )
    batch = {
        "ReservationBatchID": batch_id,
        "DemandCommitmentID": demand_id,
        "DemandClass": demand_class,
        "Status": "ActivePlanReservation",
        "ConfirmationID": confirmation_id,
        "ConfirmedBy": confirmed_by,
        "ConfirmedAt": confirmed_at_value,
        "CapacityReservationIDs": [
            row["CapacityReservationID"] for row in capacity_records
        ],
        "MaterialAllocationIDs": [
            row["MaterialAllocationID"] for row in material_records
        ],
    }
    idempotency_key = f"PlanningReservationActivated:{confirmation_id}"
    event = {
        "EventID": _stable_id("PRE", idempotency_key),
        "EventType": "PlanningReservationActivated",
        "DemandCommitmentID": demand_id,
        "ReservationBatchID": batch_id,
        "OccurredAt": confirmed_at_value,
        "ActorID": confirmed_by,
        "IdempotencyKey": idempotency_key,
        "TraceID": demand_snapshot["TraceID"],
    }
    return PlanningReservationWriteSet(
        idempotency_key=idempotency_key,
        demand_commitment=activated_demand,
        batch=batch,
        capacity_reservations=capacity_records,
        material_allocations=material_records,
        events=(event,),
    )


def _assert_no_conflicting_record(
    records: Mapping[str, dict[str, object]],
    record_id: str,
    candidate: dict[str, object],
) -> None:
    existing = records.get(record_id)
    if existing is not None and existing != candidate:
        raise ReservationConflict("Reservation target ID already exists with different content.")


def _assert_no_conflicting_event(
    events: MutableSequence[dict[str, object]], candidate: dict[str, object]
) -> None:
    event_id = str(candidate["EventID"])
    for existing in events:
        if existing.get("EventID") == event_id and existing != candidate:
            raise ReservationConflict("Reservation target ID already exists with different content.")


def _assert_no_duplicate_ids(
    records: Iterable[dict[str, object]], record_id_field: str
) -> None:
    seen: dict[str, dict[str, object]] = {}
    for record in records:
        record_id = str(record[record_id_field])
        existing = seen.get(record_id)
        if existing is None:
            seen[record_id] = record
        elif existing != record:
            raise ReservationConflict(
                "Reservation write set contains duplicate target ID with different content."
            )
        else:
            raise ReservationConflict("Reservation write set contains duplicate target ID.")


def apply_reservation_write_set(
    *,
    write_set: PlanningReservationWriteSet,
    commitments: MutableMapping[str, dict[str, object]],
    batches: MutableMapping[str, dict[str, object]],
    capacity_reservations: MutableMapping[str, dict[str, object]],
    material_allocations: MutableMapping[str, dict[str, object]],
    events: MutableSequence[dict[str, object]],
    processed_event_keys: MutableSet[str],
) -> None:
    if write_set.idempotency_key in processed_event_keys:
        return

    demand_id = str(write_set.demand_commitment["DemandCommitmentID"])
    batch_id = str(write_set.batch["ReservationBatchID"])
    _assert_no_duplicate_ids(
        write_set.capacity_reservations, "CapacityReservationID"
    )
    _assert_no_duplicate_ids(write_set.material_allocations, "MaterialAllocationID")
    _assert_no_duplicate_ids(write_set.events, "EventID")
    _assert_no_conflicting_record(commitments, demand_id, write_set.demand_commitment)
    _assert_no_conflicting_record(batches, batch_id, write_set.batch)
    for record in write_set.capacity_reservations:
        _assert_no_conflicting_record(
            capacity_reservations, str(record["CapacityReservationID"]), record
        )
    for record in write_set.material_allocations:
        _assert_no_conflicting_record(
            material_allocations, str(record["MaterialAllocationID"]), record
        )
    for event in write_set.events:
        _assert_no_conflicting_event(events, event)

    commitments.setdefault(demand_id, deepcopy(write_set.demand_commitment))
    batches.setdefault(batch_id, deepcopy(write_set.batch))
    for record in write_set.capacity_reservations:
        capacity_reservations.setdefault(
            str(record["CapacityReservationID"]), deepcopy(record)
        )
    for record in write_set.material_allocations:
        material_allocations.setdefault(
            str(record["MaterialAllocationID"]), deepcopy(record)
        )
    existing_event_ids = {event.get("EventID") for event in events}
    for event in write_set.events:
        if event["EventID"] not in existing_event_ids:
            events.append(deepcopy(event))
    processed_event_keys.add(write_set.idempotency_key)
