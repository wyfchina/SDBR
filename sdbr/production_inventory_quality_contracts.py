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


CONTRACT_ID = "PRODUCTION-INVENTORY-QUALITY-EVIDENCE-V1"
CONTRACT_VERSION = "1.0.0"
CONSUMER_SYSTEM = "SDBR"
DEFAULT_CONTRACT_ROOT = resolve_ddae_interface_contract_root()

ACK_STATUSES = {"Accepted", "Rejected", "Duplicate", "DeadLettered"}
SOURCE_AUTHORITATIVE_STATUS = "SourceAuthoritative"
DEAD_LETTER_ERROR_CODES = {
    "UNKNOWN_ITEM",
    "UNKNOWN_LOCATION",
    "UNKNOWN_LOT_OR_SERIAL",
    "CONFLICTING_MOVEMENT",
    "MOVEMENT_REVERSAL_TARGET_NOT_FOUND",
    "SUPERSESSION_TARGET_NOT_FOUND",
    "IDEMPOTENCY_CONFLICT",
}
REQUIRED_NON_CLAIMS = {
    "NotProductionValidated",
    "NotSupplierSourceApproval",
    "NotSupplierExecutionProof",
    "NotDeliveryPerformanceProof",
    "NotLeadTimePerformanceProof",
    "NotWorkOrderRoutingOperationProof",
    "NotMaterialConsumptionProof",
    "NoAutomaticDDAEMasterSettingUpdate",
    "NotBusinessGoldenLoopReady",
}


@dataclass(frozen=True)
class InventoryQualityReferenceResolver:
    item_ids: set[str] | None = None
    location_ids: set[str] | None = None
    lot_ids: set[str] | None = None
    serial_ids: set[str] | None = None
    program_ids: set[str] | None = None
    uoms: set[str] | None = None
    inventory_authority_ids: set[str] | None = None
    quality_authority_ids: set[str] | None = None
    snapshot_ids: set[str] | None = None
    movement_ids: set[str] | None = None
    quality_release_ids: set[str] | None = None
    evidence_package_ids: set[str] | None = None
    stale_snapshot_ids: set[str] | None = None
    conflicting_movement_ids: set[str] | None = None


@dataclass(frozen=True)
class InventoryQualityProcessingResult:
    ack: dict[str, Any]
    inbound_ledger_record: dict[str, Any]
    accepted_evidence: dict[str, Any] | None


def contract_root() -> Path:
    return DEFAULT_CONTRACT_ROOT


def message_schema() -> dict[str, Any]:
    return _load_json(
        _contract_path(
            "production-inventory-quality-evidence-v1",
            "schema",
            "production-inventory-quality-evidence-v1.schema.json",
        )
    )


def ack_schema() -> dict[str, Any]:
    return _load_json(
        _contract_path(
            "production-inventory-quality-evidence-v1",
            "schema",
            "production-inventory-quality-ack-v1.schema.json",
        )
    )


def process_inventory_quality_evidence_message(
    message: Mapping[str, Any],
    *,
    received_at: datetime,
    existing_ledger_records: list[Mapping[str, Any]] | None = None,
    reference_resolver: InventoryQualityReferenceResolver | None = None,
    require_source_authoritative: bool = False,
) -> InventoryQualityProcessingResult:
    normalized = deepcopy(dict(message))
    idempotency_key = str(normalized.get("IdempotencyKey", ""))
    message_id = str(normalized.get("MessageID", ""))
    evidence_package_id = _evidence_package_id(normalized)
    fingerprint = canonical_payload_fingerprint(normalized)
    duplicate_record = _find_duplicate(
        existing_ledger_records or [],
        idempotency_key=idempotency_key,
    )
    if duplicate_record is not None:
        existing_fingerprint = str(duplicate_record.get("PayloadFingerprint", ""))
        if existing_fingerprint == fingerprint:
            ack = build_inventory_quality_ack(
                message_id=message_id,
                evidence_package_id=evidence_package_id,
                ack_status="Duplicate",
                ack_at=received_at,
                errors=[],
            )
            return _result(
                message=normalized,
                ack=ack,
                received_at=received_at,
                fingerprint=fingerprint,
                accepted_evidence=None,
            )
        errors = [
            _ack_error(
                "IDEMPOTENCY_CONFLICT",
                "The same IdempotencyKey was received with different payload content.",
                retryable=False,
            )
        ]
        ack = build_inventory_quality_ack(
            message_id=message_id,
            evidence_package_id=evidence_package_id,
            ack_status="DeadLettered",
            ack_at=received_at,
            errors=errors,
        )
        return _result(
            message=normalized,
            ack=ack,
            received_at=received_at,
            fingerprint=fingerprint,
            accepted_evidence=None,
        )

    errors = _schema_errors(normalized)
    if not errors:
        errors = _business_errors(
            normalized,
            reference_resolver=reference_resolver,
            require_source_authoritative=require_source_authoritative,
        )
    if errors:
        ack = build_inventory_quality_ack(
            message_id=message_id,
            evidence_package_id=evidence_package_id,
            ack_status=_status_for_errors(errors),
            ack_at=received_at,
            errors=errors,
        )
        return _result(
            message=normalized,
            ack=ack,
            received_at=received_at,
            fingerprint=fingerprint,
            accepted_evidence=None,
        )

    accepted_evidence = _accepted_evidence_record(
        normalized,
        source_authoritative_usable=_is_source_authoritative(normalized),
    )
    ack = build_inventory_quality_ack(
        message_id=message_id,
        evidence_package_id=evidence_package_id,
        ack_status="Accepted",
        ack_at=received_at,
        errors=[],
    )
    return _result(
        message=normalized,
        ack=ack,
        received_at=received_at,
        fingerprint=fingerprint,
        accepted_evidence=accepted_evidence,
    )


