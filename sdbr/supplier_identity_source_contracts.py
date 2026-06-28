from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


CONTRACT_ID = "PRODUCTION-SUPPLIER-IDENTITY-SOURCE-V1"
CONTRACT_VERSION = "1.0.0"
CONSUMER_SYSTEM = "SDBR"
DEFAULT_CONTRACT_ROOT = Path(
    os.environ.get(
        "DDAE_INTERFACE_CONTRACT_ROOT",
        r"D:\Documents\DDAE_INTERFACE_CONTRACT",
    )
)

ACK_STATUSES = {"Accepted", "Rejected", "Duplicate", "DeadLettered"}
ACTIVE_SOURCE_STATUS = "Effective"
NON_ACTIVE_STATUSES = {
    "Candidate",
    "Reviewed",
    "Suspended",
    "Expired",
    "Superseded",
    "Rejected",
}
DEAD_LETTER_ERROR_CODES = {
    "MISSING_SOURCE_AUTHORITY",
    "UNKNOWN_SUPPLIER",
    "UNKNOWN_ITEM",
    "UNKNOWN_LOCATION",
    "UNKNOWN_SOURCE_RELATION",
    "CONFLICTING_SOURCE",
    "IDEMPOTENCY_CONFLICT",
}
REQUIRED_NON_CLAIMS = {
    "NotProductionValidated",
    "NotInventoryBalanceProof",
    "NotQualityReleaseProof",
    "NotSupplierExecutionProof",
    "NotDeliveryPerformanceProof",
    "NotLeadTimePerformanceProof",
    "NoAutomaticDDAEMasterSettingUpdate",
    "NotBusinessGoldenLoopReady",
}


@dataclass(frozen=True)
class SupplierSourceReferenceResolver:
    supplier_ids: set[str] | None = None
    item_ids: set[str] | None = None
    location_ids: set[str] | None = None
    program_ids: set[str] | None = None
    supplier_source_relation_ids: set[str] | None = None
    uoms: set[str] | None = None
    source_authority_ids: set[str] | None = None


@dataclass(frozen=True)
class SupplierIdentitySourceProcessingResult:
    ack: dict[str, Any]
    inbound_ledger_record: dict[str, Any]
    accepted_evidence: dict[str, Any] | None


def contract_root() -> Path:
    return DEFAULT_CONTRACT_ROOT


def message_schema() -> dict[str, Any]:
    return _load_json(
        _contract_path(
            "production-supplier-identity-source-v1",
            "schema",
            "production-supplier-identity-source-v1.schema.json",
        )
    )


def ack_schema() -> dict[str, Any]:
    return _load_json(
        _contract_path(
            "production-supplier-identity-source-v1",
            "schema",
            "production-supplier-identity-source-ack-v1.schema.json",
        )
    )


