from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from typing import Iterable, Mapping

from sdbr.ddsop_contracts import canonical_operating_model_fingerprint


@dataclass(frozen=True, slots=True)
class DdmrpGate:
    code: str
    message: str
    blocks_operational_action: bool = True


class DdmrpReplenishmentConflict(ValueError):
    status = "DdmrpReplenishmentConflict"


@dataclass(frozen=True, slots=True)
class DdmrpRelevantPlanningLedgerIdentity:
    schema_version: str
    scope_item_locations: tuple[tuple[str, str], ...]
    identity: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class DdmrpAuthoritySignature:
    runtime_package_id: str
    runtime_package_version: str
    runtime_package_fingerprint: str
    runtime_snapshot_id: str
    runtime_snapshot_at: str
    operating_model_configuration_id: str
    operating_model_fingerprint: str
    ddmrp_configuration_id: str
    target_time_semantics_id: str | None
    target_policy_id: str | None
    target_policy_version: str | None
    target_policy_fingerprint: str | None
    target_calendar_id: str | None
    target_calendar_version: str | None
    target_calendar_fingerprint: str | None
    planning_advice_package_id: str | None
    planning_advice_package_fingerprint: str | None
    plan_bom_package_id: str | None
    plan_bom_package_fingerprint: str | None
    material_authority_snapshot_id: str | None
    material_authority_snapshot_fingerprint: str | None
    capacity_calendar_snapshot_id: str | None
    capacity_calendar_snapshot_fingerprint: str | None
    local_planning_ledger_schema_version: str
    local_planning_ledger_identity: str
    local_planning_ledger_fingerprint: str
    scenario_label: str
    mapping_confidence: str
    parameter_authority_fingerprint: str
    signature_fingerprint: str


def canonical_fingerprint(value: object) -> str:
    try:
        encoded = json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise DdmrpReplenishmentConflict(
            "DDMRP authority input contains a non-canonical JSON value."
        ) from error
    return f"sha256:{sha256(encoded).hexdigest()}"


RELEVANT_DEMAND_FIELDS = (
    "DemandCommitmentID", "DemandSourceType", "SourceSystem", "SourceObjectType",
    "SourceObjectID", "SourceObjectVersion", "DemandLineID", "ItemOrProductID",
    "LocationID", "Quantity", "Uom", "RequiredAt", "DemandClass", "Status",
    "RecordVersion", "ContentFingerprint",
)
RELEVANT_BATCH_FIELDS = (
    "ReservationBatchID", "DemandCommitmentID", "DemandClass", "Status",
    "CapacityReservationIDs", "MaterialAllocationIDs", "PlanningRunID",
    "RecordVersion", "LastTransitionAt", "EventType",
)
RELEVANT_CAPACITY_FIELDS = (
    "CapacityReservationID", "ReservationBatchID", "DemandCommitmentID",
    "DemandClass", "ResourceID", "WindowStartAt", "WindowEndAt",
    "ReservedMinutes", "LatestAllowedCompletionAt", "Status", "PlanningRunID",
    "RecordVersion", "LastTransitionAt", "EventType",
)
RELEVANT_MATERIAL_FIELDS = (
    "MaterialAllocationID", "ReservationBatchID", "DemandCommitmentID",
    "RequirementLineID", "ItemID", "LocationID", "Uom", "AllocatedQty",
    "SupplySourceType", "SupplyID", "MaterialSnapshotID", "ExternalAllocationRef",
    "Status", "RecordVersion", "LastTransitionAt", "EventType",
)
RELEVANT_GRAPH_FIELDS = (
    "LogicalReplenishmentID", "RecommendationID", "ItemID", "LocationID", "Uom",
    "GraphStatus", "DemandCommitmentID", "ReservationBatchID",
    "PlannedManufacturingCandidateID", "FormalSupplyID", "RecordVersion",
)
RELEVANT_DEMAND_STATUSES = frozenset(
    {"Active", "LinkedToFormalOrder", "HeldForPlanningError", "AdjustmentRequired"}
)
RELEVANT_PLANNING_STATUSES = frozenset(
    {"ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError", "AdjustmentRequired"}
)
RELEVANT_GRAPH_STATUSES = frozenset(
    {"ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError", "AdjustmentRequired", "InExecution"}
)