def build_inventory_quality_ack(
    *,
    message_id: str,
    evidence_package_id: str,
    ack_status: str,
    ack_at: datetime,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    if ack_status not in ACK_STATUSES:
        raise ValueError(f"Unsupported ACK status: {ack_status}")
    ack = {
        "ContractID": CONTRACT_ID,
        "ContractVersion": CONTRACT_VERSION,
        "AckID": f"PIQEV1-ACK-SDBR-{_safe_id(message_id)}-{ack_status}",
        "MessageID": message_id,
        "EvidencePackageID": evidence_package_id,
        "ConsumerSystem": CONSUMER_SYSTEM,
        "AckStatus": ack_status,
        "AckAt": ack_at.isoformat(),
        "Errors": errors,
    }
    validate_inventory_quality_ack(ack)
    return ack


def validate_inventory_quality_ack(ack: Mapping[str, Any]) -> None:
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
    validator = Draft202012Validator(message_schema())
    errors = sorted(validator.iter_errors(dict(message)), key=lambda item: list(item.path))
    return [_schema_error_to_ack_error(error) for error in errors]


def _business_errors(
    message: Mapping[str, Any],
    *,
    reference_resolver: InventoryQualityReferenceResolver | None,
    require_source_authoritative: bool,
) -> list[dict[str, Any]]:
    payload = dict(message.get("Payload", {}))
    item_location = dict(payload.get("ItemLocation", {}))
    inventory_snapshot = payload.get("InventorySnapshot")
    stock_movements = list(payload.get("StockMovements", []))
    quality_evidence = payload.get("QualityEvidence")
    governance = dict(payload.get("DDAEGovernanceBoundary", {}))
    traceability = dict(payload.get("Traceability", {}))
    supersession = dict(payload.get("Supersession", {}))
    errors: list[dict[str, Any]] = []

    _append_datetime_errors(
        errors,
        _datetime_values(message, payload, inventory_snapshot, stock_movements, quality_evidence, traceability),
    )
    _append_authority_errors(errors, payload, inventory_snapshot, stock_movements, quality_evidence)
    _append_quantity_errors(errors, inventory_snapshot, stock_movements)
    _append_state_transition_errors(errors, stock_movements)
    _append_reversal_errors(errors, stock_movements, reference_resolver)
    _append_supersession_errors(errors, supersession, reference_resolver)
    if governance.get("AllowsAutomaticMasterSettingUpdate") is not False:
        errors.append(
            _ack_error(
                "GOVERNANCE_AUTO_UPDATE_FORBIDDEN",
                "Inventory/quality evidence cannot automatically update DDAE master settings.",
                retryable=False,
            )
        )
    if governance.get("RequiresSeparateDDAEApproval") is not True:
        errors.append(
            _ack_error(
                "GOVERNANCE_AUTO_UPDATE_FORBIDDEN",
                "Inventory/quality evidence must require separate DDAE approval.",
                retryable=False,
            )
        )
    if payload.get("EvidenceConfidence") == "ProductionValidatedReserved":
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "ProductionValidatedReserved cannot be interpreted as an active V1 production-validation claim.",
                retryable=False,
            )
        )
    if require_source_authoritative and not _is_source_authoritative(message):
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "Only SourceAuthoritative evidence can be consumed as production inventory or quality proof.",
                retryable=False,
            )
        )
    non_claims = {str(item) for item in payload.get("NonClaims", [])}
    missing_non_claims = REQUIRED_NON_CLAIMS - non_claims
    if missing_non_claims:
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "Required non-claims are missing: "
                + ", ".join(sorted(missing_non_claims)),
                retryable=False,
            )
        )
    resolver = reference_resolver
    if resolver is not None:
        _append_reference_error(
            errors,
            resolver.item_ids,
            item_location.get("ItemID"),
            "UNKNOWN_ITEM",
            "Item cannot be resolved.",
        )
        _append_reference_error(
            errors,
            resolver.location_ids,
            item_location.get("LocationID"),
            "UNKNOWN_LOCATION",
            "Location cannot be resolved.",
        )
        _append_optional_reference_error(
            errors,
            resolver.lot_ids,
            item_location.get("LotID"),
            "UNKNOWN_LOT_OR_SERIAL",
            "Lot cannot be resolved.",
        )
        _append_optional_reference_error(
            errors,
            resolver.serial_ids,
            item_location.get("SerialID"),
            "UNKNOWN_LOT_OR_SERIAL",
            "Serial cannot be resolved.",
        )
        _append_optional_reference_error(
            errors,
            resolver.program_ids,
            item_location.get("ProgramID"),
            "CONTRACT_SCOPE_VIOLATION",
            "Program cannot be resolved.",
        )
        _append_reference_error(
            errors,
            resolver.uoms,
            item_location.get("QuantityUOM"),
            "UNSUPPORTED_UOM",
            "UOM cannot be resolved.",
        )
        _append_authority_reference_errors(errors, payload, resolver)
        _append_snapshot_reference_errors(errors, inventory_snapshot, resolver)
        _append_movement_reference_errors(errors, stock_movements, resolver)
        _append_quality_release_reference_errors(errors, quality_evidence, resolver)
    return errors


