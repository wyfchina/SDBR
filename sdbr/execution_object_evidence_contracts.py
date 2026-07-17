from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from sdbr.environment_paths import resolve_ddae_interface_contract_root


CONTRACT_ID = "SDBR-EXECUTION-OBJECT-EVIDENCE-V1"
CONTRACT_VERSION = "1.0.0"
CONSUMER_SYSTEM = "DDAE"
DEFAULT_CONTRACT_ROOT = resolve_ddae_interface_contract_root()

ACK_STATUSES = {"Accepted", "Duplicate", "Rejected", "DeadLettered"}
SOURCE_AUTHORITATIVE_STATUS = "SourceAuthoritative"
DEAD_LETTER_ERROR_CODES = {
    "UNKNOWN_WORK_ORDER",
    "UNKNOWN_OPERATION",
    "UNKNOWN_RESOURCE",
    "MISSING_PLANNING_RUN",
    "MISSING_FROZEN_CONFIG",
    "FROZEN_CONFIG_MISMATCH",
    "CONFLICTING_EVENT",
    "REVERSAL_TARGET_NOT_FOUND",
    "SUPERSESSION_TARGET_NOT_FOUND",
    "IDEMPOTENCY_CONFLICT",
}
REQUIRED_NON_CLAIMS = {
    "Reviewed fixture only",
    "Not source-authoritative production execution evidence",
    "Not production material issue evidence",
    "Not production material consumption evidence",
    "Not production inventory authority",
    "Not production quality authority",
    "Not automatic DDAE master-setting update",
    "Not ProductionValidated",
    "Not Business Golden Loop readiness",
}
GOVERNANCE_FORBIDDEN_FIELDS = {
    "AllowsAutomaticOperatingModelUpdate",
    "AllowsAutomaticMasterSettingUpdate",
    "AllowsAutomaticBufferUpdate",
    "AllowsAutomaticSupplierSourceFactUpdate",
    "AllowsAutomaticLeadTimeUpdate",
    "AllowsAutomaticMOQUpdate",
    "AllowsAutomaticOrderCycleUpdate",
}


@dataclass(frozen=True)
class ExecutionObjectReferenceResolver:
    work_order_ids: set[str] | None = None
    routing_ids: set[str] | None = None
    operation_ids: set[str] | None = None
    resource_ids: set[str] | None = None
    work_center_ids: set[str] | None = None
    product_ids: set[str] | None = None
    item_ids: set[str] | None = None
    location_ids: set[str] | None = None
    uoms: set[str] | None = None
    planning_run_ids: set[str] | None = None
    master_data_version_ids: set[str] | None = None
    operational_state_snapshot_ids: set[str] | None = None
    schedule_fingerprints: set[str] | None = None
    frozen_config_by_planning_run: dict[str, dict[str, str]] | None = None
    operation_sequences_by_routing: dict[str, dict[str, int]] | None = None
    inventory_quality_evidence_package_ids: set[str] | None = None
    issue_authority_reference_ids: set[str] | None = None
    consumption_authority_reference_ids: set[str] | None = None
    prior_started_work_order_ids: set[str] | None = None
    prior_started_operation_ids: set[str] | None = None
    correction_target_ids: set[str] | None = None
    supersession_target_package_ids: set[str] | None = None
    reversal_target_event_ids: set[str] | None = None


@dataclass(frozen=True)
class ExecutionObjectEvidenceProcessingResult:
    ack: dict[str, Any]
    inbound_ledger_record: dict[str, Any]
    accepted_evidence: dict[str, Any] | None


def contract_root() -> Path:
    return DEFAULT_CONTRACT_ROOT


def evidence_schema() -> dict[str, Any]:
    return _load_json(
        _contract_path(
            "sdbr-execution-object-evidence-v1",
            "schema",
            "sdbr-execution-object-evidence-v1.schema.json",
        )
    )


def ack_schema() -> dict[str, Any]:
    return _load_json(
        _contract_path(
            "sdbr-execution-object-evidence-v1",
            "schema",
            "sdbr-execution-object-ack-v1.schema.json",
        )
    )