def build_relevant_planning_ledger_identity(
    *,
    scope_item_locations: Iterable[tuple[str, str]],
    planning_demand_commitments: Mapping[str, Mapping[str, object]],
    planning_reservation_batches: Mapping[str, Mapping[str, object]],
    ccr_capacity_reservations: Mapping[str, Mapping[str, object]],
    material_planning_allocations: Mapping[str, Mapping[str, object]],
    active_replenishment_graphs: Mapping[str, Mapping[str, object]],
) -> DdmrpRelevantPlanningLedgerIdentity:
    scope = _normalize_scope(scope_item_locations)
    scope_set = set(scope)

    demand_rows = _select_scoped_rows(
        planning_demand_commitments,
        canonical_id="DemandCommitmentID",
        fields=RELEVANT_DEMAND_FIELDS,
        status_field="Status",
        statuses=RELEVANT_DEMAND_STATUSES,
        scope_fields=("ItemOrProductID", "LocationID"),
        scope=scope_set,
    )
    demand_ids = {str(row["DemandCommitmentID"]) for row in demand_rows}

    batch_rows = _select_joined_rows(
        planning_reservation_batches,
        canonical_id="ReservationBatchID",
        fields=RELEVANT_BATCH_FIELDS,
        status_field="Status",
        statuses=RELEVANT_PLANNING_STATUSES,
        joined_field="DemandCommitmentID",
        joined_ids=demand_ids,
    )
    batch_by_id = {str(row["ReservationBatchID"]): row for row in batch_rows}

    capacity_rows = _select_reservation_children(
        ccr_capacity_reservations,
        canonical_id="CapacityReservationID",
        fields=RELEVANT_CAPACITY_FIELDS,
        demand_ids=demand_ids,
        batch_by_id=batch_by_id,
    )
    material_rows = _select_reservation_children(
        material_planning_allocations,
        canonical_id="MaterialAllocationID",
        fields=RELEVANT_MATERIAL_FIELDS,
        demand_ids=demand_ids,
        batch_by_id=batch_by_id,
    )
    graph_rows = _select_scoped_rows(
        active_replenishment_graphs,
        canonical_id="LogicalReplenishmentID",
        fields=RELEVANT_GRAPH_FIELDS,
        status_field="GraphStatus",
        statuses=RELEVANT_GRAPH_STATUSES,
        scope_fields=("ItemID", "LocationID"),
        scope=scope_set,
    )
    for graph in graph_rows:
        demand_id = graph["DemandCommitmentID"]
        batch_id = graph["ReservationBatchID"]
        if demand_id is not None and str(demand_id) not in demand_ids:
            raise DdmrpReplenishmentConflict("Relevant graph demand target is missing.")
        if batch_id is not None and str(batch_id) not in batch_by_id:
            raise DdmrpReplenishmentConflict("Relevant graph reservation target is missing.")

    payload = {
        "SchemaVersion": "DdmrpRelevantPlanningLedgerV1",
        "ScopeItemLocations": [
            {"ItemID": item_id, "LocationID": location_id}
            for item_id, location_id in scope
        ],
        "DemandCommitments": demand_rows,
        "ReservationBatches": batch_rows,
        "CapacityReservations": capacity_rows,
        "MaterialAllocations": material_rows,
        "ActiveReplenishmentGraphs": graph_rows,
    }
    fingerprint = canonical_fingerprint(payload)
    return DdmrpRelevantPlanningLedgerIdentity(
        schema_version="DdmrpRelevantPlanningLedgerV1",
        scope_item_locations=scope,
        identity=f"DPL-{fingerprint.removeprefix('sha256:')[:20]}",
        fingerprint=fingerprint,
    )