def _datetime_values(
    message: Mapping[str, Any],
    payload: Mapping[str, Any],
    inventory_snapshot: object,
    stock_movements: list[Any],
    quality_evidence: object,
    traceability: Mapping[str, Any],
) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = [
        ("OccurredAt", message.get("OccurredAt")),
        ("Payload.Traceability.RegisteredAt", traceability.get("RegisteredAt")),
    ]
    if isinstance(inventory_snapshot, Mapping):
        values.append(("Payload.InventorySnapshot.SnapshotTimestamp", inventory_snapshot.get("SnapshotTimestamp")))
    for index, movement in enumerate(stock_movements):
        if isinstance(movement, Mapping):
            values.append((f"Payload.StockMovements[{index}].MovementTimestamp", movement.get("MovementTimestamp")))
    if isinstance(quality_evidence, Mapping):
        values.extend(
            [
                ("Payload.QualityEvidence.QualityReleasedAt", quality_evidence.get("QualityReleasedAt")),
                ("Payload.QualityEvidence.RejectedAt", quality_evidence.get("RejectedAt")),
            ]
        )
    return values


def _append_datetime_errors(
    errors: list[dict[str, Any]],
    values: list[tuple[str, Any]],
) -> None:
    for field_path, value in values:
        if value is None:
            continue
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            errors.append(
                _ack_error(
                    "INVALID_TIMESTAMP",
                    f"{field_path} must be an ISO 8601 datetime.",
                    retryable=False,
                )
            )
            continue
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            errors.append(
                _ack_error(
                    "INVALID_TIMESTAMP",
                    f"{field_path} must include timezone offset.",
                    retryable=False,
                )
            )


def _append_authority_errors(
    errors: list[dict[str, Any]],
    payload: Mapping[str, Any],
    inventory_snapshot: object,
    stock_movements: list[Any],
    quality_evidence: object,
) -> None:
    inventory_authority = payload.get("InventoryAuthority")
    quality_authority = payload.get("QualityAuthority")
    if inventory_snapshot is not None and inventory_authority is None:
        errors.append(
            _ack_error(
                "MISSING_INVENTORY_AUTHORITY",
                "InventorySnapshot requires a named inventory authority.",
                retryable=True,
            )
        )
    if stock_movements and inventory_authority is None:
        errors.append(
            _ack_error(
                "MISSING_INVENTORY_AUTHORITY",
                "Stock movements require a named inventory authority.",
                retryable=True,
            )
        )
    if _quality_release_claim_present(quality_evidence) and quality_authority is None:
        errors.append(
            _ack_error(
                "MISSING_QUALITY_AUTHORITY",
                "Quality release evidence requires a named quality authority.",
                retryable=True,
            )
        )
    if any(
        isinstance(movement, Mapping)
        and movement.get("MovementType") == "InspectionRelease"
        for movement in stock_movements
    ) and quality_authority is None:
        errors.append(
            _ack_error(
                "MISSING_QUALITY_AUTHORITY",
                "InspectionRelease movements require a named quality authority.",
                retryable=True,
            )
        )