def default_reviewed_fixture_resolver() -> ExecutionObjectReferenceResolver:
    return ExecutionObjectReferenceResolver(
        work_order_ids={"WO-SUB-AVIONICS-COMPUTE-001"},
        routing_ids={"SDBR-ROUTE-SUB-AVIONICS-COMPUTE-001"},
        operation_ids={"OP-INSTALL-FPGA-SPACE-001"},
        resource_ids={"RES-AVIONICS-BENCH-001"},
        work_center_ids={"WC-AVIONICS-ASSEMBLY"},
        product_ids={"SUB-AVIONICS-COMPUTE"},
        item_ids={"SUB-AVIONICS-COMPUTE", "PART-FPGA-SPACE"},
        location_ids={"ASSY-LINE-AVIONICS", "WH-ELEC-QA"},
        uoms={"EA"},
        planning_run_ids={"SDBR-PLAN-RUN-20260628-001"},
        master_data_version_ids={"MDV-SDBR-20260628-001"},
        operational_state_snapshot_ids={"OSS-SDBR-20260628-001"},
        schedule_fingerprints={"sha256:reviewed-fixture-schedule"},
        frozen_config_by_planning_run={
            "SDBR-PLAN-RUN-20260628-001": {
                "OperatingModelConfigurationID": "OMC-SAT-BUS-001-20260628-001",
                "OperatingModelFingerprint": "sha256:reviewed-fixture-operating-model",
                "SchedulingConfigurationID": "SCH-SAT-BUS-001-20260628-001",
                "DDMRPConfigurationID": "DDMRP-SAT-BUS-001-20260628-001",
            }
        },
        operation_sequences_by_routing={
            "SDBR-ROUTE-SUB-AVIONICS-COMPUTE-001": {
                "OP-INSTALL-FPGA-SPACE-001": 10,
            }
        },
        inventory_quality_evidence_package_ids={
            "PIQE-PART-FPGA-SPACE-WH-ELEC-QA-20260628-001"
        },
    )


def process_execution_object_evidence_message(
    message: Mapping[str, Any],
    *,
    received_at: datetime,
    existing_ledger_records: list[Mapping[str, Any]] | None = None,
    reference_resolver: ExecutionObjectReferenceResolver | None = None,
    allow_source_authoritative: bool = False,
) -> ExecutionObjectEvidenceProcessingResult:
    normalized = deepcopy(dict(message))
    idempotency_key = str(normalized.get("IdempotencyKey", ""))
    message_id = str(normalized.get("MessageID", ""))
    traceable_id = _traceable_id(normalized)
    fingerprint = canonical_payload_fingerprint(normalized)
    duplicate_record = _find_duplicate(
        existing_ledger_records or [],
        idempotency_key=idempotency_key,
    )
    if duplicate_record is not None:
        existing_fingerprint = str(duplicate_record.get("PayloadFingerprint", ""))
        if existing_fingerprint == fingerprint:
            ack = build_execution_object_ack(
                message_id=message_id,
                idempotency_key=idempotency_key,
                ack_status="Duplicate",
                received_at=received_at,
                traceable_id=traceable_id,
                error=None,
            )
            return _result(
                message=normalized,
                ack=ack,
                received_at=received_at,
                fingerprint=fingerprint,
                accepted_evidence=None,
                errors=[],
            )
        error = _ack_error(
            "IDEMPOTENCY_CONFLICT",
            "Same idempotency key was received with a different canonical payload.",
            retryable=False,
        )
        ack = build_execution_object_ack(
            message_id=message_id,
            idempotency_key=idempotency_key,
            ack_status="DeadLettered",
            received_at=received_at,
            traceable_id=traceable_id,
            error=error,
        )
        return _result(
            message=normalized,
            ack=ack,
            received_at=received_at,
            fingerprint=fingerprint,
            accepted_evidence=None,
            errors=[error],
        )

    errors = _schema_errors(normalized)
    if not errors:
        errors = _business_errors(
            normalized,
            reference_resolver=reference_resolver,
            allow_source_authoritative=allow_source_authoritative,
        )
    if errors:
        primary_error = errors[0]
        ack = build_execution_object_ack(
            message_id=message_id,
            idempotency_key=idempotency_key,
            ack_status=_status_for_errors(errors),
            received_at=received_at,
            traceable_id=traceable_id,
            error=primary_error,
        )
        return _result(
            message=normalized,
            ack=ack,
            received_at=received_at,
            fingerprint=fingerprint,
            accepted_evidence=None,
            errors=errors,
        )

    accepted_evidence = _accepted_evidence_record(
        normalized,
        source_authoritative_usable=_is_source_authoritative(normalized),
    )
    ack = build_execution_object_ack(
        message_id=message_id,
        idempotency_key=idempotency_key,
        ack_status="Accepted",
        received_at=received_at,
        traceable_id=traceable_id,
        error=None,
    )
    return _result(
        message=normalized,
        ack=ack,
        received_at=received_at,
        fingerprint=fingerprint,
        accepted_evidence=accepted_evidence,
        errors=[],
    )


