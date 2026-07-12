from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Iterable, Mapping, MutableMapping, MutableSequence, MutableSet

from sdbr.planning_commitments import (
    assert_no_active_predecessor,
    normalize_demand_commitment,
)


ACTIVE_CAPACITY_RESERVATION_STATUSES = {
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError"
}
ACTIVE_MATERIAL_ALLOCATION_STATUSES = {
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError"
}


class ReservationConflict(ValueError):
    status = "PlanningReservationConflict"


class ReservationLegacyMigrationRequired(ReservationConflict):
    status = "PlanningReservationLegacyMigrationRequired"


_REPLAY_TRANSITION_FIELDS = {
    "Status",
    "RecordVersion",
    "PlanningRunID",
    "LastTransitionAt",
    "EventType",
}
_DEMAND_REPLAY_STATUSES = {
    "Active",
    "LinkedToFormalOrder",
    "HeldForPlanningError",
    "AdjustmentRequired",
    "Released",
    "Superseded",
    "Cancelled",
}
_RESERVATION_REPLAY_STATUSES = {
    "ActivePlanReservation",
    "LinkedToFormalOrder",
    "ConvertedToScheduledOccupancy",
    "HeldForPlanningError",
    "AdjustmentRequired",
    "Released",
    "Cancelled",
    "Rejected",
}
_MATERIAL_REPLAY_STATUSES = _RESERVATION_REPLAY_STATUSES | {
    "Externalized",
    "AuthorityTransferred",
}
_MATERIAL_AUTHORITY_STATUSES = {"Externalized", "AuthorityTransferred"}


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
        if not isinstance(row.get("LatestAllowedCompletionAt"), str) or not str(
            row.get("LatestAllowedCompletionAt")
        ).strip():
            raise ReservationConflict(
                "Capacity request LatestAllowedCompletionAt is required."
            )
        latest_allowed_completion = _parse_timezone_aware_iso_datetime(
            row["LatestAllowedCompletionAt"],
            "LatestAllowedCompletionAt",
        )
        if not (
            window_start < latest_allowed_completion <= window_end
        ):
            raise ReservationConflict(
                "Capacity request LatestAllowedCompletionAt must be inside the "
                "reservation window."
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
    confirmation_context: Mapping[str, object] | None = None,
) -> PlanningReservationWriteSet:
    try:
        demand_snapshot = normalize_demand_commitment(demand_commitment)
    except ValueError as error:
        raise ReservationConflict(
            f"Demand commitment identity or content is invalid: {error}"
        ) from error
    demand_id = str(demand_snapshot["DemandCommitmentID"])
    if demand_snapshot.get("Status") != "PendingConfirmation":
        raise ReservationConflict("Demand commitment must await confirmation.")
    if confirmed_at.tzinfo is None or confirmed_at.utcoffset() is None:
        raise ReservationConflict("Confirmation time must be timezone-aware.")
    assert_no_active_predecessor(existing_commitments, demand_snapshot)

    demand_snapshot = deepcopy(demand_snapshot)
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
            "RecordVersion": int(demand_snapshot.get("RecordVersion", 1)),
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
    if confirmation_context is not None:
        batch["ConfirmationContext"] = deepcopy(dict(confirmation_context))
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


def _replay_record(
    *,
    records: Mapping[str, dict[str, object]],
    record_id: str,
    id_field: str,
    record_name: str,
) -> dict[str, object]:
    record = records.get(record_id)
    if not isinstance(record, Mapping):
        raise ReservationLegacyMigrationRequired(
            f"Persisted reservation replay is missing verifiable {record_name} "
            f"{record_id}."
        )
    if record.get(id_field) != record_id:
        raise ReservationLegacyMigrationRequired(
            f"Persisted reservation replay {record_name} identity is unverifiable."
        )
    return dict(record)