def _quality_release_claim_present(quality_evidence: object) -> bool:
    return isinstance(quality_evidence, Mapping) and (
        quality_evidence.get("QualityReleaseStatus") == "QualityReleased"
        or quality_evidence.get("InspectionStatus") == "QualityReleased"
        or quality_evidence.get("QualityReleasedAt") is not None
    )


def _append_quantity_errors(
    errors: list[dict[str, Any]],
    inventory_snapshot: object,
    stock_movements: list[Any],
) -> None:
    if isinstance(inventory_snapshot, Mapping):
        available = inventory_snapshot.get("AvailableQty")
        allocated = inventory_snapshot.get("AllocatedQty")
        available_after_allocation = inventory_snapshot.get("AvailableAfterAllocationQty")
        if (
            _number_value(available) is not None
            and _number_value(allocated) is not None
            and _number_value(available_after_allocation) is not None
            and _number_value(available_after_allocation)
            > _number_value(available)
        ):
            errors.append(
                _ack_error(
                    "INVALID_QUANTITY",
                    "AvailableAfterAllocationQty cannot exceed AvailableQty.",
                    retryable=False,
                )
            )
    for movement in stock_movements:
        if not isinstance(movement, Mapping):
            continue
        movement_qty = _number_value(movement.get("MovementQty"))
        movement_type = movement.get("MovementType")
        if movement_qty is None:
            continue
        if movement_qty < 0 and movement_type not in {"Adjustment", "Correction", "Reversal"}:
            errors.append(
                _ack_error(
                    "INVALID_QUANTITY",
                    f"{movement_type} movement quantity cannot be negative.",
                    retryable=False,
                )
            )


def _number_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _append_state_transition_errors(
    errors: list[dict[str, Any]],
    stock_movements: list[Any],
) -> None:
    for movement in stock_movements:
        if not isinstance(movement, Mapping):
            continue
        movement_type = movement.get("MovementType")
        state = movement.get("MovementState")
        expected_states = {
            "InspectionRelease": "QualityReleased",
            "Rejection": "Rejected",
            "Transfer": "Transferred",
            "Reversal": "Reversed",
            "Adjustment": "Adjusted",
            "SnapshotReplacement": "Adjusted",
        }
        expected = expected_states.get(str(movement_type))
        if expected is not None and state != expected:
            errors.append(
                _ack_error(
                    "INVALID_STATE_TRANSITION",
                    f"{movement_type} movement cannot use state {state}.",
                    retryable=False,
                )
            )


def _append_reversal_errors(
    errors: list[dict[str, Any]],
    stock_movements: list[Any],
    reference_resolver: InventoryQualityReferenceResolver | None,
) -> None:
    for movement in stock_movements:
        if not isinstance(movement, Mapping):
            continue
        if movement.get("MovementType") != "Reversal" and movement.get("MovementState") != "Reversed":
            continue
        reverses_movement_id = movement.get("ReversesMovementID")
        if reverses_movement_id is None:
            errors.append(
                _ack_error(
                    "MOVEMENT_REVERSAL_TARGET_NOT_FOUND",
                    "Reversal must reference the original movement.",
                    retryable=False,
                )
            )
            continue
        if (
            reference_resolver is not None
            and reference_resolver.movement_ids is not None
            and str(reverses_movement_id) not in reference_resolver.movement_ids
        ):
            errors.append(
                _ack_error(
                    "MOVEMENT_REVERSAL_TARGET_NOT_FOUND",
                    "Reversal target movement cannot be resolved.",
                    retryable=False,
                )
            )