def build_execution_object_ack(
    *,
    message_id: str,
    idempotency_key: str,
    ack_status: str,
    received_at: datetime,
    traceable_id: str,
    error: dict[str, Any] | None,
) -> dict[str, Any]:
    if ack_status not in ACK_STATUSES:
        raise ValueError(f"Unsupported ACK status: {ack_status}")
    ack = {
        "ContractID": CONTRACT_ID,
        "ContractVersion": CONTRACT_VERSION,
        "AckID": f"SDBR-EOE-ACK-{_safe_id(message_id)}-{ack_status}",
        "MessageID": message_id,
        "IdempotencyKey": idempotency_key,
        "ConsumerSystem": CONSUMER_SYSTEM,
        "AckStatus": ack_status,
        "ErrorCode": None if error is None else error["ErrorCode"],
        "ErrorMessage": None if error is None else error["ErrorMessage"],
        "ReceivedAt": received_at.isoformat(),
        "Retryable": False if error is None else bool(error.get("Retryable", False)),
        "TraceableID": traceable_id or "UNKNOWN",
    }
    validate_execution_object_ack(ack)
    return ack


def validate_execution_object_ack(ack: Mapping[str, Any]) -> None:
    Draft202012Validator(ack_schema()).validate(dict(ack))


def canonical_payload_fingerprint(message: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _jsonable(message),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _contract_path(*parts: str) -> Path:
    return contract_root().joinpath("contracts", *parts)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _schema_errors(message: Mapping[str, Any]) -> list[dict[str, Any]]:
    validator = Draft202012Validator(evidence_schema())
    errors = sorted(validator.iter_errors(dict(message)), key=lambda item: list(item.path))
    return [_schema_error_to_ack_error(error) for error in errors]


def _business_errors(
    message: Mapping[str, Any],
    *,
    reference_resolver: ExecutionObjectReferenceResolver | None,
    allow_source_authoritative: bool,
) -> list[dict[str, Any]]:
    payload = dict(message.get("Payload", {}))
    planning = _mapping(payload.get("PlanningContext"))
    work_order = _mapping(payload.get("WorkOrder"))
    routing = _mapping(payload.get("Routing"))
    operations = list(payload.get("Operations", []))
    material_requirements = list(payload.get("MaterialRequirements", []))
    material_issues = list(payload.get("MaterialIssues", []))
    material_consumptions = list(payload.get("MaterialConsumptions", []))
    governance = _mapping(payload.get("DDAEGovernanceBoundary"))
    supersession = _mapping(payload.get("Supersession"))
    errors: list[dict[str, Any]] = []

    if payload.get("EvidenceConfidence") == "ProductionValidatedReserved":
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "EvidenceConfidence ProductionValidatedReserved is reserved and cannot be accepted in V1 reviewed fixture handling.",
                retryable=False,
            )
        )
    if not allow_source_authoritative and (
        payload.get("EvidenceStatus") == SOURCE_AUTHORITATIVE_STATUS
        or payload.get("EvidenceConfidence") == SOURCE_AUTHORITATIVE_STATUS
    ):
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "This implementation only accepts reviewed fixture/control evidence, not source-authoritative production execution.",
                retryable=False,
            )
        )

    missing_non_claims = sorted(REQUIRED_NON_CLAIMS - set(payload.get("NonClaims", [])))
    if missing_non_claims:
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "Missing required non-claims: " + ", ".join(missing_non_claims),
                retryable=False,
            )
        )

    for field in GOVERNANCE_FORBIDDEN_FIELDS:
        if governance.get(field) is not False:
            errors.append(
                _ack_error(
                    "GOVERNANCE_AUTO_UPDATE_FORBIDDEN",
                    f"{field} must be false; execution evidence cannot update DDAE governance settings.",
                    retryable=False,
                )
            )
            break
    if governance.get("RequiresSeparateDDAEApproval") is not True:
        errors.append(
            _ack_error(
                "GOVERNANCE_AUTO_UPDATE_FORBIDDEN",
                "RequiresSeparateDDAEApproval must be true.",
                retryable=False,
            )
        )

    if routing.get("RoutingAuthority") != "SDBR_EXECUTABLE_ROUTING":
        errors.append(
            _ack_error(
                "UNKNOWN_ROUTING",
                "DDAE routing, control point, resource routing, or capacity resource semantics cannot be executable SDBR routing proof.",
                retryable=False,
            )
        )

    if reference_resolver is not None:
        _append_reference_errors(errors, planning, work_order, routing, operations, material_requirements, material_issues, material_consumptions, reference_resolver)
        _append_frozen_config_errors(errors, planning, reference_resolver)
        _append_operation_sequence_errors(errors, routing, operations, reference_resolver)

    _append_quantity_errors(errors, work_order, material_requirements, material_issues, material_consumptions)
    _append_late_capture_errors(errors, work_order, operations, reference_resolver)
    _append_material_boundary_errors(errors, material_issues, material_consumptions, reference_resolver)
    _append_supersession_errors(errors, supersession, reference_resolver)
    return errors


