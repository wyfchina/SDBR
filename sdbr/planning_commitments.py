from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Mapping


DEMAND_SOURCE_TYPES = {
    "MTOCustomerOrder",
    "MTAReplenishment",
    "DependentDemand",
    "ExternalFormalOrder",
    "Adjustment",
}
ACTIVE_DEMAND_STATUSES = {
    "Active",
    "LinkedToFormalOrder",
    "HeldForPlanningError",
}


class DemandCommitmentConflict(ValueError):
    status = "DemandCommitmentConflict"


class DemandCommitmentMigrationRequired(DemandCommitmentConflict):
    status = "DemandCommitmentMigrationRequired"


BUSINESS_CONTENT_FIELDS = (
    "DemandSourceType",
    "SourceSystem",
    "SourceObjectType",
    "SourceObjectID",
    "SourceObjectVersion",
    "DemandLineID",
    "ItemOrProductID",
    "LocationID",
    "Quantity",
    "Uom",
    "RequiredAt",
    "DemandClass",
)
_BUSINESS_KEY_FIELDS = (
    "SourceSystem",
    "SourceObjectType",
    "SourceObjectID",
    "SourceObjectVersion",
    "DemandLineID",
    "ItemOrProductID",
    "LocationID",
)
_LOGICAL_DEMAND_KEY_FIELDS = tuple(
    field for field in _BUSINESS_KEY_FIELDS if field != "SourceObjectVersion"
)
_REQUIRED_STRING_FIELDS = (
    "DemandSourceType",
    "SourceSystem",
    "SourceObjectType",
    "SourceObjectID",
    "SourceObjectVersion",
    "DemandLineID",
    "ItemOrProductID",
    "LocationID",
    "Uom",
    "DemandClass",
)
_DERIVED_FIELDS = (
    "BusinessKey",
    "LogicalDemandKey",
    "DemandCommitmentID",
    "ContentFingerprint",
)


def _canonical_identity(**identity_fields: str) -> str:
    return json.dumps(identity_fields, sort_keys=True, separators=(",", ":"))


def _validate_quantity(quantity: object) -> float:
    if isinstance(quantity, bool) or not isinstance(quantity, Real):
        raise ValueError(
            "Demand commitment quantity must be a finite, strictly positive real number."
        )
    try:
        normalized_quantity = float(quantity)
    except OverflowError as error:
        raise ValueError(
            "Demand commitment quantity must be a finite, strictly positive real number."
        ) from error
    if not isfinite(normalized_quantity) or normalized_quantity <= 0:
        raise ValueError(
            "Demand commitment quantity must be a finite, strictly positive real number."
        )
    return normalized_quantity


def _canonical_utc_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _required_string(record: Mapping[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Demand commitment {field} must be a non-empty string."
        )
    return value


def _normalized_business_content(
    record: Mapping[str, object],
) -> dict[str, object]:
    try:
        required_at_value = record["RequiredAt"]
    except KeyError as error:
        raise ValueError(
            "Demand commitment business content is incomplete or invalid."
        ) from error
    strings = {
        field: _required_string(record, field)
        for field in _REQUIRED_STRING_FIELDS
    }
    if strings["DemandSourceType"] not in DEMAND_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported demand source type: {strings['DemandSourceType']}."
        )
    quantity = _validate_quantity(record.get("Quantity"))
    try:
        required_at = (
            required_at_value
            if isinstance(required_at_value, datetime)
            else datetime.fromisoformat(
                str(required_at_value).replace("Z", "+00:00")
            )
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Demand commitment required time must be timezone-aware."
        ) from error
    if required_at.tzinfo is None or required_at.utcoffset() is None:
        raise ValueError("Demand commitment required time must be timezone-aware.")
    return {
        "DemandSourceType": strings["DemandSourceType"],
        "SourceSystem": strings["SourceSystem"],
        "SourceObjectType": strings["SourceObjectType"],
        "SourceObjectID": strings["SourceObjectID"],
        "SourceObjectVersion": strings["SourceObjectVersion"],
        "DemandLineID": strings["DemandLineID"],
        "ItemOrProductID": strings["ItemOrProductID"],
        "LocationID": strings["LocationID"],
        "Quantity": quantity,
        "Uom": strings["Uom"],
        "RequiredAt": _canonical_utc_datetime(required_at),
        "DemandClass": strings["DemandClass"],
    }


def _business_content_fingerprint(content: Mapping[str, object]) -> str:
    fingerprint = sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{fingerprint}"


def demand_commitment_content_fingerprint(record: Mapping[str, object]) -> str:
    return _business_content_fingerprint(_normalized_business_content(record))


