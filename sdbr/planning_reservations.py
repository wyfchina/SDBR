from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
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
TERMINAL_RESERVATION_BATCH_STATUSES = {
    "ConvertedToScheduledOccupancy",
    "Released",
    "Cancelled",
    "Rejected",
}


class ReservationConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlanningReservationWriteSet:
    idempotency_key: str
    payload_fingerprint: str
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
    line_ids: set[str] = set()
    correlations: set[tuple[str, str]] = set()
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
        line_id = _required_string(
            row.get("ReservationLineID"), "Capacity ReservationLineID is required."
        )
        order_id = _required_string(
            row.get("OrderID"), "Capacity OrderID correlation is required."
        )
        operation_id = _required_string(
            row.get("OperationID"), "Capacity OperationID correlation is required."
        )
        if line_id in line_ids or (order_id, operation_id) in correlations:
            raise ReservationConflict(
                "Capacity request contains a duplicate semantic reservation line."
            )
        line_ids.add(line_id)
        correlations.add((order_id, operation_id))


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
    requirement_line_ids: set[str] = set()
    for row in rows:
        _require_positive(
            row.get("AllocatedQty"),
            "Material request must have positive allocated quantity.",
        )
        if not row.get("RequirementLineID") or not row.get("ItemID") or not row.get(
            "LocationID"
        ):
            raise ReservationConflict("Material request identity is required.")
        requirement_line_id = _required_string(
            row.get("RequirementLineID"), "Material RequirementLineID is required."
        )
        if requirement_line_id in requirement_line_ids:
            raise ReservationConflict(
                "Material request contains a duplicate semantic requirement line."
            )
        requirement_line_ids.add(requirement_line_id)