def _append_reference_errors(
    errors: list[dict[str, Any]],
    planning: Mapping[str, Any],
    work_order: Mapping[str, Any],
    routing: Mapping[str, Any],
    operations: list[Any],
    material_requirements: list[Any],
    material_issues: list[Any],
    material_consumptions: list[Any],
    resolver: ExecutionObjectReferenceResolver,
) -> None:
    _append_reference_error(errors, resolver.planning_run_ids, planning.get("PlanningRunID"), "MISSING_PLANNING_RUN", "PlanningRunID cannot be resolved.")
    for key in (
        "OperatingModelConfigurationID",
        "OperatingModelFingerprint",
        "SchedulingConfigurationID",
        "DDMRPConfigurationID",
    ):
        if not planning.get(key):
            errors.append(_ack_error("MISSING_FROZEN_CONFIG", f"{key} is required.", retryable=False))
    _append_reference_error(errors, resolver.master_data_version_ids, planning.get("MasterDataVersionID"), "MISSING_FROZEN_CONFIG", "MasterDataVersionID cannot be resolved.")
    _append_reference_error(errors, resolver.operational_state_snapshot_ids, planning.get("OperationalStateSnapshotID"), "MISSING_FROZEN_CONFIG", "OperationalStateSnapshotID cannot be resolved.")
    _append_reference_error(errors, resolver.schedule_fingerprints, planning.get("ScheduleFingerprint"), "FROZEN_CONFIG_MISMATCH", "ScheduleFingerprint cannot be resolved.")
    _append_reference_error(errors, resolver.work_order_ids, work_order.get("WorkOrderID"), "UNKNOWN_WORK_ORDER", "WorkOrderID cannot be resolved.")
    _append_reference_error(errors, resolver.product_ids, work_order.get("ProductID"), "UNKNOWN_WORK_ORDER", "ProductID cannot be resolved under the work order context.")
    _append_reference_error(errors, resolver.item_ids, work_order.get("ItemID"), "UNKNOWN_WORK_ORDER", "Work order ItemID cannot be resolved.")
    _append_reference_error(errors, resolver.location_ids, work_order.get("LocationID"), "UNKNOWN_WORK_ORDER", "Work order LocationID cannot be resolved.")
    _append_reference_error(errors, resolver.uoms, work_order.get("QuantityUOM"), "UNSUPPORTED_UOM", "Work order QuantityUOM cannot be resolved.")
    _append_reference_error(errors, resolver.routing_ids, routing.get("RoutingID"), "UNKNOWN_ROUTING", "RoutingID cannot be resolved as an SDBR executable routing.")
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        _append_reference_error(errors, resolver.operation_ids, operation.get("OperationID"), "UNKNOWN_OPERATION", "OperationID cannot be resolved.")
        _append_reference_error(errors, resolver.resource_ids, operation.get("ResourceID"), "UNKNOWN_RESOURCE", "ResourceID cannot be resolved.")
        _append_reference_error(errors, resolver.work_center_ids, operation.get("WorkCenterID"), "UNKNOWN_RESOURCE", "WorkCenterID cannot be resolved.")
    for requirement in material_requirements:
        if not isinstance(requirement, Mapping):
            continue
        _append_reference_error(errors, resolver.item_ids, requirement.get("ConsumedItemID"), "UNKNOWN_OPERATION", "Material requirement item cannot be resolved.")
        _append_reference_error(errors, resolver.location_ids, requirement.get("ConsumedLocationID"), "UNKNOWN_OPERATION", "Material requirement location cannot be resolved.")
        _append_reference_error(errors, resolver.uoms, requirement.get("QuantityUOM"), "UNSUPPORTED_UOM", "Material requirement UOM cannot be resolved.")
    for issue in material_issues:
        if not isinstance(issue, Mapping):
            continue
        _append_reference_error(errors, resolver.item_ids, issue.get("ConsumedItemID"), "UNKNOWN_OPERATION", "Material issue item cannot be resolved.")
        _append_reference_error(errors, resolver.location_ids, issue.get("IssueLocationID"), "UNKNOWN_OPERATION", "Material issue location cannot be resolved.")
        _append_reference_error(errors, resolver.uoms, issue.get("QuantityUOM"), "UNSUPPORTED_UOM", "Material issue UOM cannot be resolved.")
    for consumption in material_consumptions:
        if not isinstance(consumption, Mapping):
            continue
        _append_reference_error(errors, resolver.operation_ids, consumption.get("ConsumedByOperationID"), "UNKNOWN_OPERATION", "Material consumption operation cannot be resolved.")
        _append_reference_error(errors, resolver.item_ids, consumption.get("ConsumedItemID"), "UNKNOWN_OPERATION", "Material consumption item cannot be resolved.")
        _append_reference_error(errors, resolver.location_ids, consumption.get("ConsumedLocationID"), "UNKNOWN_OPERATION", "Material consumption location cannot be resolved.")
        _append_reference_error(errors, resolver.uoms, consumption.get("QuantityUOM"), "UNSUPPORTED_UOM", "Material consumption UOM cannot be resolved.")


