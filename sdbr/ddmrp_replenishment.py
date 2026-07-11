from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from typing import Iterable, Literal, Mapping, MutableMapping, MutableSequence

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
            value,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise DdmrpReplenishmentConflict(
            "DDMRP authority input contains a non-canonical JSON value."
        ) from error
    return f"sha256:{sha256(encoded).hexdigest()}"


def canonical_stable_id(prefix: str, identity: Mapping[str, object]) -> str:
    digest = canonical_fingerprint(dict(identity)).removeprefix("sha256:")
    return f"{prefix}-{digest[:20]}"


EVALUATION_SUMMARY_FIELDS = (
    "RedCount", "YellowCount", "GreenCount", "AboveGreenCount",
    "BlockedRecommendationCount", "AdjustmentRequiredCount", "IssueCount",
)
DEMAND_COMPONENT_FIELDS = (
    "DemandID", "DemandType", "DemandQty", "DemandDueAt", "IsQualifiedSpike", "Uom",
)
SUPPLY_COMPONENT_FIELDS = (
    "SupplyID", "SupplyQty", "ExpectedAt", "Status", "Uom",
)
GATE_FIELDS = ("Code", "Message", "BlocksOperationalAction")
ISSUE_RECORD_FIELDS = (
    "IssueID", "EvaluationID", "Code", "Severity", "Message", "ItemID",
    "LocationID", "BlocksOperationalAction", "IssueFingerprint",
)
ISSUE_SEVERITIES = frozenset({"Blocking", "Warning", "Information"})
EVALUATION_RUN_FIELDS = (
    "EvaluationID", "EvaluationRequestID", "EvaluationAt", "RecordedAt", "RecordedBy",
    "EvaluationMode", "RuntimePlanningInputPackageID",
    "RuntimePlanningInputPackageVersion", "RuntimeSnapshotID",
    "OperatingModelConfigurationID", "OperatingModelFingerprint",
    "DDMRPConfigurationID", "AuthoritySignature", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "Summary", "Issues", "OperationalActionAllowed", "EvaluationFingerprint",
)
EVALUATION_ROW_FIELDS = (
    "EvaluationRowID", "EvaluationID", "EvaluationAt", "RowKey", "ItemID", "LocationID", "Uom",
    "BufferProfileID", "DLTMinutes", "QualifiedOnHandQty", "PhysicalOnHandQty",
    "AuthorityAllocatedQty", "AuthorityAvailableQty", "QualityState",
    "QualifiedOpenSupplyQty", "QualifiedDemandQty", "NetFlowPosition", "TopOfRed",
    "TopOfYellow", "TopOfGreen", "PlanningStatus", "ExecutionStatus",
    "SuggestedReplenishmentQty", "RecommendedAction", "StandardTargetReceiptAt",
    "TargetStatusCode", "RecommendationID", "DemandComponents", "SupplyComponents",
    "GateCodes", "OperationalActionAllowed", "AuthoritySignatureFingerprint",
    "EvaluationRowFingerprint",
)
REPLENISHMENT_CHAIN_FIELDS = (
    "LogicalReplenishmentID", "ItemID", "LocationID", "CycleNumber",
    "OpenedAt", "OpenedByEvaluationID", "InitialStatus", "IdentityFingerprint",
    "TraceID", "ChainFingerprint",
)
RECOMMENDATION_FIELDS = (
    "RecommendationID", "LogicalReplenishmentID", "RecommendationVersion",
    "EvaluationID", "EvaluationRowID", "ItemID", "LocationID", "Uom",
    "PlanningStatus", "ExecutionStatus", "SuggestedReplenishmentQty",
    "StandardTargetReceiptAt", "AdviceType", "InitialStatus", "GateCodes",
    "PredecessorRecommendationID", "AdjustmentOfRecommendationID", "CreatedAt",
    "CreatedBy", "AuthoritySignature", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "TraceID", "RecommendationFingerprint",
)
EVENT_FIELDS = (
    "EventID", "EventType", "AggregateType", "AggregateID", "AggregateVersion",
    "EvaluationID", "LogicalReplenishmentID", "RecommendationID",
    "RelatedRecommendationID", "StatusBefore", "StatusAfter", "OccurredAt",
    "ActorID", "CausationID", "CorrelationID", "IdempotencyKey", "TraceID",
    "EventPayload", "PayloadFingerprint",
)
REQUEST_RESULT_FIELDS = (
    "EvaluationRequestID", "RequestFingerprint", "RuntimePlanningInputPackageID",
    "EvaluationID", "EvaluationRowIDs", "LogicalReplenishmentIDs",
    "CreatedLogicalReplenishmentIDs", "ReusedLogicalReplenishmentIDs",
    "RecommendationIDs", "EventIDs", "EvaluationPayloadFingerprint",
    "ResponseData", "ResponseFingerprint", "RecordedAt", "RecordedBy",
    "RequestResultFingerprint",
)
RESPONSE_DATA_FIELDS = (
    "Status", "EvaluationID", "RecommendationIDs", "OperationalActionAllowed",
)

EVENT_PAYLOAD_FIELDS_BY_TYPE = {
    "ReplenishmentChainOpened": (
        "CycleNumber", "ItemID", "LocationID", "OpenedByEvaluationID",
    ),
    "ReplenishmentChainActivated": ("DecisionID", "AdviceType", "ActiveGraphID"),
    "ReplenishmentChainAdjustmentRequired": (
        "AdjustmentRecommendationID", "AdjustmentDeltaQty", "ReasonCode",
    ),
    "ReplenishmentChainReleased": ("DecisionID", "Reason"),
    "ReplenishmentChainCancelled": ("DecisionID", "Reason"),
    "ReplenishmentChainCompleted": ("FormalSupplyID",),
    "RecommendationVersionCreated": (
        "RecommendationVersion", "SuggestedReplenishmentQty", "GateCodes",
        "PredecessorRecommendationID", "AdjustmentOfRecommendationID",
    ),
    "RecommendationSuperseded": (
        "SupersededByRecommendationID", "SupersedingEvaluationID",
    ),
    "RecommendationPendingReview": (
        "AdviceType", "AuthoritySignatureFingerprint",
    ),
    "RecommendationConfirmed": ("DecisionID", "AdviceType", "Reason"),
    "RecommendationRejected": ("DecisionID", "Reason"),
    "RecommendationIssued": ("OutputRequestID",),
    "RecommendationOutputFailed": ("OutputRequestID", "FailureCode"),
    "RecommendationERPAccepted": ("ExternalOrderRef", "FormalSupplyID"),
    "RecommendationInExecution": ("FormalSupplyID",),
    "RecommendationAdjustmentRequired": (
        "AdjustmentRecommendationID", "AdjustmentDeltaQty", "ReasonCode",
    ),
    "RecommendationReleased": ("DecisionID", "Reason"),
    "RecommendationCancelled": ("DecisionID", "Reason"),
    "RecommendationCompleted": ("FormalSupplyID", "CompletedQty"),
}
EVENT_AGGREGATE_TYPE_BY_EVENT = {
    **{
        event_type: "ReplenishmentChain"
        for event_type in EVENT_PAYLOAD_FIELDS_BY_TYPE
        if event_type.startswith("ReplenishmentChain")
    },
    **{
        event_type: "Recommendation"
        for event_type in EVENT_PAYLOAD_FIELDS_BY_TYPE
        if event_type.startswith("Recommendation")
    },
}
EVENT_TRANSITION_BY_TYPE = {
    "ReplenishmentChainActivated": (frozenset({"Open"}), "ActiveGraph"),
    "ReplenishmentChainAdjustmentRequired": (
        frozenset({"Open", "ActiveGraph"}), "AdjustmentRequired",
    ),
    "ReplenishmentChainReleased": (
        frozenset({"Open", "ActiveGraph", "AdjustmentRequired"}), "Released",
    ),
    "ReplenishmentChainCancelled": (
        frozenset({"Open", "ActiveGraph", "AdjustmentRequired"}), "Cancelled",
    ),
    "ReplenishmentChainCompleted": (
        frozenset({"Open", "ActiveGraph", "AdjustmentRequired"}), "Completed",
    ),
    "RecommendationSuperseded": (
        frozenset({"Blocked", "PendingReview", "AdjustmentRequired"}), "Superseded",
    ),
    "RecommendationPendingReview": (frozenset({"Blocked"}), "PendingReview"),
    "RecommendationConfirmed": (frozenset({"PendingReview"}), "Confirmed"),
    "RecommendationRejected": (frozenset({"PendingReview"}), "Rejected"),
    "RecommendationIssued": (frozenset({"Confirmed", "OutputFailed"}), "Issued"),
    "RecommendationOutputFailed": (frozenset({"Issued"}), "OutputFailed"),
    "RecommendationERPAccepted": (frozenset({"Issued"}), "ERPAccepted"),
    "RecommendationInExecution": (frozenset({"ERPAccepted"}), "InExecution"),
    "RecommendationAdjustmentRequired": (
        frozenset({"Confirmed", "Issued", "OutputFailed", "ERPAccepted", "InExecution"}),
        "AdjustmentRequired",
    ),
    "RecommendationReleased": (
        frozenset({"Confirmed", "AdjustmentRequired"}), "Released",
    ),
    "RecommendationCancelled": (
        frozenset({"Confirmed", "Issued", "OutputFailed", "ERPAccepted", "InExecution", "AdjustmentRequired"}),
        "Cancelled",
    ),
    "RecommendationCompleted": (frozenset({"InExecution"}), "Completed"),
}

RECOMMENDATION_ACTIVE_STATUSES = frozenset({
    "Blocked", "PendingReview", "Confirmed", "AdjustmentRequired", "Issued",
    "OutputFailed", "ERPAccepted", "InExecution",
})
RECOMMENDATION_TERMINAL_STATUSES = frozenset({
    "Rejected", "Superseded", "Released", "Cancelled", "Completed",
})
CHAIN_ACTIVE_STATUSES = frozenset({"Open", "ActiveGraph", "AdjustmentRequired"})
CHAIN_TERMINAL_STATUSES = frozenset({"Released", "Cancelled", "Completed"})