def _required_string(value: object, message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReservationConflict(message)
    return value


def _fingerprint(payload: object) -> str:
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ReservationConflict(
            "Reservation payload must contain canonical JSON-compatible content."
        ) from error
    return f"sha256:{sha256(encoded).hexdigest()}"


def _write_set_business_payload(
    *,
    demand_commitment: Mapping[str, object],
    batch: Mapping[str, object],
    capacity_reservations: Iterable[Mapping[str, object]],
    material_allocations: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "DemandCommitment": {
            key: value
            for key, value in demand_commitment.items()
            if key != "TraceID"
        },
        "Batch": dict(batch),
        "CapacityReservations": [dict(row) for row in capacity_reservations],
        "MaterialAllocations": [dict(row) for row in material_allocations],
    }


def _write_set_result(
    *,
    demand_commitment: Mapping[str, object],
    batch: Mapping[str, object],
) -> dict[str, object]:
    return {
        "DemandCommitmentID": demand_commitment["DemandCommitmentID"],
        "ReservationBatchID": batch["ReservationBatchID"],
        "CapacityReservationIDs": list(batch["CapacityReservationIDs"]),
        "MaterialAllocationIDs": list(batch["MaterialAllocationIDs"]),
    }


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
    capacity_rows = tuple(
        sorted(capacity_rows, key=lambda row: str(row["ReservationLineID"]))
    )
    material_rows = tuple(
        sorted(material_rows, key=lambda row: str(row["RequirementLineID"]))
    )

    batch_id = _stable_id("PRB", confirmation_id)
    demand_class = demand_snapshot["DemandClass"]
    capacity_records = tuple(
        {
            **row,
            "CapacityReservationID": _stable_id(
                "CCR",
                f"{confirmation_id}|{row['ReservationLineID']}",
            ),
            "ReservationBatchID": batch_id,
            "DemandCommitmentID": demand_id,
            "DemandClass": demand_class,
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
        }
        for row in capacity_rows
    )
    material_records = tuple(
        {
            **row,
            "MaterialAllocationID": _stable_id(
                "MPA", f"{confirmation_id}|{row['RequirementLineID']}"
            ),
            "ReservationBatchID": batch_id,
            "DemandCommitmentID": demand_id,
            "DemandClass": demand_class,
            "Status": "ActivePlanReservation",
            "RecordVersion": 1,
        }
        for row in material_rows
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
        "RecordVersion": 1,
    }
    idempotency_key = f"PlanningReservationActivated:{confirmation_id}"
    payload_fingerprint = _fingerprint(
        _write_set_business_payload(
            demand_commitment=activated_demand,
            batch=batch,
            capacity_reservations=capacity_records,
            material_allocations=material_records,
        )
    )
    result = _write_set_result(
        demand_commitment=activated_demand,
        batch=batch,
    )
    event = {
        "EventID": _stable_id("PRE", idempotency_key),
        "EventType": "PlanningReservationActivated",
        "DemandCommitmentID": demand_id,
        "ReservationBatchID": batch_id,
        "OccurredAt": confirmed_at_value,
        "ActorID": confirmed_by,
        "IdempotencyKey": idempotency_key,
        "TraceID": demand_snapshot["TraceID"],
        "PayloadFingerprint": payload_fingerprint,
        "Result": result,
    }
    return PlanningReservationWriteSet(
        idempotency_key=idempotency_key,
        payload_fingerprint=payload_fingerprint,
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


def _current_write_set_fingerprint(write_set: PlanningReservationWriteSet) -> str:
    return _fingerprint(
        _write_set_business_payload(
            demand_commitment=write_set.demand_commitment,
            batch=write_set.batch,
            capacity_reservations=write_set.capacity_reservations,
            material_allocations=write_set.material_allocations,
        )
    )


def _assert_write_set_fingerprint_and_result(
    write_set: PlanningReservationWriteSet,
) -> tuple[str, dict[str, object]]:
    current_fingerprint = _current_write_set_fingerprint(write_set)
    expected_result = _write_set_result(
        demand_commitment=write_set.demand_commitment,
        batch=write_set.batch,
    )
    if current_fingerprint != write_set.payload_fingerprint:
        raise ReservationConflict(
            "Reservation write set payload fingerprint does not match its content."
        )
    for event in write_set.events:
        if (
            event.get("PayloadFingerprint") != current_fingerprint
            or event.get("Result") != expected_result
        ):
            raise ReservationConflict(
                "Reservation event payload fingerprint or result is inconsistent."
            )
    return current_fingerprint, expected_result


def _assert_idempotent_replay_matches(
    *,
    write_set: PlanningReservationWriteSet,
    commitments: Mapping[str, dict[str, object]],
    batches: Mapping[str, dict[str, object]],
    capacity_reservations: Mapping[str, dict[str, object]],
    material_allocations: Mapping[str, dict[str, object]],
    events: MutableSequence[dict[str, object]],
    current_fingerprint: str,
    expected_result: dict[str, object],
) -> None:
    matching_events = [
        event
        for event in events
        if event.get("IdempotencyKey") == write_set.idempotency_key
    ]
    if len(matching_events) != 1:
        raise ReservationConflict(
            "Processed reservation idempotency key has no unique persisted result."
        )
    persisted_event = matching_events[0]
    if (
        "PayloadFingerprint" not in persisted_event
        and "Result" not in persisted_event
        and _legacy_replay_matches_stored_result(
            write_set=write_set,
            persisted_event=persisted_event,
            commitments=commitments,
            batches=batches,
            capacity_reservations=capacity_reservations,
            material_allocations=material_allocations,
        )
    ):
        return
    if (
        persisted_event.get("PayloadFingerprint") != current_fingerprint
        or persisted_event.get("Result") != expected_result
    ):
        raise ReservationConflict(
            "Reservation idempotency key was already used with different content."
        )


def _legacy_normalized_record(
    record: Mapping[str, object],
    *,
    demand: bool = False,
) -> dict[str, object]:
    normalized = deepcopy(dict(record))
    if demand:
        normalized.pop("ContentFingerprint", None)
        normalized.pop("TraceID", None)
    else:
        normalized.setdefault("RecordVersion", 1)
    for field in ("RequiredAt", "ConfirmedAt"):
        value = normalized.get(field)
        if not isinstance(value, str):
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            normalized[field] = parsed.astimezone(timezone.utc).isoformat()
    return normalized


def _legacy_replay_matches_stored_result(
    *,
    write_set: PlanningReservationWriteSet,
    persisted_event: Mapping[str, object],
    commitments: Mapping[str, dict[str, object]],
    batches: Mapping[str, dict[str, object]],
    capacity_reservations: Mapping[str, dict[str, object]],
    material_allocations: Mapping[str, dict[str, object]],
) -> bool:
    demand_id = str(write_set.demand_commitment["DemandCommitmentID"])
    batch_id = str(write_set.batch["ReservationBatchID"])
    stored_demand = commitments.get(demand_id)
    stored_batch = batches.get(batch_id)
    if stored_demand is None or stored_batch is None:
        return False
    if _legacy_normalized_record(
        stored_demand, demand=True
    ) != _legacy_normalized_record(write_set.demand_commitment, demand=True):
        return False
    if _legacy_normalized_record(stored_batch) != _legacy_normalized_record(
        write_set.batch
    ):
        return False
    for candidate in write_set.capacity_reservations:
        record_id = str(candidate["CapacityReservationID"])
        stored = capacity_reservations.get(record_id)
        if stored is None or _legacy_normalized_record(
            stored
        ) != _legacy_normalized_record(candidate):
            return False
    for candidate in write_set.material_allocations:
        record_id = str(candidate["MaterialAllocationID"])
        stored = material_allocations.get(record_id)
        if stored is None or _legacy_normalized_record(
            stored
        ) != _legacy_normalized_record(candidate):
            return False
    candidate_events = [
        event
        for event in write_set.events
        if event.get("IdempotencyKey") == write_set.idempotency_key
    ]
    if len(candidate_events) != 1:
        return False
    persisted_core = {
        key: value
        for key, value in persisted_event.items()
        if key not in {"PayloadFingerprint", "Result"}
    }
    candidate_core = {
        key: value
        for key, value in candidate_events[0].items()
        if key not in {"PayloadFingerprint", "Result"}
    }
    return persisted_core == candidate_core


def _assert_one_non_terminal_batch_per_demand(
    *,
    batches: Mapping[str, dict[str, object]],
    candidate_batch_id: str,
    demand_commitment_id: str,
) -> None:
    for existing_batch_id, existing in batches.items():
        if existing_batch_id == candidate_batch_id:
            continue
        if existing.get("DemandCommitmentID") != demand_commitment_id:
            continue
        if existing.get("Status") not in TERMINAL_RESERVATION_BATCH_STATUSES:
            raise ReservationConflict(
                "Demand commitment already has a non-terminal reservation batch."
            )


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
    demand_id = str(write_set.demand_commitment["DemandCommitmentID"])
    batch_id = str(write_set.batch["ReservationBatchID"])
    _assert_no_duplicate_ids(
        write_set.capacity_reservations, "CapacityReservationID"
    )
    _assert_no_duplicate_ids(write_set.material_allocations, "MaterialAllocationID")
    _assert_no_duplicate_ids(write_set.events, "EventID")
    current_fingerprint, expected_result = _assert_write_set_fingerprint_and_result(
        write_set
    )
    if write_set.idempotency_key in processed_event_keys:
        _assert_idempotent_replay_matches(
            write_set=write_set,
            commitments=commitments,
            batches=batches,
            capacity_reservations=capacity_reservations,
            material_allocations=material_allocations,
            events=events,
            current_fingerprint=current_fingerprint,
            expected_result=expected_result,
        )
        return

    _assert_one_non_terminal_batch_per_demand(
        batches=batches,
        candidate_batch_id=batch_id,
        demand_commitment_id=demand_id,
    )
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