def _append_supersession_errors(
    errors: list[dict[str, Any]],
    supersession: Mapping[str, Any],
    reference_resolver: InventoryQualityReferenceResolver | None,
) -> None:
    supersedes_id = supersession.get("SupersedesEvidencePackageID")
    correction_reason = supersession.get("CorrectionReason")
    replacement_scope = supersession.get("SnapshotReplacementScope")
    if correction_reason is None and replacement_scope is None:
        return
    if supersedes_id is None:
        errors.append(
            _ack_error(
                "SUPERSESSION_TARGET_NOT_FOUND",
                "Correction or snapshot replacement must reference the prior evidence package.",
                retryable=False,
            )
        )
        return
    if (
        reference_resolver is not None
        and reference_resolver.evidence_package_ids is not None
        and str(supersedes_id) not in reference_resolver.evidence_package_ids
    ):
        errors.append(
            _ack_error(
                "SUPERSESSION_TARGET_NOT_FOUND",
                "Supersession target evidence package cannot be resolved.",
                retryable=False,
            )
        )


def _append_authority_reference_errors(
    errors: list[dict[str, Any]],
    payload: Mapping[str, Any],
    resolver: InventoryQualityReferenceResolver,
) -> None:
    inventory_authority = payload.get("InventoryAuthority")
    quality_authority = payload.get("QualityAuthority")
    if isinstance(inventory_authority, Mapping):
        _append_reference_error(
            errors,
            resolver.inventory_authority_ids,
            inventory_authority.get("AuthoritySystemID"),
            "MISSING_INVENTORY_AUTHORITY",
            "Inventory authority cannot be resolved.",
        )
    if isinstance(quality_authority, Mapping):
        _append_reference_error(
            errors,
            resolver.quality_authority_ids,
            quality_authority.get("AuthoritySystemID"),
            "MISSING_QUALITY_AUTHORITY",
            "Quality authority cannot be resolved.",
        )


def _append_snapshot_reference_errors(
    errors: list[dict[str, Any]],
    inventory_snapshot: object,
    resolver: InventoryQualityReferenceResolver,
) -> None:
    if not isinstance(inventory_snapshot, Mapping):
        return
    snapshot_id = inventory_snapshot.get("SnapshotID")
    _append_reference_error(
        errors,
        resolver.snapshot_ids,
        snapshot_id,
        "STALE_SNAPSHOT",
        "Snapshot cannot be resolved.",
    )
    if resolver.stale_snapshot_ids is not None and str(snapshot_id) in resolver.stale_snapshot_ids:
        errors.append(
            _ack_error(
                "STALE_SNAPSHOT",
                "Snapshot is stale under the configured policy.",
                retryable=True,
            )
        )


def _append_movement_reference_errors(
    errors: list[dict[str, Any]],
    stock_movements: list[Any],
    resolver: InventoryQualityReferenceResolver,
) -> None:
    for movement in stock_movements:
        if not isinstance(movement, Mapping):
            continue
        movement_id = movement.get("MovementID")
        if resolver.conflicting_movement_ids is not None and str(movement_id) in resolver.conflicting_movement_ids:
            errors.append(
                _ack_error(
                    "CONFLICTING_MOVEMENT",
                    "Movement conflicts with existing authority evidence.",
                    retryable=False,
                )
            )
        _append_reference_error(
            errors,
            resolver.uoms,
            movement.get("MovementUOM"),
            "UNSUPPORTED_UOM",
            "Movement UOM cannot be resolved.",
        )


def _append_quality_release_reference_errors(
    errors: list[dict[str, Any]],
    quality_evidence: object,
    resolver: InventoryQualityReferenceResolver,
) -> None:
    if not isinstance(quality_evidence, Mapping):
        return
    quality_release_id = quality_evidence.get("QualityReleaseID")
    if quality_release_id is not None:
        _append_reference_error(
            errors,
            resolver.quality_release_ids,
            quality_release_id,
            "MISSING_QUALITY_AUTHORITY",
            "Quality release cannot be resolved.",
        )


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
    if "InventoryAuthority" in path or "InventoryAuthority" in message:
        code = "MISSING_INVENTORY_AUTHORITY"
    elif "QualityAuthority" in path or "QualityAuthority" in message:
        code = "MISSING_QUALITY_AUTHORITY"
    elif "ItemID" in path or "ItemID" in message:
        code = "UNKNOWN_ITEM"
    elif "LocationID" in path or "LocationID" in message:
        code = "UNKNOWN_LOCATION"
    elif "LotID" in path or "SerialID" in path:
        code = "UNKNOWN_LOT_OR_SERIAL"
    elif "UOM" in path or "UOM" in message:
        code = "UNSUPPORTED_UOM"
    elif "Qty" in path or "quantity" in message.lower() or error.validator == "minimum":
        code = "INVALID_QUANTITY"
    elif "Timestamp" in path or path.endswith("At") or "date-time" in message:
        code = "INVALID_TIMESTAMP"
    elif "AllowsAutomaticMasterSettingUpdate" in path:
        code = "GOVERNANCE_AUTO_UPDATE_FORBIDDEN"
    else:
        code = "CONTRACT_SCOPE_VIOLATION"
    return _ack_error(code, message, retryable=False)


