from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Literal

from sdbr.planning_commitments import create_demand_commitment


class OrderCommitmentConflict(ValueError):
    status = "OrderCommitmentConflict"


class OrderCommitmentStale(OrderCommitmentConflict):
    status = "OrderCommitmentEvaluationStale"


class OrderCommitmentSnapshotNotFound(OrderCommitmentConflict):
    status = "OperationalStateSnapshotNotFound"

    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id
        super().__init__(
            f"Operational state snapshot was not found: {snapshot_id}."
        )


@dataclass(frozen=True, slots=True)
class CcrProtectionPolicy:
    target_percent: float
    source: Literal["ApprovedOperatingModel", "ReferenceFallback"]
    approved: bool
    configuration_id: str | None = None


REFERENCE_CCR_PROTECTION_POLICY = CcrProtectionPolicy(
    target_percent=80.0,
    source="ReferenceFallback",
    approved=False,
)


def require_aware(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise OrderCommitmentConflict(f"{field} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise OrderCommitmentConflict(f"{field} must be timezone-aware.")
    return value


def _utc(value: datetime) -> datetime:
    require_aware(value, "Datetime")
    return value.astimezone(timezone.utc)


def _parse_aware(value: object) -> datetime:
    if isinstance(value, datetime):
        return _utc(value)
    try:
        return _utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except (TypeError, ValueError) as error:
        raise OrderCommitmentConflict("Datetime must be timezone-aware.") from error


def _utc_iso(value: datetime) -> str:
    return _utc(value).isoformat()


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_fingerprint(value: object) -> str:
    return f"sha256:{sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


ORDER_CONTENT_FIELDS = (
    "SourceSystem",
    "SourceObjectType",
    "OrderID",
    "OrderVersion",
    "DemandLineID",
    "ProductID",
    "LocationID",
    "Quantity",
    "Uom",
    "RequestedDueAt",
    "BusinessPriority",
    "ReceivedAt",
    "BaselinePlanningRunID",
    "RoutingID",
    "MaterialRequirements",
)


def _positive_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise OrderCommitmentConflict(f"{field} must be finite and positive.")
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise OrderCommitmentConflict(f"{field} must be finite and positive.")
    return normalized


def _required_text(record: Mapping[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise OrderCommitmentConflict(f"{field} is required.")
    return value.strip()


def normalize_mto_order(record: Mapping[str, object]) -> dict[str, object]:
    text_fields = (
        "SourceSystem",
        "SourceObjectType",
        "OrderID",
        "OrderVersion",
        "DemandLineID",
        "ProductID",
        "LocationID",
        "Uom",
        "TraceID",
        "BaselinePlanningRunID",
        "RoutingID",
    )
    order = {field: _required_text(record, field) for field in text_fields}
    order["Quantity"] = _positive_number(record.get("Quantity"), "Quantity")
    order["RequestedDueAt"] = _parse_aware(
        record.get("RequestedDueAt")
    ).isoformat()
    received_at = _parse_aware(record.get("ReceivedAt"))
    order["ReceivedAt"] = received_at.isoformat()
    priority = record.get("BusinessPriority")
    if (
        isinstance(priority, bool)
        or not isinstance(priority, int)
        or not 1 <= priority <= 999
    ):
        raise OrderCommitmentConflict("BusinessPriority must be in 1..999.")
    order["BusinessPriority"] = priority
    raw_requirements = record.get("MaterialRequirements")
    if not isinstance(raw_requirements, list):
        raise OrderCommitmentConflict("MaterialRequirements must be a list.")
    requirements: list[dict[str, object]] = []
    requirement_line_ids: set[str] = set()
    for raw in raw_requirements:
        if not isinstance(raw, Mapping):
            raise OrderCommitmentConflict("Material requirement must be an object.")
        requirement = {
            "RequirementLineID": _required_text(raw, "RequirementLineID"),
            "ItemID": _required_text(raw, "ItemID"),
            "LocationID": _required_text(raw, "LocationID"),
            "RequiredQty": _positive_number(raw.get("RequiredQty"), "RequiredQty"),
            "Uom": _required_text(raw, "Uom"),
        }
        requirement_line_id = str(requirement["RequirementLineID"])
        if requirement_line_id in requirement_line_ids:
            raise OrderCommitmentConflict(
                "Material requirement line is duplicated."
            )
        requirement_line_ids.add(requirement_line_id)
        requirements.append(requirement)
    order["MaterialRequirements"] = sorted(
        requirements,
        key=lambda row: (
            str(row["RequirementLineID"]),
            str(row["ItemID"]),
            str(row["LocationID"]),
            str(row["Uom"]),
            float(row["RequiredQty"]),
        ),
    )
    identity = {
        "SourceSystem": order["SourceSystem"],
        "SourceObjectType": order["SourceObjectType"],
        "OrderID": order["OrderID"],
        "OrderVersion": order["OrderVersion"],
        "DemandLineID": order["DemandLineID"],
        "ProductID": order["ProductID"],
        "LocationID": order["LocationID"],
    }
    order["OrderKey"] = canonical_json(identity)
    logical_order_key = canonical_json(
        {key: value for key, value in identity.items() if key != "OrderVersion"}
    )
    order["LogicalOrderKey"] = logical_order_key
    order["OrderVersionRank"] = [order["ReceivedAt"], order["OrderVersion"]]
    order["PlanningOrderID"] = (
        f"MTO-{sha256(logical_order_key.encode('utf-8')).hexdigest()}"
    )
    order["OrderContentFingerprint"] = canonical_fingerprint(
        {field: order[field] for field in ORDER_CONTENT_FIELDS}
    )
    return order


def candidate_demand_commitment_id(order: Mapping[str, object]) -> str:
    return str(
        create_demand_commitment(
            demand_source_type="MTOCustomerOrder",
            source_system=str(order["SourceSystem"]),
            source_object_type=str(order["SourceObjectType"]),
            source_object_id=str(order["OrderID"]),
            source_object_version=str(order["OrderVersion"]),
            demand_line_id=str(order["DemandLineID"]),
            item_or_product_id=str(order["ProductID"]),
            location_id=str(order["LocationID"]),
            quantity=float(order["Quantity"]),
            uom=str(order["Uom"]),
            required_at=_parse_aware(order["RequestedDueAt"]),
            demand_class="MTO",
            trace_id=str(order["TraceID"]),
        )["DemandCommitmentID"]
    )


def normalized_policy_dict(
    policy: CcrProtectionPolicy,
) -> dict[str, object]:
    if type(policy.approved) is not bool:
        raise OrderCommitmentConflict("Approved must be a boolean.")
    target = _positive_number(policy.target_percent, "TargetPercent")
    if policy.configuration_id is None:
        configuration_id = None
    elif not isinstance(policy.configuration_id, str):
        raise OrderCommitmentConflict(
            "ConfigurationID must be a nonblank identifier string."
        )
    else:
        configuration_id = policy.configuration_id.strip()
        if not configuration_id or any(
            character.isspace() or not character.isprintable()
            for character in configuration_id
        ):
            raise OrderCommitmentConflict(
                "ConfigurationID must be a nonblank identifier string."
            )
    if policy.source == "ApprovedOperatingModel":
        if not policy.approved or configuration_id is None or target > 100:
            raise OrderCommitmentConflict("Approved policy is inconsistent.")
    elif policy.source == "ReferenceFallback":
        if policy.approved or configuration_id is not None or target != 80.0:
            raise OrderCommitmentConflict(
                "Reference policy must be unapproved 80%."
            )
    else:
        raise OrderCommitmentConflict("Protection policy source is unsupported.")
    return {
        "TargetPercent": target,
        "Source": policy.source,
        "Approved": policy.approved,
        "ConfigurationID": configuration_id,
    }