def _append_frozen_config_errors(
    errors: list[dict[str, Any]],
    planning: Mapping[str, Any],
    resolver: ExecutionObjectReferenceResolver,
) -> None:
    if resolver.frozen_config_by_planning_run is None:
        return
    planning_run_id = str(planning.get("PlanningRunID", ""))
    expected = resolver.frozen_config_by_planning_run.get(planning_run_id)
    if expected is None:
        errors.append(
            _ack_error(
                "MISSING_FROZEN_CONFIG",
                "Planning Run has no resolvable frozen DDS&OP configuration context.",
                retryable=False,
            )
        )
        return
    for key, expected_value in expected.items():
        if str(planning.get(key, "")) != expected_value:
            errors.append(
                _ack_error(
                    "FROZEN_CONFIG_MISMATCH",
                    f"{key} does not match the frozen Planning Run configuration.",
                    retryable=False,
                )
            )
            return


def _append_operation_sequence_errors(
    errors: list[dict[str, Any]],
    routing: Mapping[str, Any],
    operations: list[Any],
    resolver: ExecutionObjectReferenceResolver,
) -> None:
    if resolver.operation_sequences_by_routing is None:
        return
    expected_by_operation = resolver.operation_sequences_by_routing.get(
        str(routing.get("RoutingID", ""))
    )
    if expected_by_operation is None:
        return
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        operation_id = str(operation.get("OperationID", ""))
        expected_sequence = expected_by_operation.get(operation_id)
        if expected_sequence is not None and operation.get("OperationSequence") != expected_sequence:
            errors.append(
                _ack_error(
                    "OPERATION_SEQUENCE_INVALID",
                    "OperationSequence does not match the executable routing.",
                    retryable=False,
                )
            )


def _append_quantity_errors(
    errors: list[dict[str, Any]],
    work_order: Mapping[str, Any],
    material_requirements: list[Any],
    material_issues: list[Any],
    material_consumptions: list[Any],
) -> None:
    required = _number(work_order.get("RequiredQty"))
    completed = _number(work_order.get("CompletedQty"))
    remaining = _number(work_order.get("RemainingQty"))
    scrap = _number(work_order.get("ScrapQty"))
    reject = _number(work_order.get("RejectQty"))
    if None not in (required, completed, remaining, scrap, reject):
        if completed + remaining + scrap + reject > required + 0.000001:
            errors.append(
                _ack_error(
                    "INVALID_QUANTITY",
                    "Work order quantities are internally inconsistent.",
                    retryable=False,
                )
            )
    for collection, field in (
        (material_requirements, "RequiredQty"),
        (material_issues, "IssuedQty"),
        (material_consumptions, "ConsumedQty"),
    ):
        for item in collection:
            if isinstance(item, Mapping) and _number(item.get(field)) is None:
                errors.append(
                    _ack_error("INVALID_QUANTITY", f"{field} must be numeric.", retryable=False)
                )


