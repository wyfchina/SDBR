from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from numbers import Real
from typing import Literal

from sdbr.operational_state import (
    OperationalStateSnapshot,
    evaluate_operational_state_freshness,
)
from sdbr.planning_commitments import create_demand_commitment
from sdbr.planning_reservation_view import (
    planning_allocated_qty_for_other_demands,
)


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

ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES = 60


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


def select_order_commitment_operational_snapshot(
    *,
    snapshots: Mapping[str, OperationalStateSnapshot],
    evaluated_at: datetime,
    requested_snapshot_id: str | None,
) -> dict[str, object]:
    evaluated_at = _utc(require_aware(evaluated_at, "evaluated_at"))
    requested = (
        requested_snapshot_id.strip()
        if isinstance(requested_snapshot_id, str)
        and requested_snapshot_id.strip()
        else None
    )
    mode = "Explicit" if requested is not None else "LatestCurrent"
    if requested is not None:
        snapshot = snapshots.get(requested)
        if snapshot is None:
            raise OrderCommitmentSnapshotNotFound(requested)
    else:
        eligible = [
            row
            for row in snapshots.values()
            if row.captured_at <= evaluated_at
        ]
        snapshot = max(
            eligible,
            key=lambda row: (row.captured_at, row.snapshot_id),
            default=None,
        )
    if snapshot is None:
        return {
            "SnapshotSelectionMode": mode,
            "RequestedOperationalStateSnapshotID": requested,
            "OperationalStateSnapshot": None,
            "OperationalStateSnapshotID": None,
            "OperationalStateCapturedAt": None,
            "OperationalStateFreshnessStatus": "Missing",
            "OperationalStateAgeMinutes": None,
            "OperationalStateMaxAgeMinutes": (
                ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES
            ),
            "OperationalStateValidThroughAt": None,
            "Acceptable": False,
        }
    freshness = evaluate_operational_state_freshness(
        snapshot=snapshot,
        evaluated_at=evaluated_at,
        max_age_minutes=(
            ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES
        ),
    )
    return {
        "SnapshotSelectionMode": mode,
        "RequestedOperationalStateSnapshotID": requested,
        "OperationalStateSnapshot": snapshot,
        "OperationalStateSnapshotID": snapshot.snapshot_id,
        "OperationalStateCapturedAt": snapshot.captured_at.isoformat(),
        "OperationalStateFreshnessStatus": freshness.status,
        "OperationalStateAgeMinutes": freshness.age_minutes,
        "OperationalStateMaxAgeMinutes": freshness.max_age_minutes,
        "OperationalStateValidThroughAt": (
            snapshot.captured_at
            + timedelta(
                minutes=ORDER_COMMITMENT_OPERATIONAL_STATE_MAX_AGE_MINUTES
            )
        ).isoformat(),
        "Acceptable": freshness.acceptable,
    }


def _material_evidence_insufficient(
    *,
    evidence: Mapping[str, object],
    order: Mapping[str, object],
    code: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        **deepcopy(dict(evidence)),
        "Status": "EvidenceInsufficient",
        "Lines": [],
        "AllocationRequests": [],
        "PendingRequirements": deepcopy(order["MaterialRequirements"]),
        "Issues": [{"Code": code, **deepcopy(dict(details or {}))}],
    }