def build_read_only_authority_signature(
    *,
    package_record: Mapping[str, object],
    operating_model_configuration: Mapping[str, object],
    relevant_planning_ledger: DdmrpRelevantPlanningLedgerIdentity,
    evaluated_at: datetime,
) -> tuple[DdmrpAuthoritySignature, tuple[DdmrpGate, ...]]:
    if (
        evaluated_at.tzinfo is None
        or evaluated_at.utcoffset() != timedelta(0)
        or not evaluated_at.isoformat().endswith("+00:00")
    ):
        raise DdmrpReplenishmentConflict(
            "evaluated_at must be a timezone-aware canonical UTC datetime."
        )

    payload = _mapping(package_record, "Payload")
    identity = _mapping(payload, "PackageIdentity")
    frozen = _mapping(payload, "FrozenDdsopConfiguration")
    runtime = _mapping(payload, "RuntimeEvidenceSnapshot")
    parameter_evidence = _mapping(payload, "ParameterAuthorityEvidence")
    configuration = _configuration_payload(operating_model_configuration)

    runtime_package_id = _same_required_text(
        package_record.get("RuntimePlanningInputPackageID"),
        identity.get("RuntimePlanningInputPackageID"),
        label="runtime package ID",
    )
    runtime_package_version = _same_required_text(
        package_record.get("PackageVersion"),
        identity.get("PackageVersion"),
        label="runtime package version",
    )
    configuration_id = _same_required_text(
        package_record.get("OperatingModelConfigurationID"),
        frozen.get("OperatingModelConfigurationID"),
        configuration.get("OperatingModelConfigurationID"),
        label="operating model configuration ID",
    )
    ddmrp_configuration = _mapping(configuration, "DDMRPConfiguration")
    ddmrp_configuration_id = _same_required_text(
        package_record.get("DDMRPConfigurationID"),
        frozen.get("DDMRPConfigurationID"),
        ddmrp_configuration.get("DDMRPConfigurationID"),
        label="DDMRP configuration ID",
    )
    operating_model_fingerprint = canonical_operating_model_fingerprint(configuration)
    _same_required_text(
        package_record.get("OperatingModelFingerprint"),
        frozen.get("OperatingModelFingerprint"),
        configuration.get("Fingerprint"),
        operating_model_fingerprint,
        label="operating model fingerprint",
    )

    canonical_payload = deepcopy(dict(payload))
    canonical_runtime = _mapping(canonical_payload, "RuntimeEvidenceSnapshot")
    canonical_runtime["SnapshotAt"] = evaluated_at.isoformat()
    canonical_payload["RuntimeEvidenceSnapshot"] = canonical_runtime
    runtime_package_fingerprint = canonical_fingerprint(canonical_payload)
    parameter_authority_fingerprint = canonical_fingerprint(parameter_evidence)
    scenario_label = _required_text(identity.get("ScenarioLabel"), "scenario label")
    mapping_confidence = _required_text(
        identity.get("MappingConfidence"), "mapping confidence"
    )

    base = {
        "runtime_package_id": runtime_package_id,
        "runtime_package_version": runtime_package_version,
        "runtime_package_fingerprint": runtime_package_fingerprint,
        "runtime_snapshot_id": _required_text(
            runtime.get("OperationalStateSnapshotID"), "runtime snapshot ID"
        ),
        "runtime_snapshot_at": evaluated_at.isoformat(),
        "operating_model_configuration_id": configuration_id,
        "operating_model_fingerprint": operating_model_fingerprint,
        "ddmrp_configuration_id": ddmrp_configuration_id,
        "target_time_semantics_id": None,
        "target_policy_id": None,
        "target_policy_version": None,
        "target_policy_fingerprint": None,
        "target_calendar_id": None,
        "target_calendar_version": None,
        "target_calendar_fingerprint": None,
        "planning_advice_package_id": None,
        "planning_advice_package_fingerprint": None,
        "plan_bom_package_id": None,
        "plan_bom_package_fingerprint": None,
        "material_authority_snapshot_id": None,
        "material_authority_snapshot_fingerprint": None,
        "capacity_calendar_snapshot_id": None,
        "capacity_calendar_snapshot_fingerprint": None,
        "local_planning_ledger_schema_version": relevant_planning_ledger.schema_version,
        "local_planning_ledger_identity": relevant_planning_ledger.identity,
        "local_planning_ledger_fingerprint": relevant_planning_ledger.fingerprint,
        "scenario_label": scenario_label,
        "mapping_confidence": mapping_confidence,
        "parameter_authority_fingerprint": parameter_authority_fingerprint,
    }
    signature = DdmrpAuthoritySignature(
        **base,
        signature_fingerprint=canonical_fingerprint(base),
    )
    gates = [
        DdmrpGate(
            code="DLT_TARGET_SEMANTICS_INSUFFICIENT",
            message="Accepted target policy and calendar semantics are not available.",
        ),
        DdmrpGate(
            code="PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
            message="No accepted ERP/MRP replenishment advice contract is available.",
        ),
        DdmrpGate(
            code="PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
            message="No accepted Plan BOM feasibility contract is available.",
        ),
    ]
    if not _has_accepted_operational_authority(identity, parameter_evidence):
        gates.append(
            DdmrpGate(
                code="OPERATIONAL_AUTHORITY_NOT_ACCEPTED",
                message="Runtime evidence is not accepted for operational action.",
            )
        )
    return signature, tuple(sorted(gates, key=lambda gate: gate.code))