def _append_late_capture_errors(
    errors: list[dict[str, Any]],
    work_order: Mapping[str, Any],
    operations: list[Any],
    resolver: ExecutionObjectReferenceResolver | None,
) -> None:
    if work_order.get("WorkOrderStatus") == "Completed":
        work_order_id = str(work_order.get("WorkOrderID", ""))
        prior_known = (
            resolver is not None
            and resolver.prior_started_work_order_ids is not None
            and work_order_id in resolver.prior_started_work_order_ids
        )
        if not prior_known:
            _append_capture_reconciliation_error(errors, work_order, "work order")
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        if operation.get("OperationStatus") == "Completed":
            operation_id = str(operation.get("OperationID", ""))
            prior_known = (
                resolver is not None
                and resolver.prior_started_operation_ids is not None
                and operation_id in resolver.prior_started_operation_ids
            )
            if not prior_known and operation.get("ActualOperationStartAt") is None:
                _append_capture_reconciliation_error(errors, operation, "operation")


def _append_capture_reconciliation_error(
    errors: list[dict[str, Any]],
    record: Mapping[str, Any],
    label: str,
) -> None:
    if record.get("EventCaptureMode") != "LateCaptured":
        errors.append(
            _ack_error(
                "EVENT_ORDER_INVALID",
                f"Completed {label} without prior start evidence must be late-captured and reconciled.",
                retryable=False,
            )
        )
        return
    required = (
        "LateCaptureReason",
        "ReconciliationReferenceID",
        "ObservedAt",
        "RecordedAt",
    )
    if any(record.get(field) in (None, "") for field in required):
        errors.append(
            _ack_error(
                "EVENT_ORDER_INVALID",
                f"Late-captured {label} is missing reconciliation fields.",
                retryable=False,
            )
        )
        return
    observed = _parse_datetime(record.get("ObservedAt"))
    recorded = _parse_datetime(record.get("RecordedAt"))
    if observed is None or recorded is None or observed > recorded:
        errors.append(
            _ack_error(
                "EVENT_ORDER_INVALID",
                f"Late-captured {label} has incoherent observed/recorded timestamps.",
                retryable=False,
            )
        )


def _append_material_boundary_errors(
    errors: list[dict[str, Any]],
    material_issues: list[Any],
    material_consumptions: list[Any],
    resolver: ExecutionObjectReferenceResolver | None,
) -> None:
    for issue in material_issues:
        if not isinstance(issue, Mapping):
            continue
        package_id = issue.get("InventoryQualityEvidencePackageID")
        authority_id = issue.get("IssueAuthorityReferenceID")
        if not package_id and not authority_id:
            errors.append(
                _ack_error(
                    "MISSING_INVENTORY_QUALITY_EVIDENCE",
                    "Material issue claims require a direct inventory/quality evidence package or accepted issue authority reference.",
                    retryable=False,
                )
            )
            continue
        _append_optional_reference_error(errors, resolver.inventory_quality_evidence_package_ids if resolver else None, package_id, "MISSING_INVENTORY_QUALITY_EVIDENCE", "Inventory/quality package for material issue cannot be resolved.")
        _append_optional_reference_error(errors, resolver.issue_authority_reference_ids if resolver else None, authority_id, "MISSING_INVENTORY_QUALITY_EVIDENCE", "Issue authority reference cannot be resolved.")
    for consumption in material_consumptions:
        if not isinstance(consumption, Mapping):
            continue
        package_id = consumption.get("InventoryQualityEvidencePackageID")
        authority_id = consumption.get("ConsumptionAuthorityReferenceID")
        if not package_id and not authority_id:
            errors.append(
                _ack_error(
                    "MISSING_INVENTORY_QUALITY_EVIDENCE",
                    "Material consumption claims require a direct inventory/quality evidence package or accepted consumption authority reference.",
                    retryable=False,
                )
            )
            continue
        _append_optional_reference_error(errors, resolver.inventory_quality_evidence_package_ids if resolver else None, package_id, "MISSING_INVENTORY_QUALITY_EVIDENCE", "Inventory/quality package for material consumption cannot be resolved.")
        _append_optional_reference_error(errors, resolver.consumption_authority_reference_ids if resolver else None, authority_id, "MISSING_INVENTORY_QUALITY_EVIDENCE", "Consumption authority reference cannot be resolved.")


