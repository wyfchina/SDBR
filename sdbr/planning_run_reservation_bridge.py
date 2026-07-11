from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Iterable, Mapping

from sdbr.planning_commitments import demand_commitment_content_fingerprint


GRAPH_FORMAT = "SDBRPlanningReservationGraphV2"
LEGACY_GRAPH_FORMAT = "LegacyUnversionedPlanningReservationGraph"
GRAPH_VERSION = 2
ELIGIBLE_DEMAND_STATUSES = {"Active", "LinkedToFormalOrder"}
ELIGIBLE_FREEZE_STATUSES = {"ActivePlanReservation", "LinkedToFormalOrder"}
ELIGIBLE_TRANSITION_STATUSES = ELIGIBLE_FREEZE_STATUSES | {
    "HeldForPlanningError"
}
MATERIAL_TRANSITION_STATUSES = ELIGIBLE_TRANSITION_STATUSES | {
    "Externalized",
    "AuthorityTransferred",
    "Released",
    "Cancelled",
}
AUTHORITY_OWNED_MATERIAL_STATUSES = {"Externalized", "AuthorityTransferred"}
SUPPORTED_RUN_STATUSES = {"Queued", "Completed", "Failed", "DeadLetter"}
TRANSITION_METADATA_FIELDS = {
    "Status",
    "RecordVersion",
    "PlanningRunID",
    "LastTransitionAt",
    "EventType",
}


class ReservationBatchReferenceError(ValueError):
    """Raised when a planning run refers to an invalid reservation batch graph."""


class ReservationGraphDriftError(ReservationBatchReferenceError):
    """Raised when the live graph no longer matches the frozen compare-and-set."""


class ReservationGraphMigrationRequiredError(ReservationBatchReferenceError):
    """Raised when a persisted pre-V2 graph cannot be converted safely."""

    status = "PlanningReservationGraphMigrationRequired"


class ScheduledOccupancyEvidenceError(ValueError):
    """Raised when completed schedule rows do not replace every frozen capacity row."""

    def __init__(
        self,
        capacity_reservation_ids: Iterable[str],
        *,
        reasons: Mapping[str, str] | None = None,
    ) -> None:
        self.capacity_reservation_ids = tuple(capacity_reservation_ids)
        self.reasons = dict(reasons or {})
        super().__init__(
            "Completed planning run lacks exact scheduled occupancy evidence for "
            + ", ".join(self.capacity_reservation_ids)
            + "."
        )


def _require_identity(value: object, field_name: str, record_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReservationBatchReferenceError(
            f"{record_name} identity field {field_name} is required."
        )
    return value


def _record_version(record: Mapping[str, object], record_name: str) -> int:
    if "RecordVersion" not in record:
        raise ReservationBatchReferenceError(
            f"{record_name} RecordVersion is required."
        )
    value = record.get("RecordVersion")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ReservationBatchReferenceError(
            f"{record_name} RecordVersion must be a positive integer."
        )
    return value


def _normalized_record(
    record: Mapping[str, object], record_name: str
) -> dict[str, object]:
    normalized = deepcopy(dict(record))
    normalized["RecordVersion"] = _record_version(record, record_name)
    return normalized


def _record_status(record: Mapping[str, object], record_name: str) -> str:
    status = record.get("Status")
    if not isinstance(status, str) or not status.strip():
        raise ReservationBatchReferenceError(
            f"{record_name} Status must be a string."
        )
    return status


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
            batch.get("ReservationBatchID"),
            "ReservationBatchID",
            "Reservation batch",
        )
        if canonical_batch_id != batch_id:
            raise ReservationBatchReferenceError(
                f"Reservation batch canonical ID does not match mapping key: {batch_id}."
            )
        _record_version(batch, f"Reservation batch {batch_id}")
        if (
            _record_status(batch, f"Reservation batch {batch_id}")
            not in eligible_statuses
        ):
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
                f"Reservation batch {batch_id} has duplicate canonical "
                f"{record_name} ID: {canonical_child_id}."
            )
        seen_ids.add(canonical_child_id)
        declared_ids.append(canonical_child_id)
    return declared_ids