def _assert_replay_record_content(
    *,
    persisted: Mapping[str, object],
    candidate: Mapping[str, object],
    record_name: str,
    allowed_statuses: set[str],
    allow_material_authority_handoff: bool = False,
) -> None:
    persisted_status = persisted.get("Status")
    if persisted_status not in allowed_statuses:
        raise ReservationConflict(
            f"Persisted reservation replay {record_name} has an unsupported "
            "lifecycle status."
        )
    persisted_version = persisted.get("RecordVersion")
    candidate_version = candidate.get("RecordVersion")
    if (
        isinstance(persisted_version, bool)
        or not isinstance(persisted_version, int)
        or isinstance(candidate_version, bool)
        or not isinstance(candidate_version, int)
        or persisted_version < candidate_version
    ):
        raise ReservationLegacyMigrationRequired(
            f"Persisted reservation replay {record_name} version is unverifiable."
        )
    mutable_fields = set(_REPLAY_TRANSITION_FIELDS)
    if (
        allow_material_authority_handoff
        and persisted_status in _MATERIAL_AUTHORITY_STATUSES
        and persisted_version > candidate_version
        and isinstance(persisted.get("ExternalAllocationRef"), str)
        and str(persisted.get("ExternalAllocationRef")).strip()
        and isinstance(persisted.get("MaterialSnapshotID"), str)
        and str(persisted.get("MaterialSnapshotID")).strip()
        and persisted.get("MaterialSnapshotID") != candidate.get("MaterialSnapshotID")
    ):
        mutable_fields.update({"ExternalAllocationRef", "MaterialSnapshotID"})
    persisted_immutable = {
        key: deepcopy(value)
        for key, value in persisted.items()
        if key not in mutable_fields
    }
    candidate_immutable = {
        key: deepcopy(value)
        for key, value in candidate.items()
        if key not in mutable_fields
    }
    if persisted_immutable != candidate_immutable:
        raise ReservationConflict(
            f"Persisted reservation replay {record_name} immutable content drifted."
        )
    lifecycle_changed = any(
        persisted.get(field) != candidate.get(field)
        for field in mutable_fields
    )
    if lifecycle_changed and persisted_version <= candidate_version:
        raise ReservationConflict(
            f"Persisted reservation replay {record_name} lifecycle changed without "
            "a newer version."
        )