def normalize_demand_commitment(
    record: Mapping[str, object],
    *,
    require_derived_fields: bool = True,
) -> dict[str, object]:
    content = _normalized_business_content(record)
    _required_string(record, "TraceID")
    business_key = _canonical_identity(
        **{field: str(content[field]) for field in _BUSINESS_KEY_FIELDS}
    )
    logical_demand_key = _canonical_identity(
        **{
            field: str(content[field])
            for field in _LOGICAL_DEMAND_KEY_FIELDS
        }
    )
    derived = {
        "BusinessKey": business_key,
        "LogicalDemandKey": logical_demand_key,
        "DemandCommitmentID": (
            f"DC-{sha256(business_key.encode('utf-8')).hexdigest()[:20]}"
        ),
        "ContentFingerprint": _business_content_fingerprint(content),
    }
    for field in _DERIVED_FIELDS:
        if require_derived_fields and field not in record:
            raise ValueError(
                f"Demand commitment derived identity field {field} is required."
            )
        if field in record and record.get(field) != derived[field]:
            raise ValueError(
                f"Demand commitment derived identity field {field} does not "
                "match canonical business content."
            )
    normalized = dict(record)
    normalized.update(content)
    normalized.update(derived)
    return normalized


def create_demand_commitment(
    *,
    demand_source_type: str,
    source_system: str,
    source_object_type: str,
    source_object_id: str,
    source_object_version: str,
    demand_line_id: str,
    item_or_product_id: str,
    location_id: str,
    quantity: float,
    uom: str,
    required_at: datetime,
    demand_class: str,
    trace_id: str,
) -> dict[str, object]:
    return normalize_demand_commitment(
        {
            "DemandSourceType": demand_source_type,
            "SourceSystem": source_system,
            "SourceObjectType": source_object_type,
            "SourceObjectID": source_object_id,
            "SourceObjectVersion": source_object_version,
            "DemandLineID": demand_line_id,
            "ItemOrProductID": item_or_product_id,
            "LocationID": location_id,
            "Quantity": quantity,
            "Uom": uom,
            "RequiredAt": required_at,
            "DemandClass": demand_class,
            "Status": "PendingConfirmation",
            "RecordVersion": 1,
            "TraceID": trace_id,
        },
        require_derived_fields=False,
    )


def _normalized_persisted_ledger(
    commitments: Mapping[str, dict[str, object]],
) -> list[tuple[str, dict[str, object], dict[str, object]]]:
    normalized_rows: list[tuple[str, dict[str, object], dict[str, object]]] = []
    business_key_counts: dict[str, int] = {}
    for ledger_key, existing in commitments.items():
        if not isinstance(existing, Mapping):
            raise DemandCommitmentMigrationRequired(
                "Persisted demand commitment cannot be verified without explicit "
                "migration."
            )
        try:
            normalized = normalize_demand_commitment(existing)
        except ValueError as error:
            raise DemandCommitmentMigrationRequired(
                "Persisted demand commitment cannot be verified without explicit "
                f"migration: {error}"
            ) from error
        business_key = str(normalized["BusinessKey"])
        business_key_counts[business_key] = (
            business_key_counts.get(business_key, 0) + 1
        )
        normalized_rows.append((ledger_key, dict(existing), normalized))
    if any(count > 1 for count in business_key_counts.values()):
        raise DemandCommitmentMigrationRequired(
            "Persisted demand ledger has multiple persisted demand commitments "
            "with the same canonical business key."
        )
    for ledger_key, _existing, normalized in normalized_rows:
        if ledger_key != normalized["DemandCommitmentID"]:
            raise DemandCommitmentMigrationRequired(
                "Persisted demand commitment ID does not match its ledger key; "
                "explicit migration is required."
            )
    return normalized_rows


def register_demand_commitment(
    commitments: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> tuple[str, dict[str, object]]:
    persisted_rows = _normalized_persisted_ledger(commitments)
    try:
        normalized_candidate = normalize_demand_commitment(candidate)
    except ValueError as error:
        raise DemandCommitmentConflict(
            f"Candidate demand commitment identity or content is invalid: {error}"
        ) from error
    for _ledger_key, existing, normalized_existing in persisted_rows:
        if (
            normalized_existing["BusinessKey"]
            != normalized_candidate["BusinessKey"]
        ):
            continue
        if (
            all(
                normalized_existing[field] == normalized_candidate[field]
                for field in BUSINESS_CONTENT_FIELDS
            )
            and normalized_existing["ContentFingerprint"]
            == normalized_candidate["ContentFingerprint"]
        ):
            return "Duplicate", dict(existing)
        raise DemandCommitmentConflict(
            "Demand commitment with the same business key has different content."
        )
    return "Created", normalized_candidate


def assert_no_active_predecessor(
    commitments: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> None:
    persisted_rows = _normalized_persisted_ledger(commitments)
    try:
        normalized_candidate = normalize_demand_commitment(candidate)
    except ValueError as error:
        raise DemandCommitmentConflict(
            f"Candidate demand commitment identity or content is invalid: {error}"
        ) from error
    for _ledger_key, _existing, normalized_existing in persisted_rows:
        if (
            normalized_existing["LogicalDemandKey"]
            == normalized_candidate["LogicalDemandKey"]
            and normalized_existing["BusinessKey"]
            != normalized_candidate["BusinessKey"]
            and normalized_existing.get("Status") in ACTIVE_DEMAND_STATUSES
        ):
            raise DemandCommitmentConflict(
                "New demand version cannot activate while an active predecessor exists."
            )