def _resolve_demand_commitment_ids(
    *,
    demand_commitments: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    selected_batch_ids: list[str],
) -> list[str]:
    demand_ids: list[str] = []
    seen_ids: set[str] = set()
    for batch_id in selected_batch_ids:
        batch = batches[batch_id]
        demand_id = _require_identity(
            batch.get("DemandCommitmentID"),
            "DemandCommitmentID",
            f"Reservation batch {batch_id}",
        )
        if demand_id in seen_ids:
            raise ReservationBatchReferenceError(
                "Selected reservation batches cannot share a DemandCommitmentID."
            )
        demand = demand_commitments.get(demand_id)
        if not isinstance(demand, Mapping):
            raise ReservationBatchReferenceError(
                f"Demand commitment is missing for selected batch: {demand_id}."
            )
        canonical_id = _require_identity(
            demand.get("DemandCommitmentID"),
            "DemandCommitmentID",
            "Demand commitment",
        )
        if canonical_id != demand_id:
            raise ReservationBatchReferenceError(
                f"Demand commitment canonical ID does not match mapping key: {demand_id}."
            )
        _record_version(demand, f"Demand commitment {demand_id}")
        if _record_status(demand, f"Demand commitment {demand_id}") not in (
            ELIGIBLE_DEMAND_STATUSES
        ):
            raise ReservationBatchReferenceError(
                f"Demand commitment {demand_id} status is not eligible."
            )
        persisted_fingerprint = _require_identity(
            demand.get("ContentFingerprint"),
            "ContentFingerprint",
            f"Demand commitment {demand_id}",
        )
        try:
            calculated_fingerprint = demand_commitment_content_fingerprint(demand)
        except ValueError as error:
            raise ReservationBatchReferenceError(str(error)) from error
        if persisted_fingerprint != calculated_fingerprint:
            raise ReservationBatchReferenceError(
                f"Demand commitment {demand_id} ContentFingerprint does not match content."
            )
        demand_class = _require_identity(
            demand.get("DemandClass"), "DemandClass", "Demand commitment"
        )
        batch_class = _require_identity(
            batch.get("DemandClass"), "DemandClass", f"Reservation batch {batch_id}"
        )
        if demand_class != batch_class:
            raise ReservationBatchReferenceError(
                f"Demand commitment {demand_id} DemandClass does not match batch."
            )
        seen_ids.add(demand_id)
        demand_ids.append(demand_id)
    return demand_ids


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
                    f"Selected batches have duplicate canonical {record_name} ID: "
                    f"{child_id}."
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
                f"{record_name} canonical ID must match its mapping key and batch "
                f"ledger ID: {canonical_child_id}."
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
                f"{record_name} canonical ID must match its mapping key and batch "
                f"ledger ID: {child_id}."
            )
        if child_batch_id != batch_id:
            raise ReservationBatchReferenceError(
                f"{record_name} has wrong ReservationBatchID for declared child: "
                f"{child_id}."
            )
        resolved_ids.append(child_id)
    return resolved_ids