def process_supplier_identity_source_message(
    message: Mapping[str, Any],
    *,
    received_at: datetime,
    existing_ledger_records: list[Mapping[str, Any]] | None = None,
    reference_resolver: SupplierSourceReferenceResolver | None = None,
    require_active_source: bool = False,
) -> SupplierIdentitySourceProcessingResult:
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
            ack = build_supplier_identity_source_ack(
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
        ack = build_supplier_identity_source_ack(
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
            require_active_source=require_active_source,
        )
    if errors:
        status = _status_for_errors(errors)
        ack = build_supplier_identity_source_ack(
            message_id=message_id,
            evidence_package_id=evidence_package_id,
            ack_status=status,
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
        active_source_usable=_is_active_source(normalized),
    )
    ack = build_supplier_identity_source_ack(
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


def build_supplier_identity_source_ack(
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
        "AckID": f"PSISV1-ACK-SDBR-{_safe_id(message_id)}-{ack_status}",
        "MessageID": message_id,
        "EvidencePackageID": evidence_package_id,
        "ConsumerSystem": CONSUMER_SYSTEM,
        "AckStatus": ack_status,
        "AckAt": ack_at.isoformat(),
        "Errors": errors,
    }
    validate_supplier_identity_source_ack(ack)
    return ack


def validate_supplier_identity_source_ack(ack: Mapping[str, Any]) -> None:
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
    reference_resolver: SupplierSourceReferenceResolver | None,
    require_active_source: bool,
) -> list[dict[str, Any]]:
    payload = dict(message.get("Payload", {}))
    source_authority = dict(payload.get("SourceAuthority", {}))
    supplier_identity = dict(payload.get("SupplierIdentity", {}))
    relation = dict(payload.get("SupplierSourceRelation", {}))
    source_terms = dict(payload.get("SourceTerms", {}))
    governance = dict(payload.get("DDAEGovernanceBoundary", {}))
    traceability = dict(payload.get("Traceability", {}))
    errors: list[dict[str, Any]] = []

    _append_datetime_errors(
        errors,
        [
            ("OccurredAt", message.get("OccurredAt")),
            ("Payload.SupplierSourceRelation.EffectiveFrom", relation.get("EffectiveFrom")),
            ("Payload.SupplierSourceRelation.EffectiveTo", relation.get("EffectiveTo")),
            ("Payload.Traceability.RegisteredAt", traceability.get("RegisteredAt")),
            ("Payload.Traceability.ApprovedAt", traceability.get("ApprovedAt")),
        ],
    )
    _append_effective_window_errors(errors, relation)
    if (
        source_terms.get("TermsAreProductionAuthoritative") is True
        and source_terms.get("DDAEPlanningAssumptionOnly") is True
    ):
        errors.append(
            _ack_error(
                "CONTRACT_SCOPE_VIOLATION",
                "Source terms cannot be both production-authoritative and DDAE planning assumptions.",
                retryable=False,
            )
        )
    if governance.get("AllowsAutomaticMasterSettingUpdate") is not False:
        errors.append(
            _ack_error(
                "GOVERNANCE_AUTO_UPDATE_FORBIDDEN",
                "Supplier/source evidence cannot automatically update DDAE master settings.",
                retryable=False,
            )
        )
    if governance.get("RequiresSeparateDDAEApproval") is not True:
        errors.append(
            _ack_error(
                "GOVERNANCE_AUTO_UPDATE_FORBIDDEN",
                "Supplier/source evidence must require separate DDAE approval.",
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
    if require_active_source and not _is_active_source(message):
        errors.append(
            _ack_error(
                "UNAPPROVED_SOURCE",
                "Only Effective supplier/source evidence can be consumed as an active SDBR source authority.",
                retryable=False,
            )
        )
    resolver = reference_resolver
    if resolver is not None:
        _append_reference_error(
            errors,
            resolver.source_authority_ids,
            source_authority.get("AuthoritySystemID"),
            "MISSING_SOURCE_AUTHORITY",
            "Source authority is missing or cannot be resolved.",
        )
        _append_reference_error(
            errors,
            resolver.supplier_ids,
            supplier_identity.get("SupplierID"),
            "UNKNOWN_SUPPLIER",
            "Supplier identity cannot be resolved.",
        )
        _append_reference_error(
            errors,
            resolver.item_ids,
            relation.get("ItemID"),
            "UNKNOWN_ITEM",
            "Item cannot be resolved.",
        )
        location_id = relation.get("LocationID")
        if location_id is not None:
            _append_reference_error(
                errors,
                resolver.location_ids,
                location_id,
                "UNKNOWN_LOCATION",
                "Location cannot be resolved.",
            )
        program_id = relation.get("ProgramID")
        if program_id is not None:
            _append_reference_error(
                errors,
                resolver.program_ids,
                program_id,
                "UNKNOWN_SOURCE_RELATION",
                "Program scope cannot be resolved.",
            )
        _append_reference_error(
            errors,
            resolver.supplier_source_relation_ids,
            relation.get("SupplierSourceRelationID"),
            "UNKNOWN_SOURCE_RELATION",
            "Supplier-source relation cannot be resolved.",
        )
        _append_reference_error(
            errors,
            resolver.uoms,
            source_terms.get("UOM"),
            "UNSUPPORTED_UOM",
            "UOM cannot be resolved.",
        )
    return errors


def _schema_error_to_ack_error(error) -> dict[str, Any]:
    path = ".".join(str(item) for item in error.absolute_path)
    message = str(error.message)
    if error.validator == "not" and "SourceTerms" in path:
        return _ack_error(
            "CONTRACT_SCOPE_VIOLATION",
            "Source terms cannot be both production-authoritative and DDAE planning assumptions.",
            retryable=False,
        )
    if "SourceAuthority" in message or "SourceAuthority" in path:
        code = "MISSING_SOURCE_AUTHORITY"
    elif "SupplierID" in message or "SupplierIdentity" in path:
        code = "UNKNOWN_SUPPLIER"
    elif "ItemID" in message or "ItemID" in path:
        code = "UNKNOWN_ITEM"
    elif "LocationID" in message or "LocationID" in path:
        code = "UNKNOWN_LOCATION"
    elif "UOM" in message or "UOM" in path:
        code = "UNSUPPORTED_UOM"
    elif "AllowsAutomaticMasterSettingUpdate" in path:
        code = "GOVERNANCE_AUTO_UPDATE_FORBIDDEN"
    else:
        code = "CONTRACT_SCOPE_VIOLATION" if error.validator in {"enum", "const"} else "CONTRACT_SCOPE_VIOLATION"
    return _ack_error(code, message, retryable=False)


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
                    "INVALID_EFFECTIVE_WINDOW",
                    f"{field_path} must be an ISO 8601 datetime.",
                    retryable=False,
                )
            )
            continue
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            errors.append(
                _ack_error(
                    "INVALID_EFFECTIVE_WINDOW",
                    f"{field_path} must include timezone offset.",
                    retryable=False,
                )
            )


def _append_effective_window_errors(
    errors: list[dict[str, Any]],
    relation: Mapping[str, Any],
) -> None:
    effective_from = relation.get("EffectiveFrom")
    effective_to = relation.get("EffectiveTo")
    if effective_from is None or effective_to is None:
        return
    try:
        if datetime.fromisoformat(str(effective_to)) < datetime.fromisoformat(
            str(effective_from)
        ):
            errors.append(
                _ack_error(
                    "INVALID_EFFECTIVE_WINDOW",
                    "EffectiveTo must be greater than or equal to EffectiveFrom.",
                    retryable=False,
                )
            )
    except ValueError:
        errors.append(
            _ack_error(
                "INVALID_EFFECTIVE_WINDOW",
                "EffectiveFrom or EffectiveTo is not a valid ISO 8601 datetime.",
                retryable=False,
            )
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


def _is_active_source(message: Mapping[str, Any]) -> bool:
    payload = message.get("Payload", {})
    if not isinstance(payload, Mapping):
        return False
    relation = payload.get("SupplierSourceRelation", {})
    identity = payload.get("SupplierIdentity", {})
    if not isinstance(relation, Mapping) or not isinstance(identity, Mapping):
        return False
    return (
        payload.get("EvidenceStatus") == ACTIVE_SOURCE_STATUS
        and relation.get("EligibilityStatus") == ACTIVE_SOURCE_STATUS
        and identity.get("ApprovedSupplierStatus") == ACTIVE_SOURCE_STATUS
    )


def _accepted_evidence_record(
    message: Mapping[str, Any],
    *,
    active_source_usable: bool,
) -> dict[str, Any]:
    payload = dict(message["Payload"])
    relation = dict(payload["SupplierSourceRelation"])
    identity = dict(payload["SupplierIdentity"])
    return {
        "EvidencePackageID": str(payload["EvidencePackageID"]),
        "EvidenceVersion": str(payload["EvidenceVersion"]),
        "EvidenceStatus": str(payload["EvidenceStatus"]),
        "EvidenceConfidence": str(payload["EvidenceConfidence"]),
        "SupplierID": str(identity["SupplierID"]),
        "ItemID": str(relation["ItemID"]),
        "LocationID": relation.get("LocationID"),
        "ProgramID": relation.get("ProgramID"),
        "SupplierSourceRelationID": str(relation["SupplierSourceRelationID"]),
        "ActiveSourceUsable": active_source_usable,
        "NonClaims": list(payload.get("NonClaims", [])),
    }


def _result(
    *,
    message: Mapping[str, Any],
    ack: dict[str, Any],
    received_at: datetime,
    fingerprint: str,
    accepted_evidence: dict[str, Any] | None,
) -> SupplierIdentitySourceProcessingResult:
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
    return SupplierIdentitySourceProcessingResult(
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