def _append_supersession_errors(
    errors: list[dict[str, Any]],
    supersession: Mapping[str, Any],
    resolver: ExecutionObjectReferenceResolver | None,
) -> None:
    correction_id = supersession.get("CorrectsExecutionEventID")
    supersedes_id = supersession.get("SupersedesEvidencePackageID")
    reversal_id = supersession.get("ReversesExecutionEventID")
    if supersession.get("CorrectionReason") and not correction_id and not supersedes_id:
        errors.append(
            _ack_error(
                "SUPERSESSION_TARGET_NOT_FOUND",
                "Correction requires a predecessor execution event or evidence package.",
                retryable=False,
            )
        )
    if supersedes_id:
        _append_optional_reference_error(errors, resolver.supersession_target_package_ids if resolver else None, supersedes_id, "SUPERSESSION_TARGET_NOT_FOUND", "Supersession target package cannot be resolved.")
    if supersession.get("ReversalReason") and not reversal_id:
        errors.append(
            _ack_error(
                "REVERSAL_TARGET_NOT_FOUND",
                "Reversal requires a predecessor execution event.",
                retryable=False,
            )
        )
    if reversal_id:
        _append_optional_reference_error(errors, resolver.reversal_target_event_ids if resolver else None, reversal_id, "REVERSAL_TARGET_NOT_FOUND", "Reversal target event cannot be resolved.")


def _append_reference_error(
    errors: list[dict[str, Any]],
    known_ids: set[str] | None,
    value: Any,
    error_code: str,
    message: str,
) -> None:
    if known_ids is None:
        return
    if value is None or str(value) not in known_ids:
        errors.append(_ack_error(error_code, message, retryable=False))


def _append_optional_reference_error(
    errors: list[dict[str, Any]],
    known_ids: set[str] | None,
    value: Any,
    error_code: str,
    message: str,
) -> None:
    if known_ids is None or value is None:
        return
    if str(value) not in known_ids:
        errors.append(_ack_error(error_code, message, retryable=False))


def _schema_error_to_ack_error(error) -> dict[str, Any]:
    path = ".".join(str(item) for item in error.absolute_path)
    message = str(error.message)
    if error.validator == "required" and "'WorkOrderID'" in message:
        code = "MISSING_WORK_ORDER"
    elif error.validator == "required" and "'PlanningRunID'" in message:
        code = "MISSING_PLANNING_RUN"
    elif path.endswith("WorkOrder.WorkOrderID"):
        code = "MISSING_WORK_ORDER"
    elif "RoutingAuthority" in path or "Routing" in path and error.validator == "const":
        code = "UNKNOWN_ROUTING"
        message = "DDAE PrimaryRoutingID, NetworkRoutingLine, ResourceRouting, CapacityResource, or ControlPointID cannot be used as SDBR executable routing evidence."
    elif "Routing" in path:
        code = "UNKNOWN_ROUTING"
    elif "Operation" in path:
        code = "UNKNOWN_OPERATION"
    elif "ResourceID" in path or "WorkCenterID" in path:
        code = "UNKNOWN_RESOURCE"
    elif "PlanningRunID" in path:
        code = "MISSING_PLANNING_RUN"
    elif (
        "OperatingModelConfigurationID" in path
        or "OperatingModelFingerprint" in path
        or "SchedulingConfigurationID" in path
        or "DDMRPConfigurationID" in path
        or "MasterDataVersionID" in path
        or "OperationalStateSnapshotID" in path
    ):
        code = "MISSING_FROZEN_CONFIG"
    elif "ScheduleFingerprint" in path:
        code = "FROZEN_CONFIG_MISMATCH"
    elif "UOM" in path:
        code = "UNSUPPORTED_UOM"
    elif "Qty" in path or "quantity" in message.lower() or error.validator == "minimum":
        code = "INVALID_QUANTITY"
    elif path.endswith("At") or "date-time" in message:
        code = "INVALID_TIMESTAMP"
    elif any(field in path for field in GOVERNANCE_FORBIDDEN_FIELDS):
        code = "GOVERNANCE_AUTO_UPDATE_FORBIDDEN"
    else:
        code = "CONTRACT_SCOPE_VIOLATION"
    return _ack_error(code, message, retryable=False)


def _ack_error(code: str, message: str, *, retryable: bool) -> dict[str, Any]:
    return {"ErrorCode": code, "ErrorMessage": message, "Retryable": retryable}


def _status_for_errors(errors: list[dict[str, Any]]) -> str:
    first_code = str(errors[0].get("ErrorCode", ""))
    first_message = str(errors[0].get("ErrorMessage", ""))
    if first_code == "MISSING_PLANNING_RUN" and "required property" in first_message:
        return "Rejected"
    return "DeadLettered" if first_code in DEAD_LETTER_ERROR_CODES else "Rejected"