def _validate_child_consistency(
    *,
    selected_batch_ids: list[str],
    capacity_ids: list[str],
    material_ids: list[str],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
    require_freeze_eligibility: bool,
) -> None:
    batch_by_id = {batch_id: batches[batch_id] for batch_id in selected_batch_ids}
    correlations: set[tuple[str, str]] = set()
    for capacity_id in capacity_ids:
        capacity = capacity_reservations[capacity_id]
        batch_id = str(capacity["ReservationBatchID"])
        batch = batch_by_id[batch_id]
        for field in ("DemandCommitmentID", "DemandClass"):
            child_value = _require_identity(
                capacity.get(field), field, "Capacity reservation"
            )
            batch_value = _require_identity(
                batch.get(field), field, "Reservation batch"
            )
            if child_value != batch_value:
                raise ReservationBatchReferenceError(
                    f"Capacity reservation {capacity_id} {field} does not match batch."
                )
        for field in (
            "ReservationLineID",
            "OrderID",
            "OperationID",
            "ResourceID",
            "WindowStartAt",
            "WindowEndAt",
        ):
            _require_identity(capacity.get(field), field, "Capacity reservation")
        correlation = (str(capacity["OrderID"]), str(capacity["OperationID"]))
        if correlation in correlations:
            raise ReservationBatchReferenceError(
                "Selected capacity reservations have duplicate order/operation correlation."
            )
        correlations.add(correlation)
        _positive_finite_number(
            capacity.get("ReservedMinutes"), "Capacity reservation ReservedMinutes"
        )
        try:
            window_start = _parse_aware_datetime(
                capacity.get("WindowStartAt"), "WindowStartAt"
            )
            window_end = _parse_aware_datetime(
                capacity.get("WindowEndAt"), "WindowEndAt"
            )
        except ValueError as error:
            raise ReservationBatchReferenceError(str(error)) from error
        if window_end <= window_start:
            raise ReservationBatchReferenceError(
                "Capacity reservation window end must be strictly after start."
            )
        _record_version(capacity, f"Capacity reservation {capacity_id}")
        allowed = (
            ELIGIBLE_FREEZE_STATUSES
            if require_freeze_eligibility
            else ELIGIBLE_TRANSITION_STATUSES
        )
        if _record_status(
            capacity, f"Capacity reservation {capacity_id}"
        ) not in allowed:
            raise ReservationBatchReferenceError(
                f"Capacity reservation {capacity_id} status is not eligible."
            )

    for material_id in material_ids:
        material = material_allocations[material_id]
        batch_id = str(material["ReservationBatchID"])
        batch = batch_by_id[batch_id]
        for field in ("DemandCommitmentID", "DemandClass"):
            child_value = _require_identity(
                material.get(field), field, "Material allocation"
            )
            batch_value = _require_identity(
                batch.get(field), field, "Reservation batch"
            )
            if child_value != batch_value:
                raise ReservationBatchReferenceError(
                    f"Material allocation {material_id} {field} does not match batch."
                )
        _record_version(material, f"Material allocation {material_id}")
        allowed = (
            ELIGIBLE_FREEZE_STATUSES
            if require_freeze_eligibility
            else MATERIAL_TRANSITION_STATUSES
        )
        if _record_status(
            material, f"Material allocation {material_id}"
        ) not in allowed:
            raise ReservationBatchReferenceError(
                f"Material allocation {material_id} status is not eligible."
            )