_RUNTIME_RESULT_FIELDS = (
    "EvaluationMode", "Boundary", "EvaluatedAt", "Summary", "Lines", "Issues",
)
_RUNTIME_LINE_FIELDS = (
    "ItemID", "LocationID", "BufferProfileID", "DLTMinutes", "OnHandQty",
    "QualifiedOnHandQty", "QualifiedOpenSupplyQty", "QualifiedDemandQty",
    "NetFlowPosition", "TopOfRed", "TopOfYellow", "TopOfGreen", "PlanningStatus",
    "ExecutionStatus", "SuggestedReplenishmentQty", "RecommendedAction",
    "DemandComponents", "SupplyComponents", "PhysicalOnHandQty",
    "AuthorityAllocatedQty", "AuthorityAvailableQty", "QualityState", "Uom",
)


@dataclass(frozen=True, slots=True)
class DdmrpEvaluationWriteSet:
    evaluation_request_id: str
    request_fingerprint: str
    payload_fingerprint: str
    evaluation_run: dict[str, object]
    evaluation_rows: tuple[dict[str, object], ...]
    chain_records: tuple[dict[str, object], ...]
    recommendation_versions: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]
    request_result: dict[str, object]


@dataclass(frozen=True, slots=True)
class DdmrpEvaluationStagedState:
    evaluation_runs: dict[str, dict[str, object]]
    evaluation_rows: dict[str, dict[str, object]]
    chains: dict[str, dict[str, object]]
    recommendations: dict[str, dict[str, object]]
    events: tuple[dict[str, object], ...]
    request_results: dict[str, dict[str, object]]
    result_status: Literal["Created", "Duplicate"]
    response_data: dict[str, object]


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