def assert_reservation_write_set_replay_matches(
    *,
    write_set: PlanningReservationWriteSet,
    commitments: Mapping[str, dict[str, object]],
    batches: Mapping[str, dict[str, object]],
    capacity_reservations: Mapping[str, dict[str, object]],
    material_allocations: Mapping[str, dict[str, object]],
    events: MutableSequence[dict[str, object]],
    processed_event_keys: MutableSet[str],
) -> None:
    if write_set.idempotency_key not in processed_event_keys:
        raise ReservationLegacyMigrationRequired(
            "Reservation idempotency key is not recorded as processed."
        )
    current_fingerprint, expected_result = _assert_write_set_fingerprint_and_result(
        write_set
    )
    matching_events = [
        event
        for event in events
        if event.get("IdempotencyKey") == write_set.idempotency_key
    ]
    if not matching_events:
        raise ReservationLegacyMigrationRequired(
            "Processed reservation idempotency key has no persisted replay result."
        )
    if len(matching_events) != 1:
        raise ReservationConflict(
            "Processed reservation idempotency key has no unique persisted result."
        )
    persisted_event = matching_events[0]
    if (
        "PayloadFingerprint" not in persisted_event
        or "Result" not in persisted_event
    ):
        raise ReservationLegacyMigrationRequired(
            "Legacy planning reservation replay requires explicit migration before "
            "it can be evaluated."
        )
    if (
        persisted_event.get("PayloadFingerprint") != current_fingerprint
        or persisted_event.get("Result") != expected_result
    ):
        raise ReservationConflict(
            "Reservation idempotency key was already used with different content."
        )
    if persisted_event != write_set.events[0]:
        raise ReservationConflict(
            "Persisted reservation replay event immutable content drifted."
        )
    demand_id = str(expected_result["DemandCommitmentID"])
    batch_id = str(expected_result["ReservationBatchID"])
    persisted_demand = _replay_record(
        records=commitments,
        record_id=demand_id,
        id_field="DemandCommitmentID",
        record_name="demand commitment",
    )
    persisted_batch = _replay_record(
        records=batches,
        record_id=batch_id,
        id_field="ReservationBatchID",
        record_name="reservation batch",
    )
    try:
        normalized_persisted_demand = normalize_demand_commitment(
            persisted_demand
        )
    except ValueError as error:
        raise ReservationLegacyMigrationRequired(
            "Persisted reservation replay demand content is unverifiable."
        ) from error
    try:
        normalized_candidate_demand = normalize_demand_commitment(
            write_set.demand_commitment
        )
    except ValueError as error:
        raise ReservationConflict(
            "Candidate reservation replay demand content is invalid."
        ) from error
    _assert_replay_record_content(
        persisted=normalized_persisted_demand,
        candidate=normalized_candidate_demand,
        record_name="demand commitment",
        allowed_statuses=_DEMAND_REPLAY_STATUSES,
    )
    _assert_replay_record_content(
        persisted=persisted_batch,
        candidate=write_set.batch,
        record_name="reservation batch",
        allowed_statuses=_RESERVATION_REPLAY_STATUSES,
    )
    candidate_capacities = {
        str(record["CapacityReservationID"]): record
        for record in write_set.capacity_reservations
    }
    candidate_materials = {
        str(record["MaterialAllocationID"]): record
        for record in write_set.material_allocations
    }
    expected_capacity_ids = {
        str(record_id) for record_id in expected_result["CapacityReservationIDs"]
    }
    expected_material_ids = {
        str(record_id) for record_id in expected_result["MaterialAllocationIDs"]
    }
    linked_capacity_ids = {
        str(record_id)
        for record_id, record in capacity_reservations.items()
        if isinstance(record, Mapping)
        and (
            record.get("ReservationBatchID") == batch_id
            or record.get("DemandCommitmentID") == demand_id
        )
    }
    linked_material_ids = {
        str(record_id)
        for record_id, record in material_allocations.items()
        if isinstance(record, Mapping)
        and (
            record.get("ReservationBatchID") == batch_id
            or record.get("DemandCommitmentID") == demand_id
        )
    }
    if linked_capacity_ids - expected_capacity_ids:
        raise ReservationConflict(
            "Persisted capacity reservations do not match the canonical child set."
        )
    if linked_material_ids - expected_material_ids:
        raise ReservationConflict(
            "Persisted material allocations do not match the canonical child set."
        )
    for capacity_id in expected_result["CapacityReservationIDs"]:
        persisted_capacity = _replay_record(
            records=capacity_reservations,
            record_id=str(capacity_id),
            id_field="CapacityReservationID",
            record_name="capacity reservation",
        )
        _assert_replay_record_content(
            persisted=persisted_capacity,
            candidate=candidate_capacities[str(capacity_id)],
            record_name="capacity reservation",
            allowed_statuses=_RESERVATION_REPLAY_STATUSES,
        )
    for material_id in expected_result["MaterialAllocationIDs"]:
        persisted_material = _replay_record(
            records=material_allocations,
            record_id=str(material_id),
            id_field="MaterialAllocationID",
            record_name="material allocation",
        )
        _assert_replay_record_content(
            persisted=persisted_material,
            candidate=candidate_materials[str(material_id)],
            record_name="material allocation",
            allowed_statuses=_MATERIAL_REPLAY_STATUSES,
            allow_material_authority_handoff=True,
        )


def _assert_one_batch_per_demand(
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
        raise ReservationConflict(
            "Demand commitment already has a reservation batch; a non-terminal "
            "reservation batch or converted reservation batch permits only exact "
            "idempotent replay."
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
    try:
        normalized_demand = normalize_demand_commitment(
            write_set.demand_commitment
        )
    except ValueError as error:
        raise ReservationConflict(
            f"Reservation demand identity or content is invalid: {error}"
        ) from error
    if normalized_demand != write_set.demand_commitment:
        raise ReservationConflict(
            "Reservation demand record must use canonical normalized content."
        )
    demand_id = str(write_set.demand_commitment["DemandCommitmentID"])
    batch_id = str(write_set.batch["ReservationBatchID"])
    _assert_no_duplicate_ids(
        write_set.capacity_reservations, "CapacityReservationID"
    )
    _assert_no_duplicate_ids(write_set.material_allocations, "MaterialAllocationID")
    _assert_no_duplicate_ids(write_set.events, "EventID")
    if write_set.idempotency_key in processed_event_keys:
        assert_reservation_write_set_replay_matches(
            write_set=write_set,
            commitments=commitments,
            batches=batches,
            capacity_reservations=capacity_reservations,
            material_allocations=material_allocations,
            events=events,
            processed_event_keys=processed_event_keys,
        )
        return

    _assert_one_batch_per_demand(
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