def _resolve_batch_graph(
    *,
    batch_ids: Iterable[str],
    demand_commitments: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
    require_freeze_eligibility: bool,
) -> tuple[list[str], list[str], list[str], list[str]]:
    selected_ids = _selected_batch_ids(
        batch_ids,
        batches,
        require_freeze_eligibility=require_freeze_eligibility,
    )
    demand_ids = _resolve_demand_commitment_ids(
        demand_commitments=demand_commitments,
        batches=batches,
        selected_batch_ids=selected_ids,
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
    _validate_child_consistency(
        selected_batch_ids=selected_ids,
        capacity_ids=capacity_ids,
        material_ids=material_ids,
        batches=batches,
        capacity_reservations=capacity_reservations,
        material_allocations=material_allocations,
        require_freeze_eligibility=require_freeze_eligibility,
    )
    return selected_ids, demand_ids, capacity_ids, material_ids


def _canonical_hash(value: object) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ReservationBatchReferenceError(
            "Reservation graph must contain canonical JSON-compatible content."
        ) from error
    return sha256(encoded).hexdigest()


def _graph_metadata(core: Mapping[str, object]) -> dict[str, object]:
    batches = core["Batches"]
    identity = {
        "ReservationBatchIDs": core["ReservationBatchIDs"],
        "DemandCommitmentIDs": [
            batch["DemandCommitmentID"] for batch in batches  # type: ignore[index]
        ],
    }
    return {
        "GraphFormat": GRAPH_FORMAT,
        "GraphID": f"PRG-{_canonical_hash(identity)[:20]}",
        "GraphVersion": GRAPH_VERSION,
        "GraphFingerprint": f"sha256:{_canonical_hash(core)}",
    }


def _capture_graph(
    *,
    batch_ids: Iterable[str],
    demand_commitments: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
    require_freeze_eligibility: bool,
) -> dict[str, object]:
    selected_ids, demand_ids, capacity_ids, material_ids = _resolve_batch_graph(
        batch_ids=batch_ids,
        demand_commitments=demand_commitments,
        batches=batches,
        capacity_reservations=capacity_reservations,
        material_allocations=material_allocations,
        require_freeze_eligibility=require_freeze_eligibility,
    )
    core: dict[str, object] = {
        "ReservationBatchIDs": deepcopy(selected_ids),
        "DemandCommitments": [
            _normalized_record(
                demand_commitments[demand_id],
                f"Demand commitment {demand_id}",
            )
            for demand_id in demand_ids
        ],
        "Batches": [
            _normalized_record(batches[batch_id], f"Reservation batch {batch_id}")
            for batch_id in selected_ids
        ],
        "CapacityReservations": [
            _normalized_record(
                capacity_reservations[capacity_id],
                f"Capacity reservation {capacity_id}",
            )
            for capacity_id in capacity_ids
        ],
        "MaterialAllocations": [
            _normalized_record(
                material_allocations[material_id],
                f"Material allocation {material_id}",
            )
            for material_id in material_ids
        ],
    }
    return {**_graph_metadata(core), **core}


def freeze_planning_reservations(
    *,
    batch_ids: Iterable[str],
    demand_commitments: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Return an isolated, versioned snapshot of complete eligible batches."""
    return _capture_graph(
        batch_ids=batch_ids,
        demand_commitments=demand_commitments,
        batches=batches,
        capacity_reservations=capacity_reservations,
        material_allocations=material_allocations,
        require_freeze_eligibility=True,
    )


def _records_by_id(
    rows: object,
    *,
    id_field: str,
    record_name: str,
) -> tuple[list[str], dict[str, dict[str, object]]]:
    if not isinstance(rows, list):
        raise ReservationGraphDriftError(
            f"Frozen {record_name} collection must be a list."
        )
    ids: list[str] = []
    records: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ReservationGraphDriftError(
                f"Frozen {record_name} record must be an object."
            )
        record_id = _require_identity(row.get(id_field), id_field, record_name)
        if record_id in records:
            raise ReservationGraphDriftError(
                f"Frozen {record_name} has duplicate ID: {record_id}."
            )
        ids.append(record_id)
        records[record_id] = _normalized_record(row, record_name)
    return ids, records


def _normalize_frozen_graph(
    frozen_reservations: Mapping[str, object],
) -> dict[str, object]:
    graph_format = frozen_reservations.get("GraphFormat")
    if graph_format is None or graph_format == LEGACY_GRAPH_FORMAT:
        raise ReservationGraphMigrationRequiredError(
            "Legacy planning reservation graph requires explicit migration before "
            "execution."
        )
    if graph_format != GRAPH_FORMAT:
        raise ReservationGraphDriftError(
            f"Frozen reservation graph format is unsupported: {graph_format}."
        )
    for field in ("GraphID", "GraphVersion", "GraphFingerprint"):
        if field not in frozen_reservations:
            raise ReservationGraphDriftError(
                f"Frozen reservation graph {field} is required for current format."
            )
    requested_ids = frozen_reservations.get("ReservationBatchIDs")
    if not isinstance(requested_ids, list):
        raise ReservationGraphDriftError(
            "Frozen reservation graph ReservationBatchIDs must be a list."
        )
    _, demands = _records_by_id(
        frozen_reservations.get("DemandCommitments"),
        id_field="DemandCommitmentID",
        record_name="Demand commitment",
    )
    batch_ids, batches = _records_by_id(
        frozen_reservations.get("Batches"),
        id_field="ReservationBatchID",
        record_name="Reservation batch",
    )
    _, capacities = _records_by_id(
        frozen_reservations.get("CapacityReservations"),
        id_field="CapacityReservationID",
        record_name="Capacity reservation",
    )
    _, materials = _records_by_id(
        frozen_reservations.get("MaterialAllocations"),
        id_field="MaterialAllocationID",
        record_name="Material allocation",
    )
    if requested_ids != batch_ids:
        raise ReservationGraphDriftError(
            "Frozen reservation graph batch identity order is inconsistent."
        )
    try:
        captured = _capture_graph(
            batch_ids=requested_ids,
            demand_commitments=demands,
            batches=batches,
            capacity_reservations=capacities,
            material_allocations=materials,
            require_freeze_eligibility=True,
        )
    except ReservationBatchReferenceError as error:
        raise ReservationGraphDriftError(str(error)) from error
    for field in (
        "GraphFormat",
        "GraphID",
        "GraphVersion",
        "GraphFingerprint",
    ):
        persisted = frozen_reservations[field]
        if persisted != captured[field]:
            raise ReservationGraphDriftError(
                f"Frozen reservation graph {field} does not match its content."
            )
    return captured


def _immutable_record(record: Mapping[str, object]) -> dict[str, object]:
    return {
        key: deepcopy(value)
        for key, value in record.items()
        if key not in TRANSITION_METADATA_FIELDS
    }


def _assert_record_compare_and_set(
    *,
    live: Mapping[str, object],
    frozen: Mapping[str, object],
    run_id: str,
    record_name: str,
) -> None:
    if _immutable_record(live) != _immutable_record(frozen):
        raise ReservationGraphDriftError(
            f"{record_name} immutable content drifted after Planning Run freeze."
        )
    frozen_version = _record_version(frozen, record_name)
    live_version = _record_version(live, record_name)
    if (
        live_version == frozen_version
        and live.get("Status") == frozen.get("Status")
    ):
        return
    if (
        live_version > frozen_version
        and live.get("PlanningRunID") == run_id
        and live.get("EventType")
        in {"PlanningRunFailed", "PlanningRunDeadLetter"}
        and live.get("Status")
        in {
            "HeldForPlanningError",
            "ActivePlanReservation",
            "LinkedToFormalOrder",
        }
    ):
        return
    raise ReservationGraphDriftError(
        f"{record_name} status or RecordVersion drifted after Planning Run freeze."
    )


def _assert_material_compare_and_set(
    *,
    live: Mapping[str, object],
    frozen: Mapping[str, object],
    run_id: str,
    record_name: str,
) -> None:
    try:
        _assert_record_compare_and_set(
            live=live,
            frozen=frozen,
            run_id=run_id,
            record_name=record_name,
        )
        return
    except ReservationGraphDriftError as original_error:
        live_status = _record_status(live, record_name)
        if live_status not in AUTHORITY_OWNED_MATERIAL_STATUSES:
            raise original_error
        frozen_version = _record_version(frozen, record_name)
        live_version = _record_version(live, record_name)
        if live_version <= frozen_version:
            raise original_error
        try:
            external_ref = _require_identity(
                live.get("ExternalAllocationRef"),
                "ExternalAllocationRef",
                record_name,
            )
            authority_snapshot = _require_identity(
                live.get("MaterialSnapshotID"),
                "MaterialSnapshotID",
                record_name,
            )
        except ReservationBatchReferenceError:
            raise original_error
        if (
            external_ref == frozen.get("ExternalAllocationRef")
            or authority_snapshot == frozen.get("MaterialSnapshotID")
        ):
            raise original_error
        authority_metadata_fields = {
            *TRANSITION_METADATA_FIELDS,
            "ExternalAllocationRef",
            "MaterialSnapshotID",
        }
        live_business = {
            key: deepcopy(value)
            for key, value in live.items()
            if key not in authority_metadata_fields
        }
        frozen_business = {
            key: deepcopy(value)
            for key, value in frozen.items()
            if key not in authority_metadata_fields
        }
        if live_business != frozen_business:
            raise original_error


def _compare_live_graph_to_frozen(
    *,
    run_id: str,
    frozen: Mapping[str, object],
    demand_commitments: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
) -> tuple[list[str], list[str], list[str]]:
    frozen_batch_ids = list(frozen["ReservationBatchIDs"])  # type: ignore[arg-type]
    frozen_batches = {
        str(record["ReservationBatchID"]): record
        for record in frozen["Batches"]  # type: ignore[union-attr]
    }
    frozen_demands = {
        str(record["DemandCommitmentID"]): record
        for record in frozen["DemandCommitments"]  # type: ignore[union-attr]
    }
    frozen_capacities = {
        str(record["CapacityReservationID"]): record
        for record in frozen["CapacityReservations"]  # type: ignore[union-attr]
    }
    frozen_materials = {
        str(record["MaterialAllocationID"]): record
        for record in frozen["MaterialAllocations"]  # type: ignore[union-attr]
    }
    try:
        (
            live_batch_ids,
            live_demand_ids,
            live_capacity_ids,
            live_material_ids,
        ) = _resolve_batch_graph(
            batch_ids=frozen_batch_ids,
            demand_commitments=demand_commitments,
            batches=batches,
            capacity_reservations=capacity_reservations,
            material_allocations=material_allocations,
            require_freeze_eligibility=False,
        )
    except ReservationBatchReferenceError as error:
        raise ReservationGraphDriftError(str(error)) from error
    frozen_capacity_ids = list(frozen_capacities)
    frozen_material_ids = list(frozen_materials)
    frozen_demand_ids = list(frozen_demands)
    if (
        live_batch_ids != frozen_batch_ids
        or live_demand_ids != frozen_demand_ids
        or live_capacity_ids != frozen_capacity_ids
        or live_material_ids != frozen_material_ids
    ):
        raise ReservationGraphDriftError(
            "Live reservation graph child identity set drifted after freeze."
        )
    for demand_id in frozen_demand_ids:
        _assert_record_compare_and_set(
            live=demand_commitments[demand_id],
            frozen=frozen_demands[demand_id],
            run_id=run_id,
            record_name=f"Demand commitment {demand_id}",
        )
    for batch_id in frozen_batch_ids:
        _assert_record_compare_and_set(
            live=batches[batch_id],
            frozen=frozen_batches[batch_id],
            run_id=run_id,
            record_name=f"Reservation batch {batch_id}",
        )
    for capacity_id in frozen_capacity_ids:
        _assert_record_compare_and_set(
            live=capacity_reservations[capacity_id],
            frozen=frozen_capacities[capacity_id],
            run_id=run_id,
            record_name=f"Capacity reservation {capacity_id}",
        )
    for material_id in frozen_material_ids:
        _assert_material_compare_and_set(
            live=material_allocations[material_id],
            frozen=frozen_materials[material_id],
            run_id=run_id,
            record_name=f"Material allocation {material_id}",
        )
    return frozen_batch_ids, frozen_capacity_ids, frozen_material_ids


def _validate_transition_inputs(run_status: str, occurred_at: object) -> None:
    if run_status not in SUPPORTED_RUN_STATUSES:
        raise ValueError(f"Unsupported planning run status: {run_status}.")
    if (
        not isinstance(occurred_at, datetime)
        or occurred_at.tzinfo is None
        or occurred_at.utcoffset() is None
    ):
        raise ValueError("Planning run transition time must be timezone-aware.")


def _parse_aware_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO datetime string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO datetime string.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return parsed


def _positive_finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ReservationBatchReferenceError(
            f"{field_name} must be a finite positive number."
        )
    try:
        normalized = float(value)
    except OverflowError as error:
        raise ReservationBatchReferenceError(
            f"{field_name} must be a finite positive number."
        ) from error
    if not isfinite(normalized) or normalized <= 0:
        raise ReservationBatchReferenceError(
            f"{field_name} must be a finite positive number."
        )
    return normalized


def _malformed_schedule_error(message: str) -> ValueError:
    return ValueError(f"Malformed scheduled occupancy evidence: {message}")


def _strict_scheduled_work_order_rows(
    schedule: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    if not isinstance(schedule, Mapping):
        raise _malformed_schedule_error("schedule must be an object.")
    gantt_rows = schedule.get("GanttRows")
    if not isinstance(gantt_rows, list):
        raise _malformed_schedule_error("GanttRows must be a list.")
    rows: list[dict[str, object]] = []
    for row_index, gantt_row in enumerate(gantt_rows):
        if not isinstance(gantt_row, Mapping):
            raise _malformed_schedule_error(
                f"GanttRows[{row_index}] must be an object."
            )
        resource_id = gantt_row.get("ResourceID")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise _malformed_schedule_error(
                f"GanttRows[{row_index}].ResourceID must be a non-empty string."
            )
        bars = gantt_row.get("Bars")
        if not isinstance(bars, list):
            raise _malformed_schedule_error(
                f"GanttRows[{row_index}].Bars must be a list."
            )
        for bar_index, bar in enumerate(bars):
            path = f"GanttRows[{row_index}].Bars[{bar_index}]"
            if not isinstance(bar, Mapping):
                raise _malformed_schedule_error(f"{path} must be an object.")
            order_id = bar.get("OrderID")
            operation_id = bar.get("OperationID")
            if not isinstance(order_id, str) or not order_id.strip():
                raise _malformed_schedule_error(
                    f"{path}.OrderID must be a non-empty string."
                )
            if not isinstance(operation_id, str) or not operation_id.strip():
                raise _malformed_schedule_error(
                    f"{path}.OperationID must be a non-empty string."
                )
            try:
                scheduled_start = _parse_aware_datetime(
                    bar.get("Start"), f"{path}.Start"
                )
                scheduled_end = _parse_aware_datetime(
                    bar.get("End"), f"{path}.End"
                )
                duration_minutes = _positive_finite_number(
                    bar.get("DurationMinutes"), f"{path}.DurationMinutes"
                )
            except (ReservationBatchReferenceError, ValueError) as error:
                raise _malformed_schedule_error(str(error)) from error
            if scheduled_end <= scheduled_start:
                raise _malformed_schedule_error(
                    f"{path} end must be strictly after start."
                )
            timestamp_minutes = (
                scheduled_end - scheduled_start
            ).total_seconds() / 60.0
            if abs(timestamp_minutes - duration_minutes) > 1e-9:
                raise _malformed_schedule_error(
                    f"{path} timestamp duration does not equal DurationMinutes."
                )
            rows.append(
                {
                    "OrderID": order_id,
                    "OperationID": operation_id,
                    "ResourceID": resource_id,
                    "Start": bar.get("Start"),
                    "End": bar.get("End"),
                    "DurationMinutes": duration_minutes,
                }
            )
    return rows


def _exact_scheduled_occupancy_errors(
    *,
    capacity_records: Iterable[Mapping[str, object]],
    schedule: Mapping[str, object] | None,
) -> dict[str, str]:
    capacity_rows = list(capacity_records)
    capacity_ids = [str(record["CapacityReservationID"]) for record in capacity_rows]
    if not capacity_rows:
        return {}
    try:
        schedule_rows = _strict_scheduled_work_order_rows(schedule)
    except (ReservationBatchReferenceError, ValueError) as error:
        return {capacity_id: str(error) for capacity_id in capacity_ids}
    rows_by_correlation: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in schedule_rows:
        order_id = row.get("OrderID")
        operation_id = row.get("OperationID")
        if isinstance(order_id, str) and isinstance(operation_id, str):
            rows_by_correlation.setdefault((order_id, operation_id), []).append(row)

    errors: dict[str, str] = {}
    for capacity in capacity_rows:
        capacity_id = str(capacity["CapacityReservationID"])
        correlation = (str(capacity["OrderID"]), str(capacity["OperationID"]))
        matches = rows_by_correlation.get(correlation, [])
        if len(matches) != 1:
            errors[capacity_id] = "Expected exactly one correlated schedule operation."
            continue
        row = matches[0]
        try:
            reserved_minutes = _positive_finite_number(
                capacity.get("ReservedMinutes"), "ReservedMinutes"
            )
            scheduled_minutes = _positive_finite_number(
                row.get("DurationMinutes"), "DurationMinutes"
            )
            window_start = _parse_aware_datetime(
                capacity.get("WindowStartAt"), "WindowStartAt"
            )
            window_end = _parse_aware_datetime(
                capacity.get("WindowEndAt"), "WindowEndAt"
            )
            scheduled_start = _parse_aware_datetime(row.get("Start"), "Start")
            scheduled_end = _parse_aware_datetime(row.get("End"), "End")
        except (ReservationBatchReferenceError, ValueError) as error:
            errors[capacity_id] = str(error)
            continue
        if str(row.get("ResourceID")) != str(capacity.get("ResourceID")):
            errors[capacity_id] = "Correlated schedule operation uses a different resource."
        elif window_end <= window_start:
            errors[capacity_id] = "Reserved capacity window has an invalid time range."
        elif scheduled_minutes != reserved_minutes:
            errors[capacity_id] = "Correlated schedule duration does not equal reserved minutes."
        elif abs(
            (scheduled_end - scheduled_start).total_seconds() / 60.0
            - scheduled_minutes
        ) > 1e-9:
            errors[capacity_id] = (
                "Correlated schedule timestamp duration does not equal declared minutes."
            )
        elif scheduled_start < window_start or scheduled_end > window_end:
            errors[capacity_id] = "Correlated schedule operation is outside the reserved window."
        elif scheduled_end <= scheduled_start:
            errors[capacity_id] = "Correlated schedule operation has an invalid time range."
    return errors


def _trace_run_record(
    record: dict[str, object], *, run_id: str, run_status: str, occurred_at: datetime
) -> None:
    record.update(
        {
            "RecordVersion": _record_version(record, "Reservation record") + 1,
            "PlanningRunID": run_id,
            "LastTransitionAt": occurred_at.isoformat(),
            "EventType": f"PlanningRun{run_status}",
        }
    )


def _held_by_this_run(record: Mapping[str, object], run_id: str) -> bool:
    return (
        record.get("PlanningRunID") == run_id
        and record.get("EventType")
        in {"PlanningRunFailed", "PlanningRunDeadLetter"}
    )


def transition_planning_reservations_for_run(
    *,
    run_id: str,
    run_status: str,
    occurred_at: datetime,
    demand_commitments: Mapping[str, Mapping[str, object]],
    batches: Mapping[str, Mapping[str, object]],
    capacity_reservations: Mapping[str, Mapping[str, object]],
    material_allocations: Mapping[str, Mapping[str, object]],
    batch_ids: Iterable[str] | None = None,
    frozen_reservations: Mapping[str, object] | None = None,
    schedule: Mapping[str, object] | None = None,
) -> dict[str, dict[str, dict[str, object]]]:
    """Compare-and-set a frozen graph and apply its planning-run lifecycle."""
    _validate_transition_inputs(run_status, occurred_at)
    if frozen_reservations is None:
        if batch_ids is None:
            raise ValueError("Reservation batch IDs or a frozen graph are required.")
        frozen = _capture_graph(
            batch_ids=batch_ids,
            demand_commitments=demand_commitments,
            batches=batches,
            capacity_reservations=capacity_reservations,
            material_allocations=material_allocations,
            require_freeze_eligibility=False,
        )
        selected_ids = list(frozen["ReservationBatchIDs"])  # type: ignore[arg-type]
        capacity_ids = [
            str(record["CapacityReservationID"])
            for record in frozen["CapacityReservations"]  # type: ignore[union-attr]
        ]
        material_ids = [
            str(record["MaterialAllocationID"])
            for record in frozen["MaterialAllocations"]  # type: ignore[union-attr]
        ]
    else:
        frozen = _normalize_frozen_graph(frozen_reservations)
        selected_ids, capacity_ids, material_ids = _compare_live_graph_to_frozen(
            run_id=run_id,
            frozen=frozen,
            demand_commitments=demand_commitments,
            batches=batches,
            capacity_reservations=capacity_reservations,
            material_allocations=material_allocations,
        )

    result = {
        "Batches": deepcopy(dict(batches)),
        "CapacityReservations": deepcopy(dict(capacity_reservations)),
        "MaterialAllocations": deepcopy(dict(material_allocations)),
    }
    if run_status == "Queued":
        return result

    if run_status == "Completed":
        frozen_capacities = {
            str(record["CapacityReservationID"]): record
            for record in frozen["CapacityReservations"]  # type: ignore[union-attr]
        }
        evidence_errors = _exact_scheduled_occupancy_errors(
            capacity_records=[frozen_capacities[item] for item in capacity_ids],
            schedule=schedule,
        )
        if evidence_errors:
            raise ScheduledOccupancyEvidenceError(
                [item for item in capacity_ids if item in evidence_errors],
                reasons=evidence_errors,
            )

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
        if material.get("Status") in AUTHORITY_OWNED_MATERIAL_STATUSES:
            continue
        if run_status in {"Failed", "DeadLetter"} and material.get(
            "Status"
        ) == "ActivePlanReservation":
            material["Status"] = "HeldForPlanningError"
        elif (
            run_status == "Completed"
            and material.get("Status") == "HeldForPlanningError"
            and _held_by_this_run(material, run_id)
        ):
            material["Status"] = "ActivePlanReservation"
        _trace_run_record(
            material, run_id=run_id, run_status=run_status, occurred_at=occurred_at
        )

    return result