def _ack_error(code: str, message: str, *, retryable: bool) -> dict[str, Any]:
    return {"ErrorCode": code, "ErrorMessage": message, "Retryable": retryable}


def _status_for_errors(errors: list[dict[str, Any]]) -> str:
    codes = {str(error.get("ErrorCode")) for error in errors}
    return "DeadLettered" if codes & DEAD_LETTER_ERROR_CODES else "Rejected"


def _evidence_package_id(message: Mapping[str, Any]) -> str:
    payload = message.get("Payload", {})
    if isinstance(payload, Mapping):
        value = payload.get("EvidencePackageID")
        if value is not None:
            return str(value)
    return "UNKNOWN"


def _find_duplicate(
    records: list[Mapping[str, Any]],
    *,
    idempotency_key: str,
) -> Mapping[str, Any] | None:
    for record in records:
        if str(record.get("IdempotencyKey", "")) == idempotency_key:
            return record
    return None


def _is_source_authoritative(message: Mapping[str, Any]) -> bool:
    payload = message.get("Payload", {})
    if not isinstance(payload, Mapping):
        return False
    inventory_authority = payload.get("InventoryAuthority")
    quality_authority = payload.get("QualityAuthority")
    authority_confidences = []
    for authority in (inventory_authority, quality_authority):
        if isinstance(authority, Mapping):
            authority_confidences.append(authority.get("AuthorityConfidence"))
    return (
        payload.get("EvidenceStatus") == SOURCE_AUTHORITATIVE_STATUS
        and payload.get("EvidenceConfidence") == SOURCE_AUTHORITATIVE_STATUS
        and authority_confidences
        and all(confidence == SOURCE_AUTHORITATIVE_STATUS for confidence in authority_confidences)
    )


def _accepted_evidence_record(
    message: Mapping[str, Any],
    *,
    source_authoritative_usable: bool,
) -> dict[str, Any]:
    payload = dict(message["Payload"])
    item_location = dict(payload["ItemLocation"])
    snapshot = payload.get("InventorySnapshot")
    quality_evidence = payload.get("QualityEvidence")
    return {
        "EvidencePackageID": str(payload["EvidencePackageID"]),
        "EvidenceVersion": str(payload["EvidenceVersion"]),
        "EvidenceStatus": str(payload["EvidenceStatus"]),
        "EvidenceConfidence": str(payload["EvidenceConfidence"]),
        "ItemID": str(item_location["ItemID"]),
        "LocationID": str(item_location["LocationID"]),
        "ProgramID": item_location.get("ProgramID"),
        "QuantityUOM": str(item_location["QuantityUOM"]),
        "SnapshotID": snapshot.get("SnapshotID") if isinstance(snapshot, Mapping) else None,
        "QualityReleaseID": (
            quality_evidence.get("QualityReleaseID")
            if isinstance(quality_evidence, Mapping)
            else None
        ),
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
) -> InventoryQualityProcessingResult:
    payload = message.get("Payload", {})
    evidence_version = (
        str(payload.get("EvidenceVersion", "")) if isinstance(payload, Mapping) else ""
    )
    record = {
        "ContractID": CONTRACT_ID,
        "MessageID": str(message.get("MessageID", "")),
        "IdempotencyKey": str(message.get("IdempotencyKey", "")),
        "EvidencePackageID": _evidence_package_id(message),
        "EvidenceVersion": evidence_version,
        "ReceivedAt": received_at.isoformat(),
        "Ack": ack,
        "AckStatus": ack["AckStatus"],
        "PayloadFingerprint": fingerprint,
        "Payload": deepcopy(dict(message)),
        "AcceptedEvidence": deepcopy(accepted_evidence),
        "DeadLettered": ack["AckStatus"] == "DeadLettered",
        "Errors": deepcopy(ack["Errors"]),
    }
    return InventoryQualityProcessingResult(
        ack=ack,
        inbound_ledger_record=record,
        accepted_evidence=accepted_evidence,
    )


def _safe_id(value: str) -> str:
    allowed = [ch if ch.isalnum() else "-" for ch in value]
    return "".join(allowed).strip("-") or "UNKNOWN"


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
