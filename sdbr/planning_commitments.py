from __future__ import annotations

from datetime import datetime
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
    pass


def _canonical_identity(**identity_fields: str) -> str:
    return json.dumps(identity_fields, sort_keys=True, separators=(",", ":"))


def _validate_quantity(quantity: float) -> float:
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
    if demand_source_type not in DEMAND_SOURCE_TYPES:
        raise ValueError(f"Unsupported demand source type: {demand_source_type}.")
    normalized_quantity = _validate_quantity(quantity)
    if required_at.tzinfo is None or required_at.utcoffset() is None:
        raise ValueError("Demand commitment required time must be timezone-aware.")
    business_key = _canonical_identity(
        SourceSystem=source_system,
        SourceObjectType=source_object_type,
        SourceObjectID=source_object_id,
        SourceObjectVersion=source_object_version,
        DemandLineID=demand_line_id,
        ItemOrProductID=item_or_product_id,
        LocationID=location_id,
    )
    logical_demand_key = _canonical_identity(
        SourceSystem=source_system,
        SourceObjectType=source_object_type,
        SourceObjectID=source_object_id,
        DemandLineID=demand_line_id,
        ItemOrProductID=item_or_product_id,
        LocationID=location_id,
    )
    content = {
        "DemandSourceType": demand_source_type,
        "SourceSystem": source_system,
        "SourceObjectType": source_object_type,
        "SourceObjectID": source_object_id,
        "SourceObjectVersion": source_object_version,
        "DemandLineID": demand_line_id,
        "ItemOrProductID": item_or_product_id,
        "LocationID": location_id,
        "Quantity": normalized_quantity,
        "Uom": uom,
        "RequiredAt": required_at.isoformat(),
        "DemandClass": demand_class,
        "TraceID": trace_id,
    }
    fingerprint = sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "DemandCommitmentID": f"DC-{sha256(business_key.encode('utf-8')).hexdigest()[:20]}",
        "BusinessKey": business_key,
        "LogicalDemandKey": logical_demand_key,
        "ContentFingerprint": f"sha256:{fingerprint}",
        "Status": "PendingConfirmation",
        **content,
    }


def register_demand_commitment(
    commitments: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> tuple[str, dict[str, object]]:
    for existing in commitments.values():
        if existing.get("BusinessKey") != candidate.get("BusinessKey"):
            continue
        if existing.get("ContentFingerprint") == candidate.get("ContentFingerprint"):
            return "Duplicate", dict(existing)
        raise DemandCommitmentConflict(
            "Demand commitment with the same business key has different content."
        )
    return "Created", dict(candidate)


def assert_no_active_predecessor(
    commitments: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> None:
    for existing in commitments.values():
        if (
            existing.get("LogicalDemandKey") == candidate.get("LogicalDemandKey")
            and existing.get("BusinessKey") != candidate.get("BusinessKey")
            and existing.get("Status") in ACTIVE_DEMAND_STATUSES
        ):
            raise DemandCommitmentConflict(
                "New demand version cannot activate while an active predecessor exists."
            )