def _normalize_scope(
    scope_item_locations: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    normalized: set[tuple[str, str]] = set()
    for entry in scope_item_locations:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise DdmrpReplenishmentConflict("DDMRP scope entries must be item/location pairs.")
        item_id, location_id = entry
        if not isinstance(item_id, str) or not item_id or not isinstance(location_id, str) or not location_id:
            raise DdmrpReplenishmentConflict("DDMRP scope item and location IDs are required.")
        normalized.add((item_id, location_id))
    if not normalized:
        raise DdmrpReplenishmentConflict("DDMRP relevant planning scope cannot be empty.")
    return tuple(sorted(normalized))


def _select_scoped_rows(
    rows: Mapping[str, Mapping[str, object]],
    *,
    canonical_id: str,
    fields: tuple[str, ...],
    status_field: str,
    statuses: frozenset[str],
    scope_fields: tuple[str, str],
    scope: set[tuple[str, str]],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for key, row in rows.items():
        _validate_mapping_identity(key, row, canonical_id, seen)
        status = _required_text(row.get(status_field), status_field)
        if status not in statuses:
            continue
        row_scope = (
            _required_text(row.get(scope_fields[0]), scope_fields[0]),
            _required_text(row.get(scope_fields[1]), scope_fields[1]),
        )
        if row_scope not in scope:
            continue
        selected.append(_project(row, fields))
    return sorted(selected, key=lambda row: str(row[canonical_id]))


def _select_joined_rows(
    rows: Mapping[str, Mapping[str, object]],
    *,
    canonical_id: str,
    fields: tuple[str, ...],
    status_field: str,
    statuses: frozenset[str],
    joined_field: str,
    joined_ids: set[str],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for key, row in rows.items():
        _validate_mapping_identity(key, row, canonical_id, seen)
        status = _required_text(row.get(status_field), status_field)
        if status not in statuses:
            continue
        joined_id = _required_text(row.get(joined_field), joined_field)
        if joined_id not in joined_ids:
            continue
        selected.append(_project(row, fields))
    return sorted(selected, key=lambda row: str(row[canonical_id]))


def _select_reservation_children(
    rows: Mapping[str, Mapping[str, object]],
    *,
    canonical_id: str,
    fields: tuple[str, ...],
    demand_ids: set[str],
    batch_by_id: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for key, row in rows.items():
        _validate_mapping_identity(key, row, canonical_id, seen)
        status = _required_text(row.get("Status"), "Status")
        if status not in RELEVANT_PLANNING_STATUSES:
            continue
        demand_id = _required_text(row.get("DemandCommitmentID"), "DemandCommitmentID")
        batch_id = _required_text(row.get("ReservationBatchID"), "ReservationBatchID")
        if demand_id not in demand_ids and batch_id not in batch_by_id:
            continue
        batch = batch_by_id.get(batch_id)
        if batch is None or demand_id not in demand_ids or batch["DemandCommitmentID"] != demand_id:
            raise DdmrpReplenishmentConflict("Relevant reservation child has a missing join target.")
        selected.append(_project(row, fields))
    return sorted(selected, key=lambda row: str(row[canonical_id]))


def _validate_mapping_identity(
    key: object,
    row: Mapping[str, object],
    canonical_id: str,
    seen: set[str],
) -> None:
    if not isinstance(row, Mapping):
        raise DdmrpReplenishmentConflict("Relevant planning ledger rows must be mappings.")
    semantic_id = _required_text(row.get(canonical_id), canonical_id)
    if key != semantic_id:
        raise DdmrpReplenishmentConflict(
            f"Relevant planning ledger key does not match {canonical_id}."
        )
    if semantic_id in seen:
        raise DdmrpReplenishmentConflict(f"Duplicate semantic ID for {canonical_id}.")
    seen.add(semantic_id)


def _project(
    row: Mapping[str, object], fields: tuple[str, ...]
) -> dict[str, object]:
    missing = [field for field in fields if field not in row]
    if missing:
        raise DdmrpReplenishmentConflict(
            f"Relevant planning row is missing required fields: {', '.join(missing)}."
        )
    projected = {field: deepcopy(row[field]) for field in fields}
    canonical_fingerprint(projected)
    return projected


def _mapping(parent: Mapping[str, object], field: str) -> dict[str, object]:
    value = parent.get(field)
    if not isinstance(value, Mapping):
        raise DdmrpReplenishmentConflict(f"{field} must be a mapping.")
    return dict(value)


def _configuration_payload(
    operating_model_configuration: Mapping[str, object],
) -> dict[str, object]:
    payload = operating_model_configuration.get("Payload")
    if isinstance(payload, Mapping):
        return dict(payload)
    return dict(operating_model_configuration)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DdmrpReplenishmentConflict(f"{label} is required.")
    return value


def _same_required_text(*values: object, label: str) -> str:
    normalized = tuple(_required_text(value, label) for value in values)
    if len(set(normalized)) != 1:
        raise DdmrpReplenishmentConflict(f"{label} references do not match.")
    return normalized[0]


def _has_accepted_operational_authority(
    identity: Mapping[str, object], parameter_evidence: Mapping[str, object]
) -> bool:
    refs = parameter_evidence.get("ParameterEvidenceRefs")
    return (
        identity.get("PackageStatus") == "AcceptedForBoundedPlanning"
        and identity.get("MappingConfidence") == "ProductionAccepted"
        and isinstance(refs, list)
        and bool(refs)
        and all(
            isinstance(row, Mapping)
            and row.get("ProductionAuthorityStatus") == "Accepted"
            for row in refs
        )
    )