def _require_exact_fields(
    value: Mapping[str, object],
    fields: tuple[str, ...],
    *,
    context: str,
) -> None:
    actual = frozenset(value)
    expected = frozenset(fields)
    if actual != expected:
        raise DdmrpReplenishmentConflict(
            f"{context} fields differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _validate_event_contract(event: Mapping[str, object]) -> None:
    _require_exact_fields(event, EVENT_FIELDS, context="DDMRP event")
    event_type = str(event["EventType"])
    payload_fields = EVENT_PAYLOAD_FIELDS_BY_TYPE.get(event_type)
    if payload_fields is None:
        raise DdmrpReplenishmentConflict(f"Unsupported DDMRP event type: {event_type}")
    if event["AggregateType"] != EVENT_AGGREGATE_TYPE_BY_EVENT[event_type]:
        raise DdmrpReplenishmentConflict("DDMRP event aggregate type mismatch.")
    payload = event["EventPayload"]
    if not isinstance(payload, Mapping):
        raise DdmrpReplenishmentConflict("DDMRP event payload must be a mapping.")
    _require_exact_fields(payload, payload_fields, context=f"{event_type} payload")
    if event["PayloadFingerprint"] != canonical_fingerprint(dict(payload)):
        raise DdmrpReplenishmentConflict("DDMRP event payload fingerprint mismatch.")
    version = event["AggregateVersion"]
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise DdmrpReplenishmentConflict(
            "DDMRP aggregate versions must be positive integers."
        )
    expected_id = canonical_stable_id(
        "DRE",
        {
            "AggregateType": event["AggregateType"],
            "AggregateID": event["AggregateID"],
            "AggregateVersion": version,
            "EventType": event_type,
        },
    )
    if event["EventID"] != expected_id:
        raise DdmrpReplenishmentConflict("DDMRP event canonical ID mismatch.")


def _fold_status(
    *,
    aggregate_type: str,
    aggregate_id: str,
    creation_event_type: str,
    creation_status: str,
    events: Iterable[Mapping[str, object]],
    terminal_statuses: frozenset[str],
) -> str:
    selected = [
        event for event in events
        if event.get("AggregateType") == aggregate_type
        and event.get("AggregateID") == aggregate_id
    ]
    if not selected:
        raise DdmrpReplenishmentConflict("DDMRP aggregate has no creation event.")
    versions: set[int] = set()
    for event in selected:
        _validate_event_contract(event)
        version = event["AggregateVersion"]
        if version in versions:
            raise DdmrpReplenishmentConflict(
                "DDMRP aggregate versions must be unique contiguous integers starting at 1."
            )
        versions.add(version)
    selected.sort(key=lambda event: (event["AggregateVersion"], str(event["EventID"])))
    current: str | None = None
    for expected_version, event in enumerate(selected, start=1):
        if event["AggregateVersion"] != expected_version:
            raise DdmrpReplenishmentConflict(
                "DDMRP aggregate versions must be unique contiguous integers starting at 1."
            )
        if event["StatusBefore"] != current:
            raise DdmrpReplenishmentConflict("DDMRP event StatusBefore does not match fold.")
        event_type = str(event["EventType"])
        status_after = str(event["StatusAfter"])
        if expected_version == 1:
            if event_type != creation_event_type or status_after != creation_status:
                raise DdmrpReplenishmentConflict(
                    "DDMRP aggregate must start with its exact version-1 creation event."
                )
        else:
            if current in terminal_statuses:
                raise DdmrpReplenishmentConflict("Terminal DDMRP aggregate has a later event.")
            transition = EVENT_TRANSITION_BY_TYPE.get(event_type)
            if transition is None:
                raise DdmrpReplenishmentConflict("Creation event cannot appear after version 1.")
            allowed_before, required_after = transition
            if current not in allowed_before or status_after != required_after:
                raise DdmrpReplenishmentConflict("Illegal DDMRP event status transition.")
        current = status_after
    assert current is not None
    return current


def fold_recommendation_status(
    recommendation: Mapping[str, object],
    events: Iterable[Mapping[str, object]],
) -> str:
    frozen_events = tuple(events)
    status = _fold_status(
        aggregate_type="Recommendation",
        aggregate_id=str(recommendation["RecommendationID"]),
        creation_event_type="RecommendationVersionCreated",
        creation_status=str(recommendation["InitialStatus"]),
        events=frozen_events,
        terminal_statuses=RECOMMENDATION_TERMINAL_STATUSES,
    )
    creation = _aggregate_events(
        frozen_events, "Recommendation", str(recommendation["RecommendationID"])
    )[0]
    payload = creation["EventPayload"]
    if (
        payload["RecommendationVersion"] != recommendation["RecommendationVersion"]
        or payload["SuggestedReplenishmentQty"]
        != recommendation["SuggestedReplenishmentQty"]
        or payload["GateCodes"] != recommendation["GateCodes"]
        or payload["PredecessorRecommendationID"]
        != recommendation["PredecessorRecommendationID"]
        or payload["AdjustmentOfRecommendationID"]
        != recommendation["AdjustmentOfRecommendationID"]
    ):
        raise DdmrpReplenishmentConflict(
            "Recommendation creation payload does not match immutable record."
        )
    return status


def fold_chain_status(
    chain: Mapping[str, object],
    events: Iterable[Mapping[str, object]],
) -> str:
    frozen_events = tuple(events)
    status = _fold_status(
        aggregate_type="ReplenishmentChain",
        aggregate_id=str(chain["LogicalReplenishmentID"]),
        creation_event_type="ReplenishmentChainOpened",
        creation_status="Open",
        events=frozen_events,
        terminal_statuses=CHAIN_TERMINAL_STATUSES,
    )
    creation = _aggregate_events(
        frozen_events, "ReplenishmentChain", str(chain["LogicalReplenishmentID"])
    )[0]
    payload = creation["EventPayload"]
    if payload != {
        "CycleNumber": chain["CycleNumber"],
        "ItemID": chain["ItemID"],
        "LocationID": chain["LocationID"],
        "OpenedByEvaluationID": chain["OpenedByEvaluationID"],
    }:
        raise DdmrpReplenishmentConflict(
            "Replenishment chain creation payload does not match immutable record."
        )
    return status


def prepare_ddmrp_evaluation(
    *,
    evaluation_request_id: str,
    recorded_at: datetime,
    actor_id: str,
    runtime_result: Mapping[str, object],
    authority_signature: DdmrpAuthoritySignature,
    gates: tuple[DdmrpGate, ...],
    existing_chains: Mapping[str, Mapping[str, object]],
    existing_recommendations: Mapping[str, Mapping[str, object]],
    existing_events: tuple[Mapping[str, object], ...],
    active_replenishment_graphs: Mapping[str, Mapping[str, object]],
) -> DdmrpEvaluationWriteSet:
    request_id = _required_text(evaluation_request_id, "evaluation request ID")
    actor = _required_text(actor_id, "actor ID")
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise DdmrpReplenishmentConflict("recorded_at must be timezone-aware.")
    recorded_text = recorded_at.isoformat()
    _require_exact_fields(runtime_result, _RUNTIME_RESULT_FIELDS, context="DDMRP runtime result")
    evaluated_at = _required_text(runtime_result.get("EvaluatedAt"), "EvaluatedAt")
    if (
        evaluated_at != authority_signature.runtime_snapshot_at
        or not evaluated_at.endswith("+00:00")
    ):
        raise DdmrpReplenishmentConflict(
            "Runtime evaluation time must equal the canonical authority snapshot time."
        )
    lines = runtime_result.get("Lines")
    if not isinstance(lines, list):
        raise DdmrpReplenishmentConflict("DDMRP runtime Lines must be a list.")
    if not all(isinstance(line, Mapping) for line in lines):
        raise DdmrpReplenishmentConflict("DDMRP runtime line must be a mapping.")
    signature = asdict(authority_signature)
    if set(signature) != set(DdmrpAuthoritySignature.__dataclass_fields__):
        raise DdmrpReplenishmentConflict("DDMRP authority signature fields differ.")
    if canonical_fingerprint(
        {key: value for key, value in signature.items() if key != "signature_fingerprint"}
    ) != authority_signature.signature_fingerprint:
        raise DdmrpReplenishmentConflict("DDMRP authority signature fingerprint mismatch.")

    gate_records = _freeze_gates(gates)
    operational_allowed = not any(
        gate["BlocksOperationalAction"] for gate in gate_records
    )
    request_fingerprint = canonical_fingerprint({
        "EvaluationRequestID": request_id,
        "RuntimePlanningInputPackageID": authority_signature.runtime_package_id,
    })
    evaluation_id = canonical_stable_id("DDE", {
        "AuthoritySignatureFingerprint": authority_signature.signature_fingerprint,
        "EvaluationAt": evaluated_at,
    })

    existing_chain_rows, chain_statuses = _validate_existing_chains(
        existing_chains, existing_events, active_replenishment_graphs
    )
    existing_recommendation_rows, recommendation_statuses = (
        _validate_existing_recommendations(
            existing_recommendations, existing_events, existing_chain_rows
        )
    )
    _validate_event_references(
        existing_events, existing_chain_rows, existing_recommendation_rows,
        active_replenishment_graphs,
    )

    issues = _build_issues(evaluation_id, gate_records)
    evaluation_rows: list[dict[str, object]] = []
    chain_records: list[dict[str, object]] = []
    recommendations: list[dict[str, object]] = []
    new_events: list[dict[str, object]] = []
    created_logical_ids: set[str] = set()
    reused_logical_ids: set[str] = set()

    seen_row_keys: set[str] = set()
    for source_line in sorted(
        lines, key=lambda row: (str(row.get("ItemID")), str(row.get("LocationID")))
    ):
        line = deepcopy(dict(source_line))
        _require_exact_fields(line, _RUNTIME_LINE_FIELDS, context="DDMRP runtime line")
        demand_components = _freeze_components(
            line["DemandComponents"], DEMAND_COMPONENT_FIELDS, "demand component"
        )
        supply_components = _freeze_components(
            line["SupplyComponents"], SUPPLY_COMPONENT_FIELDS, "supply component"
        )
        item_id = _required_text(line["ItemID"], "ItemID")
        location_id = _required_text(line["LocationID"], "LocationID")
        row_key = _canonical_json({"ItemID": item_id, "LocationID": location_id})
        if row_key in seen_row_keys:
            raise DdmrpReplenishmentConflict("Duplicate DDMRP runtime item/location row.")
        seen_row_keys.add(row_key)
        evaluation_row_id = canonical_stable_id(
            "DER", {"EvaluationID": evaluation_id, "RowKey": row_key}
        )
        planning_status = _required_text(line["PlanningStatus"], "PlanningStatus")
        suggested_qty = line["SuggestedReplenishmentQty"]
        actionable = planning_status in {"Red", "Yellow"} and suggested_qty > 0
        recommendation_id: str | None = None
        if actionable:
            chain, created = _select_or_create_chain(
                item_id=item_id,
                location_id=location_id,
                evaluation_id=evaluation_id,
                evaluated_at=evaluated_at,
                existing_chains=existing_chain_rows,
                chain_statuses=chain_statuses,
            )
            logical_id = str(chain["LogicalReplenishmentID"])
            if created:
                chain_records.append(chain)
                existing_chain_rows[logical_id] = chain
                chain_statuses[logical_id] = "Open"
                created_logical_ids.add(logical_id)
                new_events.append(_new_event(
                    event_type="ReplenishmentChainOpened",
                    aggregate_type="ReplenishmentChain",
                    aggregate_id=logical_id,
                    aggregate_version=1,
                    evaluation_id=evaluation_id,
                    logical_id=logical_id,
                    recommendation_id=None,
                    related_recommendation_id=None,
                    status_before=None,
                    status_after="Open",
                    occurred_at=recorded_text,
                    actor_id=actor,
                    causation_id=request_id,
                    correlation_id=evaluation_id,
                    payload={
                        "CycleNumber": chain["CycleNumber"],
                        "ItemID": item_id,
                        "LocationID": location_id,
                        "OpenedByEvaluationID": evaluation_id,
                    },
                ))
            else:
                reused_logical_ids.add(logical_id)

            prior = sorted(
                (
                    recommendation for recommendation in existing_recommendation_rows.values()
                    if recommendation["LogicalReplenishmentID"] == logical_id
                ),
                key=lambda recommendation: recommendation["RecommendationVersion"],
            )
            predecessor = prior[-1] if prior else None
            version = len(prior) + 1
            recommendation_id = canonical_stable_id("DDR", {
                "LogicalReplenishmentID": logical_id,
                "RecommendationVersion": version,
            })
            graph = active_replenishment_graphs.get(logical_id)
            adjustment_of = None
            initial_status = "Blocked"
            if graph is not None:
                adjustment_of = _required_text(
                    graph.get("RecommendationID"), "active graph RecommendationID"
                )
                if adjustment_of not in existing_recommendation_rows:
                    raise DdmrpReplenishmentConflict(
                        "Active replenishment graph recommendation is missing."
                    )
                initial_status = "AdjustmentRequired"
            recommendation = {
                "RecommendationID": recommendation_id,
                "LogicalReplenishmentID": logical_id,
                "RecommendationVersion": version,
                "EvaluationID": evaluation_id,
                "EvaluationRowID": evaluation_row_id,
                "ItemID": item_id,
                "LocationID": location_id,
                "Uom": deepcopy(line["Uom"]),
                "PlanningStatus": planning_status,
                "ExecutionStatus": deepcopy(line["ExecutionStatus"]),
                "SuggestedReplenishmentQty": deepcopy(suggested_qty),
                "StandardTargetReceiptAt": None,
                "AdviceType": None,
                "InitialStatus": initial_status,
                "GateCodes": deepcopy(gate_records),
                "PredecessorRecommendationID": (
                    predecessor["RecommendationID"] if predecessor else None
                ),
                "AdjustmentOfRecommendationID": adjustment_of,
                "CreatedAt": recorded_text,
                "CreatedBy": actor,
                "AuthoritySignature": deepcopy(signature),
                "AuthoritySignatureFingerprint": authority_signature.signature_fingerprint,
                "RelevantPlanningLedgerIdentity": authority_signature.local_planning_ledger_identity,
                "RelevantPlanningLedgerFingerprint": authority_signature.local_planning_ledger_fingerprint,
                "TraceID": logical_id,
            }
            recommendation["RecommendationFingerprint"] = canonical_fingerprint(recommendation)
            recommendations.append(recommendation)
            existing_recommendation_rows[recommendation_id] = recommendation
            recommendation_statuses[recommendation_id] = initial_status
            new_events.append(_new_event(
                event_type="RecommendationVersionCreated",
                aggregate_type="Recommendation",
                aggregate_id=recommendation_id,
                aggregate_version=1,
                evaluation_id=evaluation_id,
                logical_id=logical_id,
                recommendation_id=recommendation_id,
                related_recommendation_id=(
                    predecessor["RecommendationID"] if predecessor else None
                ),
                status_before=None,
                status_after=initial_status,
                occurred_at=recorded_text,
                actor_id=actor,
                causation_id=request_id,
                correlation_id=evaluation_id,
                payload={
                    "RecommendationVersion": version,
                    "SuggestedReplenishmentQty": deepcopy(suggested_qty),
                    "GateCodes": deepcopy(gate_records),
                    "PredecessorRecommendationID": (
                        predecessor["RecommendationID"] if predecessor else None
                    ),
                    "AdjustmentOfRecommendationID": adjustment_of,
                },
            ))
            if predecessor is not None:
                predecessor_id = str(predecessor["RecommendationID"])
                predecessor_status = recommendation_statuses[predecessor_id]
                if predecessor_status in {"Blocked", "PendingReview", "AdjustmentRequired"}:
                    aggregate_version = 1 + max(
                        event["AggregateVersion"] for event in (*existing_events, *new_events)
                        if event["AggregateType"] == "Recommendation"
                        and event["AggregateID"] == predecessor_id
                    )
                    new_events.append(_new_event(
                        event_type="RecommendationSuperseded",
                        aggregate_type="Recommendation",
                        aggregate_id=predecessor_id,
                        aggregate_version=aggregate_version,
                        evaluation_id=evaluation_id,
                        logical_id=logical_id,
                        recommendation_id=predecessor_id,
                        related_recommendation_id=recommendation_id,
                        status_before=predecessor_status,
                        status_after="Superseded",
                        occurred_at=recorded_text,
                        actor_id=actor,
                        causation_id=request_id,
                        correlation_id=evaluation_id,
                        payload={
                            "SupersededByRecommendationID": recommendation_id,
                            "SupersedingEvaluationID": evaluation_id,
                        },
                    ))
                    recommendation_statuses[predecessor_id] = "Superseded"

        row = {
            "EvaluationRowID": evaluation_row_id,
            "EvaluationID": evaluation_id,
            "EvaluationAt": evaluated_at,
            "RowKey": row_key,
            "ItemID": item_id,
            "LocationID": location_id,
            "Uom": deepcopy(line["Uom"]),
            "BufferProfileID": deepcopy(line["BufferProfileID"]),
            "DLTMinutes": deepcopy(line["DLTMinutes"]),
            "QualifiedOnHandQty": deepcopy(line["QualifiedOnHandQty"]),
            "PhysicalOnHandQty": deepcopy(line["PhysicalOnHandQty"]),
            "AuthorityAllocatedQty": deepcopy(line["AuthorityAllocatedQty"]),
            "AuthorityAvailableQty": deepcopy(line["AuthorityAvailableQty"]),
            "QualityState": deepcopy(line["QualityState"]),
            "QualifiedOpenSupplyQty": deepcopy(line["QualifiedOpenSupplyQty"]),
            "QualifiedDemandQty": deepcopy(line["QualifiedDemandQty"]),
            "NetFlowPosition": deepcopy(line["NetFlowPosition"]),
            "TopOfRed": deepcopy(line["TopOfRed"]),
            "TopOfYellow": deepcopy(line["TopOfYellow"]),
            "TopOfGreen": deepcopy(line["TopOfGreen"]),
            "PlanningStatus": planning_status,
            "ExecutionStatus": deepcopy(line["ExecutionStatus"]),
            "SuggestedReplenishmentQty": deepcopy(suggested_qty),
            "RecommendedAction": deepcopy(line["RecommendedAction"]),
            "StandardTargetReceiptAt": None,
            "TargetStatusCode": "DLT_TARGET_SEMANTICS_INSUFFICIENT",
            "RecommendationID": recommendation_id,
            "DemandComponents": demand_components,
            "SupplyComponents": supply_components,
            "GateCodes": deepcopy(gate_records),
            "OperationalActionAllowed": operational_allowed,
            "AuthoritySignatureFingerprint": authority_signature.signature_fingerprint,
        }
        row["EvaluationRowFingerprint"] = canonical_fingerprint(row)
        evaluation_rows.append(row)

    summary = {
        "RedCount": sum(row["PlanningStatus"] == "Red" for row in evaluation_rows),
        "YellowCount": sum(row["PlanningStatus"] == "Yellow" for row in evaluation_rows),
        "GreenCount": sum(row["PlanningStatus"] == "Green" for row in evaluation_rows),
        "AboveGreenCount": sum(
            row["PlanningStatus"] == "AboveGreen" for row in evaluation_rows
        ),
        "BlockedRecommendationCount": sum(
            row["InitialStatus"] == "Blocked" for row in recommendations
        ),
        "AdjustmentRequiredCount": sum(
            row["InitialStatus"] == "AdjustmentRequired" for row in recommendations
        ),
        "IssueCount": len(issues),
    }
    evaluation_run = {
        "EvaluationID": evaluation_id,
        "EvaluationRequestID": request_id,
        "EvaluationAt": evaluated_at,
        "RecordedAt": recorded_text,
        "RecordedBy": actor,
        "EvaluationMode": deepcopy(runtime_result["EvaluationMode"]),
        "RuntimePlanningInputPackageID": authority_signature.runtime_package_id,
        "RuntimePlanningInputPackageVersion": authority_signature.runtime_package_version,
        "RuntimeSnapshotID": authority_signature.runtime_snapshot_id,
        "OperatingModelConfigurationID": authority_signature.operating_model_configuration_id,
        "OperatingModelFingerprint": authority_signature.operating_model_fingerprint,
        "DDMRPConfigurationID": authority_signature.ddmrp_configuration_id,
        "AuthoritySignature": deepcopy(signature),
        "AuthoritySignatureFingerprint": authority_signature.signature_fingerprint,
        "RelevantPlanningLedgerIdentity": authority_signature.local_planning_ledger_identity,
        "RelevantPlanningLedgerFingerprint": authority_signature.local_planning_ledger_fingerprint,
        "Summary": summary,
        "Issues": issues,
        "OperationalActionAllowed": operational_allowed,
    }
    evaluation_run["EvaluationFingerprint"] = canonical_fingerprint(evaluation_run)

    all_events = (*existing_events, *new_events)
    _validate_event_references(
        all_events, existing_chain_rows, existing_recommendation_rows,
        active_replenishment_graphs,
    )
    for chain in existing_chain_rows.values():
        fold_chain_status(chain, all_events)
    for recommendation in existing_recommendation_rows.values():
        fold_recommendation_status(recommendation, all_events)

    evaluation_rows.sort(key=lambda row: (row["ItemID"], row["LocationID"]))
    chain_records.sort(key=lambda row: row["LogicalReplenishmentID"])
    recommendations.sort(key=lambda row: row["RecommendationID"])
    new_events.sort(key=lambda row: (row["AggregateType"], row["AggregateID"], row["AggregateVersion"]))
    payload = {
        "EvaluationRun": evaluation_run,
        "EvaluationRows": evaluation_rows,
        "ChainRecords": chain_records,
        "RecommendationVersions": recommendations,
        "Events": new_events,
    }
    payload_fingerprint = canonical_fingerprint(payload)
    created_ids = sorted(created_logical_ids)
    reused_ids = sorted(reused_logical_ids)
    if set(created_ids) & set(reused_ids):
        raise DdmrpReplenishmentConflict(
            "Created and reused logical replenishment memberships overlap."
        )
    logical_ids = sorted((*created_ids, *reused_ids))
    recommendation_ids = sorted(
        recommendation["RecommendationID"] for recommendation in recommendations
    )
    response_data = {
        "Status": "Created",
        "EvaluationID": evaluation_id,
        "RecommendationIDs": recommendation_ids,
        "OperationalActionAllowed": operational_allowed,
    }
    request_result = {
        "EvaluationRequestID": request_id,
        "RequestFingerprint": request_fingerprint,
        "RuntimePlanningInputPackageID": authority_signature.runtime_package_id,
        "EvaluationID": evaluation_id,
        "EvaluationRowIDs": sorted(row["EvaluationRowID"] for row in evaluation_rows),
        "LogicalReplenishmentIDs": logical_ids,
        "CreatedLogicalReplenishmentIDs": created_ids,
        "ReusedLogicalReplenishmentIDs": reused_ids,
        "RecommendationIDs": recommendation_ids,
        "EventIDs": sorted(event["EventID"] for event in new_events),
        "EvaluationPayloadFingerprint": payload_fingerprint,
        "ResponseData": response_data,
        "ResponseFingerprint": canonical_fingerprint(response_data),
        "RecordedAt": recorded_text,
        "RecordedBy": actor,
    }
    request_result["RequestResultFingerprint"] = canonical_fingerprint(request_result)
    _validate_request_result(request_result)
    return DdmrpEvaluationWriteSet(
        evaluation_request_id=request_id,
        request_fingerprint=request_fingerprint,
        payload_fingerprint=payload_fingerprint,
        evaluation_run=deepcopy(evaluation_run),
        evaluation_rows=tuple(deepcopy(evaluation_rows)),
        chain_records=tuple(deepcopy(chain_records)),
        recommendation_versions=tuple(deepcopy(recommendations)),
        events=tuple(deepcopy(new_events)),
        request_result=deepcopy(request_result),
    )


def lookup_ddmrp_evaluation_request_result(
    *,
    evaluation_request_id: str,
    request_fingerprint: str,
    request_results: Mapping[str, Mapping[str, object]],
    evaluation_runs: Mapping[str, Mapping[str, object]],
    evaluation_rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: tuple[Mapping[str, object], ...],
) -> dict[str, object] | None:
    persisted = request_results.get(evaluation_request_id)
    if persisted is None:
        return None
    if persisted.get("EvaluationRequestID") != evaluation_request_id:
        raise DdmrpReplenishmentConflict(
            "EVALUATION_REQUEST_RESULT_KEY_MISMATCH"
        )
    _require_exact_fields(
        persisted,
        REQUEST_RESULT_FIELDS,
        context="DDMRP evaluation request result",
    )
    fingerprint_source = {
        key: deepcopy(persisted[key])
        for key in REQUEST_RESULT_FIELDS
        if key != "RequestResultFingerprint"
    }
    if persisted["RequestResultFingerprint"] != canonical_fingerprint(
        fingerprint_source
    ):
        raise DdmrpReplenishmentConflict("EVALUATION_REQUEST_RESULT_DRIFT")
    if persisted["RequestFingerprint"] != request_fingerprint:
        raise DdmrpReplenishmentConflict("EVALUATION_REQUEST_ID_REUSED")
    _validate_persisted_evaluation_result_graph(
        result=persisted,
        evaluation_runs=evaluation_runs,
        evaluation_rows=evaluation_rows,
        chains=chains,
        recommendations=recommendations,
        events=events,
    )
    response = deepcopy(dict(persisted["ResponseData"]))
    response["Status"] = "Duplicate"
    return response


def stage_ddmrp_evaluation(
    *,
    write_set: DdmrpEvaluationWriteSet,
    evaluation_runs: Mapping[str, Mapping[str, object]],
    evaluation_rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
    request_results: Mapping[str, Mapping[str, object]],
) -> DdmrpEvaluationStagedState:
    _assert_unique_write_set_ids(write_set)
    _assert_write_set_fingerprints(write_set)

    staged_runs = deepcopy(dict(evaluation_runs))
    staged_rows = deepcopy(dict(evaluation_rows))
    staged_chains = deepcopy(dict(chains))
    staged_recommendations = deepcopy(dict(recommendations))
    staged_events = tuple(deepcopy(tuple(events)))
    staged_results = deepcopy(dict(request_results))

    replayed = lookup_ddmrp_evaluation_request_result(
        evaluation_request_id=write_set.evaluation_request_id,
        request_fingerprint=write_set.request_fingerprint,
        request_results=staged_results,
        evaluation_runs=staged_runs,
        evaluation_rows=staged_rows,
        chains=staged_chains,
        recommendations=staged_recommendations,
        events=staged_events,
    )
    if replayed is not None:
        return DdmrpEvaluationStagedState(
            evaluation_runs=staged_runs,
            evaluation_rows=staged_rows,
            chains=staged_chains,
            recommendations=staged_recommendations,
            events=staged_events,
            request_results=staged_results,
            result_status="Duplicate",
            response_data=deepcopy(replayed),
        )

    target_ids = {
        "evaluation": str(write_set.evaluation_run["EvaluationID"]),
        "rows": {str(row["EvaluationRowID"]) for row in write_set.evaluation_rows},
        "chains": {str(row["LogicalReplenishmentID"]) for row in write_set.chain_records},
        "recommendations": {
            str(row["RecommendationID"])
            for row in write_set.recommendation_versions
        },
        "events": {str(row["EventID"]) for row in write_set.events},
    }
    existing_event_ids = {str(event.get("EventID")) for event in staged_events}
    if (
        target_ids["evaluation"] in staged_runs
        or target_ids["rows"] & set(staged_rows)
        or target_ids["chains"] & set(staged_chains)
        or target_ids["recommendations"] & set(staged_recommendations)
        or target_ids["events"] & existing_event_ids
    ):
        raise DdmrpReplenishmentConflict("ORPHAN_DDMRP_EVALUATION_CHILD")

    reused_ids = set(write_set.request_result["ReusedLogicalReplenishmentIDs"])
    created_ids = set(write_set.request_result["CreatedLogicalReplenishmentIDs"])
    if reused_ids & target_ids["chains"] or created_ids != target_ids["chains"]:
        raise DdmrpReplenishmentConflict(
            "DDMRP write set created/reused chain membership differs."
        )
    if not reused_ids <= set(staged_chains):
        raise DdmrpReplenishmentConflict("DDMRP reused chain is missing.")

    prospective_events = (*staged_events, *deepcopy(write_set.events))
    _, existing_chain_statuses = _validate_existing_chains(
        staged_chains, staged_events, {}
    )
    for logical_id in reused_ids:
        if existing_chain_statuses[logical_id] not in CHAIN_ACTIVE_STATUSES:
            raise DdmrpReplenishmentConflict(
                "DDMRP reused chain must be non-terminal."
            )
        if not any(
            recommendation["LogicalReplenishmentID"] == logical_id
            for recommendation in write_set.recommendation_versions
        ):
            raise DdmrpReplenishmentConflict(
                "DDMRP reused chain has no new recommendation."
            )

    staged_runs[target_ids["evaluation"]] = deepcopy(write_set.evaluation_run)
    for row in write_set.evaluation_rows:
        staged_rows[str(row["EvaluationRowID"])] = deepcopy(row)
    for row in write_set.chain_records:
        staged_chains[str(row["LogicalReplenishmentID"])] = deepcopy(row)
    for row in write_set.recommendation_versions:
        staged_recommendations[str(row["RecommendationID"])] = deepcopy(row)
    staged_events = tuple(deepcopy(prospective_events))

    _validate_existing_chains(staged_chains, staged_events, {})
    _validate_existing_recommendations(
        staged_recommendations, staged_events, staged_chains
    )
    _validate_event_references(
        staged_events, staged_chains, staged_recommendations, {},
        require_active_graph_references=False,
    )
    _validate_persisted_evaluation_result_graph(
        result=write_set.request_result,
        evaluation_runs=staged_runs,
        evaluation_rows=staged_rows,
        chains=staged_chains,
        recommendations=staged_recommendations,
        events=staged_events,
    )
    staged_results[write_set.evaluation_request_id] = deepcopy(
        write_set.request_result
    )
    return DdmrpEvaluationStagedState(
        evaluation_runs=staged_runs,
        evaluation_rows=staged_rows,
        chains=staged_chains,
        recommendations=staged_recommendations,
        events=staged_events,
        request_results=staged_results,
        result_status="Created",
        response_data=deepcopy(dict(write_set.request_result["ResponseData"])),
    )


def apply_staged_ddmrp_evaluation(
    *,
    staged: DdmrpEvaluationStagedState,
    evaluation_runs: MutableMapping[str, dict[str, object]],
    evaluation_rows: MutableMapping[str, dict[str, object]],
    chains: MutableMapping[str, dict[str, object]],
    recommendations: MutableMapping[str, dict[str, object]],
    events: MutableSequence[dict[str, object]],
    request_results: MutableMapping[str, dict[str, object]],
) -> tuple[Literal["Created", "Duplicate"], dict[str, object]]:
    snapshots = (
        deepcopy(dict(evaluation_runs)),
        deepcopy(dict(evaluation_rows)),
        deepcopy(dict(chains)),
        deepcopy(dict(recommendations)),
        deepcopy(list(events)),
        deepcopy(dict(request_results)),
    )
    try:
        _replace_mapping(evaluation_runs, staged.evaluation_runs)
        _replace_mapping(evaluation_rows, staged.evaluation_rows)
        _replace_mapping(chains, staged.chains)
        _replace_mapping(recommendations, staged.recommendations)
        _replace_sequence(events, staged.events)
        _replace_mapping(request_results, staged.request_results)
    except BaseException:
        _replace_mapping(evaluation_runs, snapshots[0])
        _replace_mapping(evaluation_rows, snapshots[1])
        _replace_mapping(chains, snapshots[2])
        _replace_mapping(recommendations, snapshots[3])
        _replace_sequence(events, snapshots[4])
        _replace_mapping(request_results, snapshots[5])
        raise
    return deepcopy((staged.result_status, staged.response_data))


def _freeze_gates(gates: tuple[DdmrpGate, ...]) -> list[dict[str, object]]:
    by_code: dict[str, dict[str, object]] = {}
    for gate in gates:
        record = {
            "Code": _required_text(gate.code, "gate code"),
            "Message": _required_text(gate.message, "gate message"),
            "BlocksOperationalAction": gate.blocks_operational_action,
        }
        _require_exact_fields(record, GATE_FIELDS, context="DDMRP gate")
        prior = by_code.get(gate.code)
        if prior is not None and prior != record:
            raise DdmrpReplenishmentConflict("Duplicate DDMRP gate code differs.")
        by_code[gate.code] = record
    return [deepcopy(by_code[code]) for code in sorted(by_code)]


def _freeze_components(
    value: object, fields: tuple[str, ...], context: str
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise DdmrpReplenishmentConflict(f"DDMRP {context}s must be a list.")
    result: list[dict[str, object]] = []
    for component in value:
        if not isinstance(component, Mapping):
            raise DdmrpReplenishmentConflict(f"DDMRP {context} must be a mapping.")
        _require_exact_fields(component, fields, context=f"DDMRP {context}")
        frozen = deepcopy(dict(component))
        canonical_fingerprint(frozen)
        result.append(frozen)
    return sorted(result, key=_canonical_json)


def _build_issues(
    evaluation_id: str, gates: list[dict[str, object]]
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for gate in gates:
        issue = {
            "IssueID": canonical_stable_id("DRI", {
                "EvaluationID": evaluation_id,
                "Code": gate["Code"],
                "ItemID": None,
                "LocationID": None,
            }),
            "EvaluationID": evaluation_id,
            "Code": gate["Code"],
            "Severity": (
                "Blocking" if gate["BlocksOperationalAction"] else "Warning"
            ),
            "Message": gate["Message"],
            "ItemID": None,
            "LocationID": None,
            "BlocksOperationalAction": gate["BlocksOperationalAction"],
        }
        issue["IssueFingerprint"] = canonical_fingerprint(issue)
        _validate_issue(issue)
        issues.append(issue)
    return sorted(issues, key=lambda issue: issue["Code"])


def _validate_issue(issue: Mapping[str, object]) -> None:
    _require_exact_fields(issue, ISSUE_RECORD_FIELDS, context="DDMRP issue")
    if issue["Severity"] not in ISSUE_SEVERITIES:
        raise DdmrpReplenishmentConflict("Unsupported DDMRP issue severity.")
    expected_id = canonical_stable_id("DRI", {
        "EvaluationID": issue["EvaluationID"],
        "Code": issue["Code"],
        "ItemID": issue["ItemID"],
        "LocationID": issue["LocationID"],
    })
    if issue["IssueID"] != expected_id:
        raise DdmrpReplenishmentConflict("DDMRP issue canonical ID mismatch.")
    expected = canonical_fingerprint({
        key: value for key, value in issue.items() if key != "IssueFingerprint"
    })
    if issue["IssueFingerprint"] != expected:
        raise DdmrpReplenishmentConflict("DDMRP issue fingerprint mismatch.")


def _select_or_create_chain(
    *,
    item_id: str,
    location_id: str,
    evaluation_id: str,
    evaluated_at: str,
    existing_chains: Mapping[str, Mapping[str, object]],
    chain_statuses: Mapping[str, str],
) -> tuple[dict[str, object], bool]:
    scoped = [
        chain for chain in existing_chains.values()
        if chain["ItemID"] == item_id and chain["LocationID"] == location_id
    ]
    active = [
        chain for chain in scoped
        if chain_statuses[str(chain["LogicalReplenishmentID"])] in CHAIN_ACTIVE_STATUSES
    ]
    if len(active) > 1:
        raise DdmrpReplenishmentConflict(
            "Multiple non-terminal replenishment chains exist for item/location."
        )
    if active:
        return deepcopy(active[0]), False
    cycle_number = max((int(chain["CycleNumber"]) for chain in scoped), default=0) + 1
    identity = {
        "ItemID": item_id,
        "LocationID": location_id,
        "CycleNumber": cycle_number,
    }
    logical_id = canonical_stable_id("DRL", identity)
    chain = {
        "LogicalReplenishmentID": logical_id,
        "ItemID": item_id,
        "LocationID": location_id,
        "CycleNumber": cycle_number,
        "OpenedAt": evaluated_at,
        "OpenedByEvaluationID": evaluation_id,
        "InitialStatus": "Open",
        "IdentityFingerprint": canonical_fingerprint(identity),
        "TraceID": logical_id,
    }
    chain["ChainFingerprint"] = canonical_fingerprint(chain)
    return chain, True


def _validate_existing_chains(
    chains: Mapping[str, Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
    active_graphs: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    result: dict[str, dict[str, object]] = {}
    statuses: dict[str, str] = {}
    active_by_scope: set[tuple[str, str]] = set()
    for key, source in chains.items():
        if not isinstance(source, Mapping):
            raise DdmrpReplenishmentConflict("DDMRP chain must be a mapping.")
        _require_exact_fields(source, REPLENISHMENT_CHAIN_FIELDS, context="DDMRP chain")
        chain = deepcopy(dict(source))
        logical_id = _required_text(chain["LogicalReplenishmentID"], "LogicalReplenishmentID")
        if key != logical_id or logical_id in result:
            raise DdmrpReplenishmentConflict("DDMRP chain mapping identity mismatch.")
        identity = {
            "ItemID": chain["ItemID"], "LocationID": chain["LocationID"],
            "CycleNumber": chain["CycleNumber"],
        }
        if chain["IdentityFingerprint"] != canonical_fingerprint(identity):
            raise DdmrpReplenishmentConflict("DDMRP chain identity fingerprint mismatch.")
        if logical_id != canonical_stable_id("DRL", identity):
            raise DdmrpReplenishmentConflict("DDMRP chain canonical ID mismatch.")
        if chain["ChainFingerprint"] != canonical_fingerprint({
            field: value for field, value in chain.items() if field != "ChainFingerprint"
        }):
            raise DdmrpReplenishmentConflict("DDMRP chain fingerprint mismatch.")
        status = fold_chain_status(chain, events)
        scope = (str(chain["ItemID"]), str(chain["LocationID"]))
        if status in CHAIN_ACTIVE_STATUSES:
            if scope in active_by_scope:
                raise DdmrpReplenishmentConflict(
                    "Multiple non-terminal replenishment chains exist for item/location."
                )
            active_by_scope.add(scope)
        result[logical_id] = chain
        statuses[logical_id] = status
    for key, graph in active_graphs.items():
        if not isinstance(graph, Mapping) or key != graph.get("LogicalReplenishmentID"):
            raise DdmrpReplenishmentConflict("Active graph mapping identity mismatch.")
        if key not in result:
            raise DdmrpReplenishmentConflict("Active graph replenishment chain is missing.")
        if statuses[key] in CHAIN_TERMINAL_STATUSES:
            raise DdmrpReplenishmentConflict("Active graph is attached to terminal chain.")
    return result, statuses


def _validate_existing_recommendations(
    recommendations: Mapping[str, Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    result: dict[str, dict[str, object]] = {}
    statuses: dict[str, str] = {}
    by_chain: dict[str, list[dict[str, object]]] = {}
    for key, source in recommendations.items():
        if not isinstance(source, Mapping):
            raise DdmrpReplenishmentConflict("DDMRP recommendation must be a mapping.")
        _require_exact_fields(source, RECOMMENDATION_FIELDS, context="DDMRP recommendation")
        recommendation = deepcopy(dict(source))
        recommendation_id = _required_text(
            recommendation["RecommendationID"], "RecommendationID"
        )
        logical_id = _required_text(
            recommendation["LogicalReplenishmentID"], "LogicalReplenishmentID"
        )
        if key != recommendation_id or recommendation_id in result:
            raise DdmrpReplenishmentConflict("DDMRP recommendation mapping identity mismatch.")
        if logical_id not in chains:
            raise DdmrpReplenishmentConflict("DDMRP recommendation chain is missing.")
        version = recommendation["RecommendationVersion"]
        if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
            raise DdmrpReplenishmentConflict("Recommendation version must be positive integer.")
        if recommendation_id != canonical_stable_id("DDR", {
            "LogicalReplenishmentID": logical_id,
            "RecommendationVersion": version,
        }):
            raise DdmrpReplenishmentConflict("DDMRP recommendation canonical ID mismatch.")
        if recommendation["RecommendationFingerprint"] != canonical_fingerprint({
            field: value for field, value in recommendation.items()
            if field != "RecommendationFingerprint"
        }):
            raise DdmrpReplenishmentConflict("DDMRP recommendation fingerprint mismatch.")
        status = fold_recommendation_status(recommendation, events)
        result[recommendation_id] = recommendation
        statuses[recommendation_id] = status
        by_chain.setdefault(logical_id, []).append(recommendation)
    for chain_recommendations in by_chain.values():
        ordered = sorted(
            chain_recommendations, key=lambda row: row["RecommendationVersion"]
        )
        if [row["RecommendationVersion"] for row in ordered] != list(
            range(1, len(ordered) + 1)
        ):
            raise DdmrpReplenishmentConflict("Recommendation version sequence has a gap.")
        successors: set[str] = set()
        for index, recommendation in enumerate(ordered):
            expected_predecessor = (
                None if index == 0 else ordered[index - 1]["RecommendationID"]
            )
            if recommendation["PredecessorRecommendationID"] != expected_predecessor:
                raise DdmrpReplenishmentConflict("Recommendation predecessor sequence differs.")
            if expected_predecessor is not None:
                if expected_predecessor in successors:
                    raise DdmrpReplenishmentConflict("Recommendation has multiple successors.")
                successors.add(expected_predecessor)
                if recommendation["AdjustmentOfRecommendationID"] is None:
                    reverse = [
                        event for event in events
                        if event.get("EventType") == "RecommendationSuperseded"
                        and event.get("AggregateID") == expected_predecessor
                        and event.get("RelatedRecommendationID")
                        == recommendation["RecommendationID"]
                    ]
                    if len(reverse) != 1:
                        raise DdmrpReplenishmentConflict(
                            "Recommendation supersession reverse event is missing."
                        )
    return result, statuses


def _validate_event_references(
    events: Iterable[Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    active_graphs: Mapping[str, Mapping[str, object]],
    *,
    require_active_graph_references: bool = True,
) -> None:
    seen_versions: set[tuple[object, object, object]] = set()
    for event in events:
        _validate_event_contract(event)
        version_key = (
            event["AggregateType"], event["AggregateID"], event["AggregateVersion"]
        )
        if version_key in seen_versions:
            raise DdmrpReplenishmentConflict("Duplicate DDMRP aggregate version.")
        seen_versions.add(version_key)
        logical_id = event["LogicalReplenishmentID"]
        if logical_id not in chains:
            raise DdmrpReplenishmentConflict("DDMRP event chain reference is missing.")
        if event["AggregateType"] == "ReplenishmentChain":
            if event["AggregateID"] != logical_id:
                raise DdmrpReplenishmentConflict("DDMRP chain event aggregate differs.")
            recommendation_id = event["RecommendationID"]
            if recommendation_id is not None and (
                recommendation_id not in recommendations
                or recommendations[recommendation_id]["LogicalReplenishmentID"]
                != logical_id
            ):
                raise DdmrpReplenishmentConflict(
                    "DDMRP chain event recommendation reference differs."
                )
        else:
            recommendation_id = event["RecommendationID"]
            if recommendation_id not in recommendations:
                raise DdmrpReplenishmentConflict(
                    "DDMRP event recommendation reference is missing."
                )
            if event["AggregateID"] != recommendation_id:
                raise DdmrpReplenishmentConflict(
                    "DDMRP recommendation event aggregate differs."
                )
            if recommendations[recommendation_id]["LogicalReplenishmentID"] != logical_id:
                raise DdmrpReplenishmentConflict(
                    "DDMRP recommendation event chain reference differs."
                )
        event_type = event["EventType"]
        payload = event["EventPayload"]
        if event_type == "RecommendationVersionCreated":
            predecessor_id = payload["PredecessorRecommendationID"]
            if event["RelatedRecommendationID"] != predecessor_id:
                raise DdmrpReplenishmentConflict(
                    "Recommendation creation predecessor reference differs."
                )
        if event_type == "RecommendationSuperseded":
            related = payload["SupersededByRecommendationID"]
            if related not in recommendations or event["RelatedRecommendationID"] != related:
                raise DdmrpReplenishmentConflict(
                    "Recommendation supersession reference differs."
                )
            if payload["SupersedingEvaluationID"] != recommendations[related]["EvaluationID"]:
                raise DdmrpReplenishmentConflict(
                    "Recommendation superseding evaluation reference differs."
                )
        if event_type == "RecommendationPendingReview" and (
            payload["AuthoritySignatureFingerprint"]
            != recommendations[event["RecommendationID"]]["AuthoritySignatureFingerprint"]
        ):
            raise DdmrpReplenishmentConflict(
                "Recommendation authority signature reference differs."
            )
        if event_type in {
            "RecommendationAdjustmentRequired", "ReplenishmentChainAdjustmentRequired"
        } and payload["AdjustmentRecommendationID"] not in recommendations:
            raise DdmrpReplenishmentConflict("Adjustment recommendation is missing.")
        if (
            event_type == "ReplenishmentChainActivated"
            and require_active_graph_references
        ):
            graph_id = payload["ActiveGraphID"]
            if graph_id not in active_graphs:
                raise DdmrpReplenishmentConflict("Activated replenishment graph is missing.")


def _new_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    aggregate_version: int,
    evaluation_id: str,
    logical_id: str,
    recommendation_id: str | None,
    related_recommendation_id: str | None,
    status_before: str | None,
    status_after: str,
    occurred_at: str,
    actor_id: str,
    causation_id: str,
    correlation_id: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    identity = {
        "AggregateType": aggregate_type,
        "AggregateID": aggregate_id,
        "AggregateVersion": aggregate_version,
        "EventType": event_type,
    }
    frozen_payload = deepcopy(dict(payload))
    event_id = canonical_stable_id("DRE", identity)
    event = {
        "EventID": event_id,
        "EventType": event_type,
        "AggregateType": aggregate_type,
        "AggregateID": aggregate_id,
        "AggregateVersion": aggregate_version,
        "EvaluationID": evaluation_id,
        "LogicalReplenishmentID": logical_id,
        "RecommendationID": recommendation_id,
        "RelatedRecommendationID": related_recommendation_id,
        "StatusBefore": status_before,
        "StatusAfter": status_after,
        "OccurredAt": occurred_at,
        "ActorID": actor_id,
        "CausationID": causation_id,
        "CorrelationID": correlation_id,
        "IdempotencyKey": event_id,
        "TraceID": logical_id,
        "EventPayload": frozen_payload,
        "PayloadFingerprint": canonical_fingerprint(frozen_payload),
    }
    _validate_event_contract(event)
    return event


def _aggregate_events(
    events: Iterable[Mapping[str, object]], aggregate_type: str, aggregate_id: str
) -> list[Mapping[str, object]]:
    return sorted(
        (
            event for event in events
            if event.get("AggregateType") == aggregate_type
            and event.get("AggregateID") == aggregate_id
        ),
        key=lambda event: event["AggregateVersion"],
    )


def _assert_unique_write_set_ids(write_set: DdmrpEvaluationWriteSet) -> None:
    for records, field in (
        (write_set.evaluation_rows, "EvaluationRowID"),
        (write_set.chain_records, "LogicalReplenishmentID"),
        (write_set.recommendation_versions, "RecommendationID"),
        (write_set.events, "EventID"),
    ):
        identifiers = [str(record.get(field)) for record in records]
        if len(identifiers) != len(set(identifiers)):
            raise DdmrpReplenishmentConflict(
                f"DDMRP write set contains duplicate {field} values."
            )


def _assert_write_set_fingerprints(write_set: DdmrpEvaluationWriteSet) -> None:
    _validate_evaluation_run_contract(write_set.evaluation_run)
    for row in write_set.evaluation_rows:
        _validate_evaluation_row_contract(row)
    for chain in write_set.chain_records:
        _validate_chain_record_contract(chain)
    for recommendation in write_set.recommendation_versions:
        _validate_recommendation_record_contract(recommendation)
    for event in write_set.events:
        _validate_event_contract(event)
    _validate_request_result(write_set.request_result)

    evaluation_id = write_set.evaluation_run["EvaluationID"]
    if (
        write_set.evaluation_request_id
        != write_set.request_result["EvaluationRequestID"]
        or write_set.request_fingerprint
        != write_set.request_result["RequestFingerprint"]
        or evaluation_id != write_set.request_result["EvaluationID"]
    ):
        raise DdmrpReplenishmentConflict("DDMRP write set root identity differs.")
    payload = _evaluation_payload(
        evaluation_run=write_set.evaluation_run,
        evaluation_rows=write_set.evaluation_rows,
        chain_records=write_set.chain_records,
        recommendations=write_set.recommendation_versions,
        events=write_set.events,
    )
    payload_fingerprint = canonical_fingerprint(payload)
    if (
        write_set.payload_fingerprint != payload_fingerprint
        or write_set.request_result["EvaluationPayloadFingerprint"]
        != payload_fingerprint
    ):
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation payload fingerprint differs."
        )


def _validate_persisted_evaluation_result_graph(
    *,
    result: Mapping[str, object],
    evaluation_runs: Mapping[str, Mapping[str, object]],
    evaluation_rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: tuple[Mapping[str, object], ...],
) -> None:
    _validate_request_result(result)
    expected_request_fingerprint = canonical_fingerprint({
        "EvaluationRequestID": result["EvaluationRequestID"],
        "RuntimePlanningInputPackageID": result["RuntimePlanningInputPackageID"],
    })
    if result["RequestFingerprint"] != expected_request_fingerprint:
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation request fingerprint differs."
        )
    evaluation_id = str(result["EvaluationID"])
    evaluation = evaluation_runs.get(evaluation_id)
    if evaluation is None:
        raise DdmrpReplenishmentConflict("DDMRP evaluation result is missing.")

    for key, run in evaluation_runs.items():
        if not isinstance(run, Mapping) or key != run.get("EvaluationID"):
            raise DdmrpReplenishmentConflict(
                "DDMRP evaluation mapping identity mismatch."
            )
        _validate_evaluation_run_contract(run)
    for key, row in evaluation_rows.items():
        if not isinstance(row, Mapping) or key != row.get("EvaluationRowID"):
            raise DdmrpReplenishmentConflict(
                "DDMRP evaluation row mapping identity mismatch."
            )
        _validate_evaluation_row_contract(row)
    for recommendation in recommendations.values():
        if not isinstance(recommendation, Mapping):
            raise DdmrpReplenishmentConflict(
                "DDMRP recommendation must be a mapping."
            )
        _validate_recommendation_record_contract(recommendation)

    chain_rows, _ = _validate_existing_chains(chains, events, {})
    recommendation_rows, _ = _validate_existing_recommendations(
        recommendations, events, chain_rows
    )
    _validate_event_references(
        events, chain_rows, recommendation_rows, {},
        require_active_graph_references=False,
    )
    event_ids: set[str] = set()
    for event in events:
        event_id = str(event["EventID"])
        if event_id in event_ids:
            raise DdmrpReplenishmentConflict("Duplicate DDMRP event ID.")
        event_ids.add(event_id)

    row_ids = _sorted_unique_ids(result["EvaluationRowIDs"], "EvaluationRowIDs")
    logical_ids = _sorted_unique_ids(
        result["LogicalReplenishmentIDs"], "LogicalReplenishmentIDs"
    )
    created_ids = _sorted_unique_ids(
        result["CreatedLogicalReplenishmentIDs"],
        "CreatedLogicalReplenishmentIDs",
    )
    reused_ids = _sorted_unique_ids(
        result["ReusedLogicalReplenishmentIDs"],
        "ReusedLogicalReplenishmentIDs",
    )
    recommendation_ids = _sorted_unique_ids(
        result["RecommendationIDs"], "RecommendationIDs"
    )
    result_event_ids = _sorted_unique_ids(result["EventIDs"], "EventIDs")

    actual_row_ids = sorted(
        key for key, row in evaluation_rows.items()
        if row["EvaluationID"] == evaluation_id
    )
    actual_created_ids = sorted(
        key for key, chain in chain_rows.items()
        if chain["OpenedByEvaluationID"] == evaluation_id
    )
    actual_recommendation_ids = sorted(
        key for key, recommendation in recommendation_rows.items()
        if recommendation["EvaluationID"] == evaluation_id
    )
    actual_event_ids = sorted(
        str(event["EventID"])
        for event in events
        if event["EvaluationID"] == evaluation_id
    )
    if (
        row_ids != actual_row_ids
        or created_ids != actual_created_ids
        or recommendation_ids != actual_recommendation_ids
        or result_event_ids != actual_event_ids
    ):
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation request result child membership differs."
        )
    if set(created_ids) & set(reused_ids) or logical_ids != sorted(
        (*created_ids, *reused_ids)
    ):
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation request result chain partition differs."
        )
    if any(logical_id not in chain_rows for logical_id in logical_ids):
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation request result chain is missing."
        )

    rows_by_id = {row_id: evaluation_rows[row_id] for row_id in row_ids}
    result_recommendations = [
        recommendation_rows[recommendation_id]
        for recommendation_id in recommendation_ids
    ]
    referenced_logical_ids = sorted({
        str(recommendation["LogicalReplenishmentID"])
        for recommendation in result_recommendations
    })
    if referenced_logical_ids != logical_ids:
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation recommendation chain membership differs."
        )
    for logical_id in created_ids:
        if chain_rows[logical_id]["OpenedByEvaluationID"] != evaluation_id:
            raise DdmrpReplenishmentConflict(
                "DDMRP created chain does not belong to evaluation."
            )
    for logical_id in reused_ids:
        if chain_rows[logical_id]["OpenedByEvaluationID"] == evaluation_id:
            raise DdmrpReplenishmentConflict(
                "DDMRP reused chain was opened by current evaluation."
            )

    for recommendation in result_recommendations:
        row_id = str(recommendation["EvaluationRowID"])
        row = rows_by_id.get(row_id)
        if row is None or row["RecommendationID"] != recommendation["RecommendationID"]:
            raise DdmrpReplenishmentConflict(
                "DDMRP recommendation evaluation row reference differs."
            )
        if (
            row["ItemID"] != recommendation["ItemID"]
            or row["LocationID"] != recommendation["LocationID"]
            or row["Uom"] != recommendation["Uom"]
            or chain_rows[str(recommendation["LogicalReplenishmentID"])]["ItemID"]
            != recommendation["ItemID"]
            or chain_rows[str(recommendation["LogicalReplenishmentID"])]["LocationID"]
            != recommendation["LocationID"]
        ):
            raise DdmrpReplenishmentConflict(
                "DDMRP recommendation item/location graph differs."
            )
    for row in rows_by_id.values():
        recommendation_id = row["RecommendationID"]
        if recommendation_id is not None and recommendation_id not in recommendation_ids:
            raise DdmrpReplenishmentConflict(
                "DDMRP evaluation row recommendation is orphaned."
            )

    selected_events = [
        event for event in events if str(event["EventID"]) in result_event_ids
    ]
    request_id = result["EvaluationRequestID"]
    if any(event["CausationID"] != request_id for event in selected_events):
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation event causation differs."
        )
    for issue in evaluation["Issues"]:
        if issue["EvaluationID"] != evaluation_id:
            raise DdmrpReplenishmentConflict(
                "DDMRP issue evaluation reference differs."
            )
    expected_summary = {
        "RedCount": sum(row["PlanningStatus"] == "Red" for row in rows_by_id.values()),
        "YellowCount": sum(
            row["PlanningStatus"] == "Yellow" for row in rows_by_id.values()
        ),
        "GreenCount": sum(
            row["PlanningStatus"] == "Green" for row in rows_by_id.values()
        ),
        "AboveGreenCount": sum(
            row["PlanningStatus"] == "AboveGreen" for row in rows_by_id.values()
        ),
        "BlockedRecommendationCount": sum(
            recommendation["InitialStatus"] == "Blocked"
            for recommendation in result_recommendations
        ),
        "AdjustmentRequiredCount": sum(
            recommendation["InitialStatus"] == "AdjustmentRequired"
            for recommendation in result_recommendations
        ),
        "IssueCount": len(evaluation["Issues"]),
    }
    if dict(evaluation["Summary"]) != expected_summary:
        raise DdmrpReplenishmentConflict("DDMRP evaluation summary differs.")

    payload = _evaluation_payload(
        evaluation_run=evaluation,
        evaluation_rows=tuple(rows_by_id.values()),
        chain_records=tuple(chain_rows[logical_id] for logical_id in created_ids),
        recommendations=tuple(result_recommendations),
        events=tuple(selected_events),
    )
    if result["EvaluationPayloadFingerprint"] != canonical_fingerprint(payload):
        raise DdmrpReplenishmentConflict(
            "DDMRP persisted evaluation payload fingerprint differs."
        )

    response = result["ResponseData"]
    expected_response = {
        "Status": "Created",
        "EvaluationID": evaluation_id,
        "RecommendationIDs": recommendation_ids,
        "OperationalActionAllowed": False,
    }
    if dict(response) != expected_response:
        raise DdmrpReplenishmentConflict(
            "DDMRP persisted evaluation response differs."
        )
    if (
        evaluation["EvaluationRequestID"] != request_id
        or evaluation["RuntimePlanningInputPackageID"]
        != result["RuntimePlanningInputPackageID"]
        or evaluation["RecordedAt"] != result["RecordedAt"]
        or evaluation["RecordedBy"] != result["RecordedBy"]
        or evaluation["OperationalActionAllowed"] is not False
    ):
        raise DdmrpReplenishmentConflict(
            "DDMRP persisted evaluation result root differs."
        )


def _validate_evaluation_run_contract(run: Mapping[str, object]) -> None:
    _require_exact_fields(run, EVALUATION_RUN_FIELDS, context="DDMRP evaluation")
    summary = run["Summary"]
    if not isinstance(summary, Mapping):
        raise DdmrpReplenishmentConflict("DDMRP evaluation summary must be a mapping.")
    _require_exact_fields(summary, EVALUATION_SUMMARY_FIELDS, context="DDMRP summary")
    issues = run["Issues"]
    if not isinstance(issues, list):
        raise DdmrpReplenishmentConflict("DDMRP evaluation issues must be a list.")
    for issue in issues:
        if not isinstance(issue, Mapping):
            raise DdmrpReplenishmentConflict("DDMRP issue must be a mapping.")
        _validate_issue(issue)
    _validate_authority_signature_contract(
        run["AuthoritySignature"], run["AuthoritySignatureFingerprint"]
    )
    expected_id = canonical_stable_id("DDE", {
        "AuthoritySignatureFingerprint": run["AuthoritySignatureFingerprint"],
        "EvaluationAt": run["EvaluationAt"],
    })
    if run["EvaluationID"] != expected_id:
        raise DdmrpReplenishmentConflict("DDMRP evaluation canonical ID mismatch.")
    if run["EvaluationFingerprint"] != canonical_fingerprint({
        key: value for key, value in run.items() if key != "EvaluationFingerprint"
    }):
        raise DdmrpReplenishmentConflict("DDMRP evaluation fingerprint mismatch.")


def _validate_evaluation_row_contract(row: Mapping[str, object]) -> None:
    _require_exact_fields(row, EVALUATION_ROW_FIELDS, context="DDMRP evaluation row")
    for values, fields, context in (
        (row["DemandComponents"], DEMAND_COMPONENT_FIELDS, "demand component"),
        (row["SupplyComponents"], SUPPLY_COMPONENT_FIELDS, "supply component"),
        (row["GateCodes"], GATE_FIELDS, "gate"),
    ):
        if not isinstance(values, list):
            raise DdmrpReplenishmentConflict(f"DDMRP {context}s must be a list.")
        for value in values:
            if not isinstance(value, Mapping):
                raise DdmrpReplenishmentConflict(f"DDMRP {context} must be a mapping.")
            _require_exact_fields(value, fields, context=f"DDMRP {context}")
            canonical_fingerprint(dict(value))
    expected_row_key = _canonical_json({
        "ItemID": row["ItemID"], "LocationID": row["LocationID"]
    })
    expected_id = canonical_stable_id("DER", {
        "EvaluationID": row["EvaluationID"], "RowKey": expected_row_key
    })
    if row["RowKey"] != expected_row_key or row["EvaluationRowID"] != expected_id:
        raise DdmrpReplenishmentConflict(
            "DDMRP evaluation row canonical identity mismatch."
        )
    if row["EvaluationRowFingerprint"] != canonical_fingerprint({
        key: value for key, value in row.items()
        if key != "EvaluationRowFingerprint"
    }):
        raise DdmrpReplenishmentConflict("DDMRP evaluation row fingerprint mismatch.")


def _validate_chain_record_contract(chain: Mapping[str, object]) -> None:
    _require_exact_fields(chain, REPLENISHMENT_CHAIN_FIELDS, context="DDMRP chain")
    identity = {
        "ItemID": chain["ItemID"],
        "LocationID": chain["LocationID"],
        "CycleNumber": chain["CycleNumber"],
    }
    if (
        chain["LogicalReplenishmentID"] != canonical_stable_id("DRL", identity)
        or chain["IdentityFingerprint"] != canonical_fingerprint(identity)
        or chain["ChainFingerprint"] != canonical_fingerprint({
            key: value for key, value in chain.items() if key != "ChainFingerprint"
        })
    ):
        raise DdmrpReplenishmentConflict("DDMRP chain immutable identity differs.")


def _validate_recommendation_record_contract(
    recommendation: Mapping[str, object],
) -> None:
    _require_exact_fields(
        recommendation, RECOMMENDATION_FIELDS, context="DDMRP recommendation"
    )
    version = recommendation["RecommendationVersion"]
    if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
        raise DdmrpReplenishmentConflict(
            "Recommendation version must be positive integer."
        )
    identity = {
        "LogicalReplenishmentID": recommendation["LogicalReplenishmentID"],
        "RecommendationVersion": version,
    }
    _validate_authority_signature_contract(
        recommendation["AuthoritySignature"],
        recommendation["AuthoritySignatureFingerprint"],
    )
    gates = recommendation["GateCodes"]
    if not isinstance(gates, list):
        raise DdmrpReplenishmentConflict(
            "DDMRP recommendation gates must be a list."
        )
    for gate in gates:
        if not isinstance(gate, Mapping):
            raise DdmrpReplenishmentConflict("DDMRP gate must be a mapping.")
        _require_exact_fields(gate, GATE_FIELDS, context="DDMRP gate")
        canonical_fingerprint(dict(gate))
    if (
        recommendation["RecommendationID"] != canonical_stable_id("DDR", identity)
        or recommendation["RecommendationFingerprint"] != canonical_fingerprint({
            key: value for key, value in recommendation.items()
            if key != "RecommendationFingerprint"
        })
    ):
        raise DdmrpReplenishmentConflict(
            "DDMRP recommendation immutable identity differs."
        )


def _validate_authority_signature_contract(
    signature: object,
    expected_fingerprint: object,
) -> None:
    if not isinstance(signature, Mapping):
        raise DdmrpReplenishmentConflict("DDMRP authority signature must be a mapping.")
    signature_fields = tuple(DdmrpAuthoritySignature.__dataclass_fields__)
    _require_exact_fields(
        signature, signature_fields, context="DDMRP authority signature"
    )
    signature_source = {
        key: value for key, value in signature.items()
        if key != "signature_fingerprint"
    }
    if (
        signature["signature_fingerprint"] != canonical_fingerprint(signature_source)
        or expected_fingerprint != signature["signature_fingerprint"]
    ):
        raise DdmrpReplenishmentConflict("DDMRP authority signature drift.")


def _evaluation_payload(
    *,
    evaluation_run: Mapping[str, object],
    evaluation_rows: Iterable[Mapping[str, object]],
    chain_records: Iterable[Mapping[str, object]],
    recommendations: Iterable[Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "EvaluationRun": deepcopy(dict(evaluation_run)),
        "EvaluationRows": sorted(
            (deepcopy(dict(row)) for row in evaluation_rows),
            key=lambda row: (row["ItemID"], row["LocationID"]),
        ),
        "ChainRecords": sorted(
            (deepcopy(dict(row)) for row in chain_records),
            key=lambda row: row["LogicalReplenishmentID"],
        ),
        "RecommendationVersions": sorted(
            (deepcopy(dict(row)) for row in recommendations),
            key=lambda row: row["RecommendationID"],
        ),
        "Events": sorted(
            (deepcopy(dict(row)) for row in events),
            key=lambda row: (
                row["AggregateType"], row["AggregateID"], row["AggregateVersion"]
            ),
        ),
    }


def _sorted_unique_ids(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(identifier, str) or not identifier for identifier in value
    ):
        raise DdmrpReplenishmentConflict(f"DDMRP {label} must be an ID list.")
    if value != sorted(set(value)):
        raise DdmrpReplenishmentConflict(
            f"DDMRP {label} must be sorted and unique."
        )
    return list(value)


def _replace_mapping(
    target: MutableMapping[str, dict[str, object]],
    source: Mapping[str, Mapping[str, object]],
) -> None:
    target.clear()
    target.update(deepcopy(dict(source)))


def _replace_sequence(
    target: MutableSequence[dict[str, object]],
    source: Iterable[Mapping[str, object]],
) -> None:
    target.clear()
    target.extend(deepcopy(tuple(source)))


def _validate_request_result(result: Mapping[str, object]) -> None:
    _require_exact_fields(result, REQUEST_RESULT_FIELDS, context="DDMRP request result")
    response = result["ResponseData"]
    if not isinstance(response, Mapping):
        raise DdmrpReplenishmentConflict("DDMRP response data must be a mapping.")
    _require_exact_fields(response, RESPONSE_DATA_FIELDS, context="DDMRP response data")
    if result["ResponseFingerprint"] != canonical_fingerprint(dict(response)):
        raise DdmrpReplenishmentConflict("DDMRP response fingerprint mismatch.")
    for field in (
        "EvaluationRowIDs", "LogicalReplenishmentIDs",
        "CreatedLogicalReplenishmentIDs", "ReusedLogicalReplenishmentIDs",
        "RecommendationIDs", "EventIDs",
    ):
        _sorted_unique_ids(result[field], field)
    created = result["CreatedLogicalReplenishmentIDs"]
    reused = result["ReusedLogicalReplenishmentIDs"]
    if set(created) & set(reused) or result["LogicalReplenishmentIDs"] != sorted(
        (*created, *reused)
    ):
        raise DdmrpReplenishmentConflict("DDMRP request result chain partition differs.")
    expected = canonical_fingerprint({
        key: value for key, value in result.items() if key != "RequestResultFingerprint"
    })
    if result["RequestResultFingerprint"] != expected:
        raise DdmrpReplenishmentConflict("DDMRP request result fingerprint mismatch.")


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
    except (TypeError, ValueError) as error:
        raise DdmrpReplenishmentConflict(
            "DDMRP authority input contains a non-canonical JSON value."
        ) from error


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