def _accepted_evidence_record(
    message: Mapping[str, Any],
    *,
    source_authoritative_usable: bool,
) -> dict[str, Any]:
    payload = dict(message["Payload"])
    planning = dict(payload["PlanningContext"])
    work_order = dict(payload["WorkOrder"])
    routing = dict(payload["Routing"])
    return {
        "EvidencePackageID": str(payload["EvidencePackageID"]),
        "EvidenceVersion": str(payload["EvidenceVersion"]),
        "EvidenceStatus": str(payload["EvidenceStatus"]),
        "EvidenceConfidence": str(payload["EvidenceConfidence"]),
        "PlanningContext": {
            "PlanningRunID": planning["PlanningRunID"],
            "OperatingModelConfigurationID": planning["OperatingModelConfigurationID"],
            "OperatingModelFingerprint": planning["OperatingModelFingerprint"],
            "SchedulingConfigurationID": planning["SchedulingConfigurationID"],
            "DDMRPConfigurationID": planning["DDMRPConfigurationID"],
            "MasterDataVersionID": planning["MasterDataVersionID"],
            "ScheduleFingerprint": planning["ScheduleFingerprint"],
        },
        "WorkOrderID": work_order["WorkOrderID"],
        "ProductID": work_order["ProductID"],
        "ItemID": work_order["ItemID"],
        "LocationID": work_order["LocationID"],
        "RoutingID": routing["RoutingID"],
        "OperationIDs": [
            str(operation["OperationID"])
            for operation in payload.get("Operations", [])
            if isinstance(operation, Mapping)
        ],
        "MaterialRequirementIDs": [
            str(requirement["MaterialRequirementID"])
            for requirement in payload.get("MaterialRequirements", [])
            if isinstance(requirement, Mapping)
        ],
        "MaterialIssueCount": len(payload.get("MaterialIssues", [])),
        "MaterialConsumptionCount": len(payload.get("MaterialConsumptions", [])),
        "SourceAuthoritativeUsable": bool(source_authoritative_usable),
        "NonClaims": list(payload.get("NonClaims", [])),
    }


def _result(
    *,
    message: Mapping[str, Any],
    ack: dict[str, Any],
    received_at: datetime,
    fingerprint: str,
    accepted_evidence: dict[str, Any] | None,
    errors: list[dict[str, Any]],
) -> ExecutionObjectEvidenceProcessingResult:
    payload = message.get("Payload", {})
    evidence_version = (
        str(payload.get("EvidenceVersion", "")) if isinstance(payload, Mapping) else ""
    )
    evidence_package_id = (
        str(payload.get("EvidencePackageID", "UNKNOWN"))
        if isinstance(payload, Mapping)
        else "UNKNOWN"
    )
    record = {
        "ContractID": CONTRACT_ID,
        "MessageID": str(message.get("MessageID", "")),
        "IdempotencyKey": str(message.get("IdempotencyKey", "")),
        "EvidencePackageID": evidence_package_id,
        "EvidenceVersion": evidence_version,
        "ReceivedAt": received_at.isoformat(),
        "Ack": deepcopy(ack),
        "AckStatus": ack["AckStatus"],
        "PayloadFingerprint": fingerprint,
        "Payload": deepcopy(dict(message)),
        "AcceptedEvidence": deepcopy(accepted_evidence),
        "DeadLettered": ack["AckStatus"] == "DeadLettered",
        "Errors": deepcopy(errors),
    }
    return ExecutionObjectEvidenceProcessingResult(
        ack=ack,
        inbound_ledger_record=record,
        accepted_evidence=accepted_evidence,
    )


def _find_duplicate(
    records: list[Mapping[str, Any]],
    *,
    idempotency_key: str,
) -> Mapping[str, Any] | None:
    for record in records:
        if str(record.get("IdempotencyKey", "")) == idempotency_key:
            return record
    return None


def _traceable_id(message: Mapping[str, Any]) -> str:
    payload = message.get("Payload", {})
    if isinstance(payload, Mapping):
        traceability = payload.get("Traceability", {})
        if isinstance(traceability, Mapping) and traceability.get("TraceableID"):
            return str(traceability["TraceableID"])
    return "UNKNOWN"


def _is_source_authoritative(message: Mapping[str, Any]) -> bool:
    payload = message.get("Payload", {})
    if not isinstance(payload, Mapping):
        return False
    return (
        payload.get("EvidenceStatus") == SOURCE_AUTHORITATIVE_STATUS
        and payload.get("EvidenceConfidence") == SOURCE_AUTHORITATIVE_STATUS
    )


def _safe_id(value: str) -> str:
    allowed = [ch if ch.isalnum() else "-" for ch in value]
    return "".join(allowed).strip("-") or "UNKNOWN"


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