def evaluate_mto_material_availability(
    *,
    order: Mapping[str, object],
    snapshot_selection: Mapping[str, object],
    active_material_allocations: list[dict[str, object]],
    current_demand_commitment_id: str,
    evaluated_at: datetime,
    material_check_window_minutes: int,
    check_material_availability: bool = True,
    skip_reason: str | None = None,
) -> dict[str, object]:
    selection = snapshot_selection
    normalized_skip_reason = (
        skip_reason.strip()
        if isinstance(skip_reason, str) and skip_reason.strip()
        else None
    )
    if material_check_window_minutes < 0:
        raise OrderCommitmentConflict("Material check window cannot be negative.")
    material_cutoff = (
        _utc(evaluated_at)
        + timedelta(minutes=material_check_window_minutes)
        if check_material_availability
        else None
    )
    evidence = {
        "CheckEnabled": bool(check_material_availability),
        "SkipReason": normalized_skip_reason,
        "MaterialCheckWindowMinutes": material_check_window_minutes,
        "MaterialEligibilityCutoffAt": (
            material_cutoff.isoformat() if material_cutoff is not None else None
        ),
        "SnapshotSelectionMode": selection["SnapshotSelectionMode"],
        "RequestedOperationalStateSnapshotID": selection[
            "RequestedOperationalStateSnapshotID"
        ],
        "OperationalStateSnapshotID": selection[
            "OperationalStateSnapshotID"
        ],
        "OperationalStateCapturedAt": selection[
            "OperationalStateCapturedAt"
        ],
        "OperationalStateFreshnessStatus": selection[
            "OperationalStateFreshnessStatus"
        ],
        "OperationalStateAgeMinutes": selection[
            "OperationalStateAgeMinutes"
        ],
        "OperationalStateMaxAgeMinutes": 60,
        "OperationalStateValidThroughAt": selection[
            "OperationalStateValidThroughAt"
        ],
        "ReleaseGateStillRequired": True,
    }
    if not check_material_availability:
        if not normalized_skip_reason:
            raise OrderCommitmentConflict("Material check skip reason is required.")
        return {
            **evidence,
            "Status": "SkippedPendingConfirmation",
            "Lines": [],
            "AllocationRequests": [],
            "PendingRequirements": deepcopy(order["MaterialRequirements"]),
        }
    if not selection["Acceptable"]:
        return _material_evidence_insufficient(
            evidence=evidence,
            order=order,
            code="OPERATIONAL_STATE_EVIDENCE_NOT_FRESH",
            details={
                "FreshnessStatus": selection[
                    "OperationalStateFreshnessStatus"
                ]
            },
        )
    if not order["MaterialRequirements"]:
        return _material_evidence_insufficient(
            evidence=evidence,
            order=order,
            code="MATERIAL_REQUIREMENTS_MISSING",
        )
    snapshot = selection["OperationalStateSnapshot"]
    if snapshot is None or material_cutoff is None:
        return _material_evidence_insufficient(
            evidence=evidence,
            order=order,
            code="OPERATIONAL_STATE_EVIDENCE_MISSING",
        )
    requirements = sorted(
        deepcopy(order["MaterialRequirements"]),
        key=lambda row: (
            str(row["ItemID"]),
            str(row["LocationID"]),
            str(row["RequirementLineID"]),
        ),
    )
    relevant_keys = {
        (str(row["ItemID"]), str(row["LocationID"]))
        for row in requirements
    }
    relevant_allocations = [
        deepcopy(row)
        for row in active_material_allocations
        if (
            str(row.get("ItemID") or ""),
            str(row.get("LocationID") or ""),
        ) in relevant_keys
    ]
    buffers = {
        (row.item_id, row.location_id): row
        for row in snapshot.inventory_buffers
        if (row.item_id, row.location_id) in relevant_keys
    }
    availability_rows = {
        (row.item_id, row.location_id): row
        for row in snapshot.material_availability
        if (row.item_id, row.location_id) in relevant_keys
    }
    if set(buffers) != relevant_keys or set(availability_rows) != relevant_keys:
        return _material_evidence_insufficient(
            evidence=evidence,
            order=order,
            code="REQUIRED_MATERIAL_EVIDENCE_MISSING",
        )
    lines: list[dict[str, object]] = []
    allocation_requests: list[dict[str, object]] = []
    try:
        supply_by_key: dict[
            tuple[str, str], dict[str, float | str]
        ] = {}
        for key in sorted(relevant_keys):
            buffer = buffers[key]
            availability = availability_rows[key]
            inbound_at = availability.inbound_available_at
            if inbound_at is not None:
                inbound_at = _utc(inbound_at)
            eligible_inbound = (
                float(availability.inbound_qty)
                if inbound_at is not None and inbound_at <= material_cutoff
                else 0.0
            )
            other_planning = planning_allocated_qty_for_other_demands(
                allocations=relevant_allocations,
                item_id=key[0],
                location_id=key[1],
                current_demand_commitment_id=current_demand_commitment_id,
            )
            qualified = float(buffer.on_hand_qty) + eligible_inbound
            uncommitted = max(
                qualified
                - float(availability.allocated_qty)
                - other_planning,
                0.0,
            )
            supply_by_key[key] = {
                "OnHandQty": float(buffer.on_hand_qty),
                "EligibleInboundQty": eligible_inbound,
                "AuthorityAllocatedQty": float(availability.allocated_qty),
                "OtherPlanningAllocatedQty": other_planning,
                "QualifiedSupplyQty": qualified,
                "UncommittedAvailabilityQty": uncommitted,
                "SupplySourceType": (
                    "OnHandAndInbound" if eligible_inbound > 0 else "OnHand"
                ),
            }

        remaining_by_key = {
            key: float(row["UncommittedAvailabilityQty"])
            for key, row in supply_by_key.items()
        }
        for requirement in requirements:
            key = (
                str(requirement["ItemID"]),
                str(requirement["LocationID"]),
            )
            supply = supply_by_key[key]
            required = float(requirement["RequiredQty"])
            available_before_line = remaining_by_key[key]
            covered = available_before_line >= required
            if covered:
                remaining_by_key[key] = available_before_line - required
            lines.append(
                {
                    "RequirementLineID": requirement["RequirementLineID"],
                    "ItemID": key[0],
                    "LocationID": key[1],
                    "Uom": requirement["Uom"],
                    "RequiredQty": required,
                    "OnHandQty": supply["OnHandQty"],
                    "EligibleInboundQty": supply["EligibleInboundQty"],
                    "AuthorityAllocatedQty": supply[
                        "AuthorityAllocatedQty"
                    ],
                    "OtherPlanningAllocatedQty": supply[
                        "OtherPlanningAllocatedQty"
                    ],
                    "QualifiedSupplyQty": supply["QualifiedSupplyQty"],
                    "UncommittedAvailabilityQty": available_before_line,
                    "CoverageStatus": "Covered" if covered else "Shortage",
                }
            )
            if covered:
                allocation_requests.append(
                    {
                        "RequirementLineID": requirement[
                            "RequirementLineID"
                        ],
                        "ItemID": key[0],
                        "LocationID": key[1],
                        "Uom": requirement["Uom"],
                        "AllocatedQty": required,
                        "SupplySourceType": supply["SupplySourceType"],
                        "MaterialSnapshotID": selection[
                            "OperationalStateSnapshotID"
                        ],
                    }
                )
    except (TypeError, ValueError, OverflowError) as error:
        return _material_evidence_insufficient(
            evidence=evidence,
            order=order,
            code="MATERIAL_EVIDENCE_INVALID",
            details={"Message": str(error)},
        )
    if any(row["CoverageStatus"] == "Shortage" for row in lines):
        return {
            **evidence,
            "Status": "Shortage",
            "Lines": lines,
            "AllocationRequests": [],
            "PendingRequirements": deepcopy(requirements),
            "Issues": [],
        }
    return {
        **evidence,
        "Status": "Feasible",
        "Lines": lines,
        "AllocationRequests": allocation_requests,
        "PendingRequirements": [],
        "Issues": [],
    }
