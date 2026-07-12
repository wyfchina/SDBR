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
from sdbr.planning_commitments import (
    create_demand_commitment,
    normalize_demand_commitment,
)
from sdbr.planning_reservations import (
    PlanningReservationWriteSet,
    prepare_reservation_confirmation,
)
from sdbr.planning_reservation_view import (
    ACTIVE_PLANNING_STATUSES,
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
PENDING_CAPACITY_RESERVATION_STATUSES = frozenset({
    "ActivePlanReservation",
    "HeldForPlanningError",
})

ACCEPTANCE_DECISIONS = frozenset(
    {
        "AcceptRequestedDate",
        "ConditionallyAcceptRequestedDate",
        "AcceptRecommendedDate",
        "ConditionallyAcceptRecommendedDate",
    }
)

ACCEPTANCE_ACTION_CONTEXT = {
    "AcceptRequestedDate": (
        "OnTime",
        "Feasible",
        "RequestedDateAssessment",
    ),
    "ConditionallyAcceptRequestedDate": (
        "OnTime",
        "SkippedPendingConfirmation",
        "RequestedDateAssessment",
    ),
    "AcceptRecommendedDate": (
        "LaterSafeDate",
        "Feasible",
        "EarliestSafeAssessment",
    ),
    "ConditionallyAcceptRecommendedDate": (
        "LaterSafeDate",
        "SkippedPendingConfirmation",
        "EarliestSafeAssessment",
    ),
}


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


def action_acknowledgement_requirements(
    *,
    action: str,
    requires_ccr_acknowledgement: bool,
    requires_material_acknowledgement: bool,
) -> dict[str, bool]:
    is_acceptance = action in ACCEPTANCE_DECISIONS
    return {
        "RequiresCcrAcknowledgement": (
            is_acceptance and requires_ccr_acknowledgement
        ),
        "RequiresMaterialAcknowledgement": (
            is_acceptance and requires_material_acknowledgement
        ),
    }


def build_order_commitment_recommendation(
    *,
    shadow_schedule: Mapping[str, object],
    material_assessment: Mapping[str, object],
    protection_policy: CcrProtectionPolicy,
) -> dict[str, object]:
    """Map frozen capacity/material evidence to a planner decision request."""
    capacity = shadow_schedule["Status"]
    material = material_assessment["Status"]
    selected = shadow_schedule.get("SelectedAssessment") or {}
    threshold_state = (
        "ReferenceFallback"
        if protection_policy.source == "ReferenceFallback"
        else "ApprovedExceeded"
        if bool(selected.get("ThresholdExceeded"))
        else "ApprovedWithin"
    )
    requires_ccr = threshold_state in {
        "ReferenceFallback",
        "ApprovedExceeded",
    }
    requires_material = material == "SkippedPendingConfirmation"

    if capacity == "NotAssessable":
        decision, actions = "DoNotRecommendAccept", ["Reevaluate", "Reject"]
    elif material == "EvidenceInsufficient":
        decision, actions = "MaterialEvidenceRequired", ["Reevaluate", "Reject"]
    elif material == "Shortage":
        decision, actions = "DoNotRecommendAccept", ["Reevaluate", "Reject"]
    elif capacity == "OnTime" and material == "Feasible":
        decision = (
            "RecommendAccept"
            if threshold_state == "ApprovedWithin"
            else "PlannerConfirmationRequired"
        )
        actions = ["AcceptRequestedDate", "Reevaluate", "Reject"]
    elif capacity == "OnTime" and material == "SkippedPendingConfirmation":
        decision = (
            "CapacityAcceptableMaterialPending"
            if threshold_state == "ApprovedWithin"
            else "PlannerConfirmationRequired"
        )
        actions = [
            "ConditionallyAcceptRequestedDate",
            "Reevaluate",
            "Reject",
        ]
    elif capacity == "LaterSafeDate" and material == "Feasible":
        decision = (
            "RecommendLaterPromise"
            if threshold_state == "ApprovedWithin"
            else "PlannerConfirmationRequired"
        )
        actions = ["AcceptRecommendedDate", "Reevaluate", "Reject"]
    elif (
        capacity == "LaterSafeDate"
        and material == "SkippedPendingConfirmation"
    ):
        decision = (
            "RecommendLaterPromise"
            if threshold_state == "ApprovedWithin"
            else "PlannerConfirmationRequired"
        )
        actions = [
            "ConditionallyAcceptRecommendedDate",
            "Reevaluate",
            "Reject",
        ]
    else:
        raise OrderCommitmentConflict(
            f"Unsupported recommendation state: {capacity}/{material}."
        )

    return {
        "Decision": decision,
        "AllowedActions": actions,
        "ThresholdState": threshold_state,
        "RequiresPlannerDecision": True,
        "RequiresCcrAcknowledgement": requires_ccr,
        "RequiresMaterialAcknowledgement": requires_material,
        "ActionAcknowledgementRequirements": {
            action: action_acknowledgement_requirements(
                action=action,
                requires_ccr_acknowledgement=requires_ccr,
                requires_material_acknowledgement=requires_material,
            )
            for action in actions
        },
    }


CAPACITY_BASIS_FIELDS = (
    "CapacityReservationID", "ReservationBatchID", "DemandCommitmentID",
    "DemandClass", "ResourceID", "WindowStartAt", "WindowEndAt",
    "ReservedMinutes", "LatestAllowedCompletionAt", "Status",
    "RecordVersion",
)
MATERIAL_BASIS_FIELDS = (
    "MaterialAllocationID", "ReservationBatchID", "DemandCommitmentID",
    "DemandClass", "ItemID", "LocationID", "AllocatedQty",
    "MaterialSnapshotID", "Status", "RecordVersion",
)
CAPACITY_DECISION_WINDOW_FIELDS = (
    "RouteSequence", "OperationID", "ResourceID", "WindowStartAt",
    "WindowEndAt", "UsableWindowStartAt", "UsableWindowEndAt",
    "LatestAllowedCompletionAt", "CapacityMinutes",
    "UsableTemporalCapacityMinutes", "ScheduledLoadMinutes",
    "ScheduledLoadBeforeDeadlineMinutes", "ExistingReservationMinutes",
    "CandidateLoadMinutes", "LoadBeforeMinutes", "LoadAfterMinutes",
    "LoadAfterPercent", "AggregateRemainingMinutes",
    "TemporalRemainingMinutes", "LoadStatus", "ThresholdExceeded",
)
CAPACITY_DECISION_REQUEST_FIELDS = (
    "ReservationLineID", "OrderID", "OperationID", "ResourceID",
    "WindowStartAt", "WindowEndAt", "ReservedMinutes",
    "LatestAllowedCompletionAt",
)
MATERIAL_DECISION_REQUEST_FIELDS = (
    "RequirementLineID", "ItemID", "LocationID", "Uom",
    "AllocatedQty", "SupplySourceType", "MaterialSnapshotID",
)


def _basis_nonnegative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise OrderCommitmentConflict(f"{field} must be finite and non-negative.")
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0:
        raise OrderCommitmentConflict(f"{field} must be finite and non-negative.")
    return normalized


def _basis_record_version(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise OrderCommitmentConflict(f"{field} must be a positive integer.")
    return value


def build_order_commitment_basis(
    *,
    baseline_planning_run_id: str,
    baseline_operational_state_snapshot_id: str | None,
    baseline_schedule_fingerprint: str,
    master_data_version_id: str,
    operating_model_configuration_id: str | None,
    operating_model_fingerprint: str | None,
    scheduling_configuration_id: str | None,
    ddmrp_configuration_id: str | None,
    release_policy_version_id: str | None,
    frozen_release_policy_fingerprint: str,
    routing_fingerprint: str,
    calendar_fingerprint: str,
    time_buffer_minutes: int,
    material_check_window_minutes: int,
    capacity_assessment_cutoff_at: datetime,
    material_eligibility_cutoff_at: datetime | None,
    check_material_availability: bool,
    material_skip_reason: str | None,
    snapshot_selection: Mapping[str, object],
    relevant_capacity_window_keys: list[tuple[str, str, str]],
    capacity_ledger_rows: list[dict[str, object]],
    relevant_material_keys: list[tuple[str, str]],
    inventory_buffer_rows: list[InventoryBufferPolicy],
    material_availability_rows: list[MaterialAvailability],
    material_ledger_rows: list[dict[str, object]],
) -> dict[str, object]:
    selection = snapshot_selection
    capacity_keys = sorted({
        (
            str(resource_id),
            _parse_aware(start).isoformat(),
            _parse_aware(end).isoformat(),
        )
        for resource_id, start, end in relevant_capacity_window_keys
    })
    material_keys = sorted({
        (str(item_id), str(location_id))
        for item_id, location_id in relevant_material_keys
    })
    capacity_key_set = set(capacity_keys)
    relevant_capacity_resources = {key[0] for key in capacity_keys}
    material_key_set = set(material_keys)

    capacity_projection: list[dict[str, object]] = []
    seen_capacity_ids: set[str] = set()
    for raw in capacity_ledger_rows:
        if raw.get("Status") not in PENDING_CAPACITY_RESERVATION_STATUSES:
            continue
        resource_id = str(raw.get("ResourceID") or "")
        if resource_id not in relevant_capacity_resources:
            continue
        start = _parse_aware(raw.get("WindowStartAt"))
        end = _parse_aware(raw.get("WindowEndAt"))
        raw_key = (
            resource_id,
            start.isoformat(),
            end.isoformat(),
        )
        if raw_key not in capacity_key_set:
            continue
        capacity_id = _required_text(raw, "CapacityReservationID")
        if capacity_id in seen_capacity_ids:
            raise OrderCommitmentConflict(
                "Relevant capacity reservation ID is duplicated."
            )
        latest = _parse_aware(raw["LatestAllowedCompletionAt"])
        if end <= start or not start < latest <= end:
            raise OrderCommitmentConflict(
                "Relevant capacity reservation window is invalid."
            )
        projected = {field: deepcopy(raw.get(field)) for field in CAPACITY_BASIS_FIELDS}
        projected.update({
            "CapacityReservationID": capacity_id,
            "ReservationBatchID": _required_text(raw, "ReservationBatchID"),
            "DemandCommitmentID": _required_text(raw, "DemandCommitmentID"),
            "DemandClass": _required_text(raw, "DemandClass"),
            "ResourceID": raw_key[0],
            "WindowStartAt": start.isoformat(),
            "WindowEndAt": end.isoformat(),
            "ReservedMinutes": _positive_number(
                raw.get("ReservedMinutes"), "ReservedMinutes"
            ),
            "LatestAllowedCompletionAt": latest.isoformat(),
            "Status": _required_text(raw, "Status"),
            "RecordVersion": _basis_record_version(
                raw.get("RecordVersion"), "Capacity RecordVersion"
            ),
        })
        seen_capacity_ids.add(capacity_id)
        capacity_projection.append(projected)
    capacity_projection.sort(key=lambda row: str(row["CapacityReservationID"]))

    inventory_projection: list[dict[str, object]] = []
    seen_inventory_keys: set[tuple[str, str]] = set()
    for row in inventory_buffer_rows:
        key = (row.item_id, row.location_id)
        if key not in material_key_set:
            continue
        if key in seen_inventory_keys:
            raise OrderCommitmentConflict(
                "Relevant inventory-buffer evidence is duplicated."
            )
        seen_inventory_keys.add(key)
        inventory_projection.append({
            "ItemID": row.item_id,
            "LocationID": row.location_id,
            "OnHandQty": _basis_nonnegative(row.on_hand_qty, "OnHandQty"),
            "RedZoneQty": _basis_nonnegative(row.red_zone_qty, "RedZoneQty"),
            "YellowZoneQty": _basis_nonnegative(
                row.yellow_zone_qty, "YellowZoneQty"
            ),
            "GreenZoneQty": _basis_nonnegative(
                row.green_zone_qty, "GreenZoneQty"
            ),
        })
    inventory_projection.sort(
        key=lambda row: (str(row["ItemID"]), str(row["LocationID"]))
    )

    availability_projection: list[dict[str, object]] = []
    seen_availability_keys: set[tuple[str, str]] = set()
    for row in material_availability_rows:
        key = (row.item_id, row.location_id)
        if key not in material_key_set:
            continue
        if key in seen_availability_keys:
            raise OrderCommitmentConflict(
                "Relevant material-availability evidence is duplicated."
            )
        seen_availability_keys.add(key)
        availability_projection.append({
            "ItemID": row.item_id,
            "LocationID": row.location_id,
            "AllocatedQty": _basis_nonnegative(
                row.allocated_qty, "Authority AllocatedQty"
            ),
            "InboundQty": _basis_nonnegative(row.inbound_qty, "InboundQty"),
            "InboundAvailableAt": (
                _utc(row.inbound_available_at).isoformat()
                if row.inbound_available_at is not None
                else None
            ),
        })
    availability_projection.sort(
        key=lambda row: (str(row["ItemID"]), str(row["LocationID"]))
    )

    material_projection: list[dict[str, object]] = []
    seen_material_ids: set[str] = set()
    for raw in material_ledger_rows:
        if raw.get("Status") not in ACTIVE_PLANNING_STATUSES:
            continue
        raw_key = (
            str(raw.get("ItemID") or ""),
            str(raw.get("LocationID") or ""),
        )
        if raw_key not in material_key_set:
            continue
        allocation_id = _required_text(raw, "MaterialAllocationID")
        if allocation_id in seen_material_ids:
            raise OrderCommitmentConflict(
                "Relevant material allocation ID is duplicated."
            )
        projected = {field: deepcopy(raw.get(field)) for field in MATERIAL_BASIS_FIELDS}
        projected.update({
            "MaterialAllocationID": allocation_id,
            "ReservationBatchID": _required_text(raw, "ReservationBatchID"),
            "DemandCommitmentID": _required_text(raw, "DemandCommitmentID"),
            "DemandClass": _required_text(raw, "DemandClass"),
            "ItemID": raw_key[0],
            "LocationID": raw_key[1],
            "AllocatedQty": _basis_nonnegative(
                raw.get("AllocatedQty"), "AllocatedQty"
            ),
            "MaterialSnapshotID": _required_text(raw, "MaterialSnapshotID"),
            "Status": _required_text(raw, "Status"),
            "RecordVersion": _basis_record_version(
                raw.get("RecordVersion"), "Material RecordVersion"
            ),
        })
        seen_material_ids.add(allocation_id)
        material_projection.append(projected)
    material_projection.sort(key=lambda row: str(row["MaterialAllocationID"]))

    audit_basis = {
        "BaselinePlanningRunID": baseline_planning_run_id,
        "BaselineOperationalStateSnapshotID": baseline_operational_state_snapshot_id,
        "BaselineScheduleFingerprint": baseline_schedule_fingerprint,
        "MasterDataVersionID": master_data_version_id,
        "OperatingModelConfigurationID": operating_model_configuration_id,
        "OperatingModelFingerprint": operating_model_fingerprint,
        "SchedulingConfigurationID": scheduling_configuration_id,
        "DDMRPConfigurationID": ddmrp_configuration_id,
        "ReleasePolicyVersionID": release_policy_version_id,
        "FrozenReleasePolicyFingerprint": frozen_release_policy_fingerprint,
        "RoutingFingerprint": routing_fingerprint,
        "CalendarFingerprint": calendar_fingerprint,
        "TimeBufferMinutes": time_buffer_minutes,
        "MaterialCheckWindowMinutes": material_check_window_minutes,
        "CapacityAssessmentCutoffAt": _utc_iso(capacity_assessment_cutoff_at),
        "MaterialEligibilityCutoffAt": (
            _utc_iso(material_eligibility_cutoff_at)
            if material_eligibility_cutoff_at is not None
            else None
        ),
        "SelectedOperationalStateSnapshotID": selection[
            "OperationalStateSnapshotID"
        ],
        "SelectedOperationalStateCapturedAt": selection[
            "OperationalStateCapturedAt"
        ],
        "OperationalStateFreshnessStatus": selection[
            "OperationalStateFreshnessStatus"
        ],
        "OperationalStateAgeMinutes": selection["OperationalStateAgeMinutes"],
        "OperationalStateMaxAgeMinutes": 60,
        "OperationalStateValidThroughAt": selection[
            "OperationalStateValidThroughAt"
        ],
        "RelevantCapacityWindowKeys": capacity_keys,
        "RelevantCapacityLedger": capacity_projection,
        "RelevantMaterialKeys": material_keys,
        "RelevantInventoryBuffers": inventory_projection,
        "RelevantMaterialAvailability": availability_projection,
        "RelevantMaterialLedger": material_projection,
    }
    audit_fingerprint_projection = deepcopy(audit_basis)
    audit_fingerprint_projection.pop("OperationalStateAgeMinutes", None)
    capacity_decision_basis = {
        key: deepcopy(audit_basis[key])
        for key in (
            "BaselinePlanningRunID",
            "BaselineScheduleFingerprint",
            "MasterDataVersionID",
            "OperatingModelConfigurationID",
            "OperatingModelFingerprint",
            "SchedulingConfigurationID",
            "DDMRPConfigurationID",
            "ReleasePolicyVersionID",
            "FrozenReleasePolicyFingerprint",
            "RoutingFingerprint",
            "CalendarFingerprint",
            "TimeBufferMinutes",
            "RelevantCapacityWindowKeys",
            "RelevantCapacityLedger",
        )
    }
    decision_staleness_basis = {
        **capacity_decision_basis,
        "MaterialPolicy": {
            "CheckEnabled": bool(check_material_availability),
            "SkipReason": material_skip_reason,
            "MaterialCheckWindowMinutes": material_check_window_minutes,
        },
    }
    if check_material_availability:
        decision_staleness_basis.update({
            "SelectedOperationalStateSnapshotID": audit_basis[
                "SelectedOperationalStateSnapshotID"
            ],
            "SelectedOperationalStateCapturedAt": audit_basis[
                "SelectedOperationalStateCapturedAt"
            ],
            "OperationalStateFreshnessStatus": audit_basis[
                "OperationalStateFreshnessStatus"
            ],
            "OperationalStateValidThroughAt": audit_basis[
                "OperationalStateValidThroughAt"
            ],
            "RelevantMaterialKeys": material_keys,
            "RelevantInventoryBuffers": inventory_projection,
            "RelevantMaterialAvailability": availability_projection,
            "RelevantMaterialLedger": material_projection,
        })
    return {
        **audit_basis,
        "AuditBasisFingerprint": canonical_fingerprint(audit_fingerprint_projection),
        "DecisionStalenessBasis": decision_staleness_basis,
        "DecisionStalenessBasisFingerprint": canonical_fingerprint(
            decision_staleness_basis
        ),
    }


def canonical_order_commitment_decision_facts(
    evaluation: Mapping[str, object],
) -> dict[str, object]:
    shadow = dict(evaluation["ShadowSchedule"])
    material = dict(evaluation["MaterialAssessment"])
    recommendation = dict(evaluation["Recommendation"])
    candidate_key = {
        "OnTime": "RequestedDateAssessment",
        "LaterSafeDate": "EarliestSafeAssessment",
    }.get(str(shadow["Status"]))
    candidate = (
        dict(shadow[candidate_key])
        if candidate_key is not None
        and isinstance(shadow.get(candidate_key), Mapping)
        else {}
    )
    actions = list(recommendation["AllowedActions"])
    return {
        "CapacityStatus": shadow["Status"],
        "SelectedCandidateKey": candidate_key,
        "SelectedPromiseAt": candidate.get("PromiseAt"),
        "CapacityWindowAssessments": sorted(
            [
                {field: row.get(field) for field in CAPACITY_DECISION_WINDOW_FIELDS}
                for row in candidate.get("WindowAssessments", [])
            ],
            key=lambda row: (
                int(row["RouteSequence"]),
                str(row["OperationID"]),
                str(row["WindowStartAt"]),
            ),
        ),
        "CapacityReservationRequests": sorted(
            [
                {field: row.get(field) for field in CAPACITY_DECISION_REQUEST_FIELDS}
                for row in candidate.get("ReservationRequests", [])
            ],
            key=lambda row: str(row["ReservationLineID"]),
        ),
        "MaterialStatus": material["Status"],
        "MaterialAllocationRequests": sorted(
            [
                {field: row.get(field) for field in MATERIAL_DECISION_REQUEST_FIELDS}
                for row in material.get("AllocationRequests", [])
            ],
            key=lambda row: str(row["RequirementLineID"]),
        ),
        "Recommendation": recommendation["Decision"],
        "ThresholdState": recommendation["ThresholdState"],
        "AllowedActions": actions,
        "ActionAcknowledgementRequirements": {
            action: action_acknowledgement_requirements(
                action=action,
                requires_ccr_acknowledgement=bool(
                    recommendation["RequiresCcrAcknowledgement"]
                ),
                requires_material_acknowledgement=bool(
                    recommendation["RequiresMaterialAcknowledgement"]
                ),
            )
            for action in actions
        },
    }


def create_order_commitment_evaluation(
    *,
    order: Mapping[str, object],
    shadow_schedule: Mapping[str, object],
    material_assessment: Mapping[str, object],
    basis: Mapping[str, object],
    protection_policy: CcrProtectionPolicy,
    evaluated_at: datetime,
) -> dict[str, object]:
    evaluated_at = _utc(require_aware(evaluated_at, "evaluated_at"))
    policy = normalized_policy_dict(protection_policy)
    identity = {
        "OrderContentFingerprint": order["OrderContentFingerprint"],
        "AuditBasisFingerprint": basis["AuditBasisFingerprint"],
        "DecisionStalenessBasisFingerprint": basis[
            "DecisionStalenessBasisFingerprint"
        ],
        "CapacityAssessmentCutoffAt": basis["CapacityAssessmentCutoffAt"],
        "MaterialEligibilityCutoffAt": basis["MaterialEligibilityCutoffAt"],
        "MaterialPolicy": {
            "CheckEnabled": material_assessment["CheckEnabled"],
            "SkipReason": material_assessment.get("SkipReason"),
            "MaterialCheckWindowMinutes": material_assessment[
                "MaterialCheckWindowMinutes"
            ],
            "SnapshotSelectionMode": material_assessment["SnapshotSelectionMode"],
            "RequestedOperationalStateSnapshotID": material_assessment.get(
                "RequestedOperationalStateSnapshotID"
            ),
        },
        "ProtectionPolicy": policy,
        "ShadowAlgorithm": deepcopy(shadow_schedule["Algorithm"]),
    }
    evaluation_id = "OCE-" + sha256(
        canonical_json(identity).encode("utf-8")
    ).hexdigest()[:20]
    immutable = {
        "EvaluationID": evaluation_id,
        "Order": deepcopy(order),
        "LogicalOrderKey": order["LogicalOrderKey"],
        "OrderContentFingerprint": order["OrderContentFingerprint"],
        "Basis": deepcopy(basis),
        "AuditBasisFingerprint": basis["AuditBasisFingerprint"],
        "DecisionStalenessBasisFingerprint": basis[
            "DecisionStalenessBasisFingerprint"
        ],
        "ProtectionPolicy": policy,
        "ShadowSchedule": deepcopy(shadow_schedule),
        "MaterialAssessment": deepcopy(material_assessment),
        "Recommendation": build_order_commitment_recommendation(
            shadow_schedule=shadow_schedule,
            material_assessment=material_assessment,
            protection_policy=protection_policy,
        ),
    }
    immutable["DecisionFacts"] = canonical_order_commitment_decision_facts(immutable)
    immutable["DecisionFactsFingerprint"] = canonical_fingerprint(
        immutable["DecisionFacts"]
    )
    fingerprint_projection = deepcopy(immutable)
    fingerprint_projection["Basis"].pop("OperationalStateAgeMinutes", None)
    fingerprint_projection["MaterialAssessment"].pop(
        "OperationalStateAgeMinutes", None
    )
    evaluation_fingerprint = canonical_fingerprint(fingerprint_projection)
    return {
        **immutable,
        "EvaluationFingerprint": evaluation_fingerprint,
        "EvaluatedAt": _utc_iso(evaluated_at),
        "CreatedAt": _utc_iso(evaluated_at),
        "Status": "AwaitingPlannerDecision",
        "RecordVersion": 1,
    }


def register_order_commitment_evaluation(
    evaluations: Mapping[str, dict[str, object]],
    candidate: dict[str, object],
) -> tuple[Literal["Created", "Duplicate"], dict[str, object]]:
    evaluation_id = _required_text(candidate, "EvaluationID")
    fingerprint = _required_text(candidate, "EvaluationFingerprint")
    existing = evaluations.get(evaluation_id)
    if existing is None:
        return "Created", deepcopy(candidate)
    if existing.get("EvaluationFingerprint") == fingerprint:
        return "Duplicate", deepcopy(existing)
    raise OrderCommitmentConflict(
        "Evaluation ID already exists with different canonical content."
    )


def exact_order_commitment_intake_replay(
    *,
    evaluations: Mapping[str, dict[str, object]],
    order: Mapping[str, object],
) -> dict[str, object] | None:
    logical_rows = [
        row for row in evaluations.values()
        if row.get("LogicalOrderKey") == order["LogicalOrderKey"]
    ]
    exact = next(
        (
            row for row in logical_rows
            if row.get("OrderContentFingerprint") == order["OrderContentFingerprint"]
        ),
        None,
    )
    if exact is not None:
        return deepcopy(exact)
    if any(
        row.get("Order", {}).get("OrderKey") == order["OrderKey"]
        for row in logical_rows
    ):
        raise OrderCommitmentConflict("OrderVersionContentConflict")
    if any(
        row.get("Status") == "AcceptedPendingFormalSchedule"
        for row in logical_rows
    ):
        raise OrderCommitmentConflict(
            "AcceptedOrderVersionChangeRequiresExplicitAmendment"
        )
    if logical_rows:
        greatest_rank = max(
            tuple(row["Order"]["OrderVersionRank"])
            for row in logical_rows
        )
        if tuple(order["OrderVersionRank"]) < greatest_rank:
            raise OrderCommitmentConflict("OrderVersionSuperseded")
    return None


def supersede_open_order_commitment_evaluations(
    *,
    evaluations: Mapping[str, dict[str, object]],
    candidate: Mapping[str, object],
    superseded_at: datetime,
) -> dict[str, dict[str, object]]:
    updates: dict[str, dict[str, object]] = {}
    for evaluation_id, row in evaluations.items():
        if (
            row.get("LogicalOrderKey") != candidate["LogicalOrderKey"]
            or row.get("Status") != "AwaitingPlannerDecision"
            or evaluation_id == candidate["EvaluationID"]
        ):
            continue
        updated = deepcopy(row)
        updated["Status"] = "Superseded"
        updated["SupersededAt"] = _utc_iso(superseded_at)
        updated["SupersededByEvaluationID"] = candidate["EvaluationID"]
        updated["RecordVersion"] = int(row["RecordVersion"]) + 1
        updates[evaluation_id] = updated
    return updates


def _decision_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrderCommitmentConflict(f"{field} is required.")
    return value.strip()


def prepare_mto_acceptance(
    *,
    evaluation: Mapping[str, object],
    existing_commitments: Mapping[str, dict[str, object]],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> PlanningReservationWriteSet:
    normalized_decision_id = _decision_text(decision_id, "DecisionID")
    normalized_actor = _decision_text(decided_by, "DecidedBy")
    _decision_text(reason, "Reason")
    decided_at = _utc(require_aware(decided_at, "DecidedAt"))
    if evaluation["Status"] != "AwaitingPlannerDecision":
        raise OrderCommitmentConflict("Evaluation is not decision-eligible.")
    context = ACCEPTANCE_ACTION_CONTEXT.get(decision)
    if (
        context is None
        or decision not in evaluation["Recommendation"]["AllowedActions"]
    ):
        raise OrderCommitmentConflict("Decision is not allowed.")
    capacity_status, material_status, candidate_key = context
    if evaluation["ShadowSchedule"]["Status"] != capacity_status:
        raise OrderCommitmentConflict("Decision capacity context does not match.")
    if evaluation["MaterialAssessment"]["Status"] != material_status:
        raise OrderCommitmentConflict("Decision material context does not match.")
    requirements = action_acknowledgement_requirements(
        action=decision,
        requires_ccr_acknowledgement=bool(
            evaluation["Recommendation"]["RequiresCcrAcknowledgement"]
        ),
        requires_material_acknowledgement=bool(
            evaluation["Recommendation"]["RequiresMaterialAcknowledgement"]
        ),
    )
    if requirements["RequiresCcrAcknowledgement"] and not ccr_risk_acknowledged:
        raise OrderCommitmentConflict("CCR risk acknowledgement is required.")
    if (
        requirements["RequiresMaterialAcknowledgement"]
        and not material_risk_acknowledged
    ):
        raise OrderCommitmentConflict("Material risk acknowledgement is required.")
    candidate = evaluation["ShadowSchedule"].get(candidate_key)
    if not isinstance(candidate, Mapping):
        raise OrderCommitmentConflict("Selected capacity assessment is missing.")
    accepted_promise_at = _parse_aware(candidate["PromiseAt"])
    for row in candidate.get("ReservationRequests", []):
        if _parse_aware(row["LatestAllowedCompletionAt"]) <= decided_at:
            raise OrderCommitmentConflict("Selected reservation window has expired.")

    order = evaluation["Order"]
    demand = create_demand_commitment(
        demand_source_type="MTOCustomerOrder",
        source_system=order["SourceSystem"],
        source_object_type=order["SourceObjectType"],
        source_object_id=order["OrderID"],
        source_object_version=order["OrderVersion"],
        demand_line_id=order["DemandLineID"],
        item_or_product_id=order["ProductID"],
        location_id=order["LocationID"],
        quantity=order["Quantity"],
        uom=order["Uom"],
        required_at=accepted_promise_at,
        demand_class="MTO",
        trace_id=order["TraceID"],
    )
    demand.update({
        "OrderCommitmentEvaluationID": evaluation["EvaluationID"],
        "BaselinePlanningRunID": evaluation["Basis"]["BaselinePlanningRunID"],
        "OperatingModelConfigurationID": evaluation["Basis"][
            "OperatingModelConfigurationID"
        ],
        "OperatingModelFingerprint": evaluation["Basis"][
            "OperatingModelFingerprint"
        ],
        "SchedulingConfigurationID": evaluation["Basis"][
            "SchedulingConfigurationID"
        ],
        "DDMRPConfigurationID": evaluation["Basis"]["DDMRPConfigurationID"],
        "ReleasePolicyVersionID": evaluation["Basis"][
            "ReleasePolicyVersionID"
        ],
        "RoutingID": order["RoutingID"],
        "BusinessPriority": order["BusinessPriority"],
        "AcceptedPromiseAt": accepted_promise_at.isoformat(),
        "MaterialCommitmentStatus": (
            "PlannedAllocationPrepared"
            if material_status == "Feasible"
            else "PendingConfirmation"
        ),
        "PendingMaterialRequirements": (
            []
            if material_status == "Feasible"
            else deepcopy(evaluation["MaterialAssessment"]["PendingRequirements"])
        ),
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    })
    demand = normalize_demand_commitment(demand)
    material_requests = (
        evaluation["MaterialAssessment"]["AllocationRequests"]
        if material_status == "Feasible"
        else []
    )
    return prepare_reservation_confirmation(
        demand_commitment=demand,
        existing_commitments=existing_commitments,
        confirmation_id=normalized_decision_id,
        confirmed_by=normalized_actor,
        confirmed_at=decided_at,
        capacity_requests=candidate.get("ReservationRequests", []),
        material_requests=material_requests,
    )


def canonical_decision_fingerprint(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    actor_id: str,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> str:
    identity = {
        "DecisionID": _decision_text(decision_id, "DecisionID"),
        "EvaluationID": evaluation["EvaluationID"],
        "EvaluationFingerprint": evaluation["EvaluationFingerprint"],
        "Decision": _decision_text(decision, "Decision"),
        "ActorID": _decision_text(actor_id, "ActorID"),
        "Reason": _decision_text(reason, "Reason"),
        "CcrRiskAcknowledged": bool(ccr_risk_acknowledged),
        "MaterialRiskAcknowledged": bool(material_risk_acknowledged),
    }
    return canonical_fingerprint(identity)


def _decision_evidence(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
    normalized_decision_id = _decision_text(decision_id, "DecisionID")
    normalized_actor = _decision_text(decided_by, "DecidedBy")
    normalized_reason = _decision_text(reason, "Reason")
    decided_at = _utc(require_aware(decided_at, "DecidedAt"))
    return {
        "DecisionID": normalized_decision_id,
        "DecisionFingerprint": canonical_decision_fingerprint(
            evaluation=evaluation,
            decision_id=normalized_decision_id,
            decision=decision,
            actor_id=normalized_actor,
            reason=normalized_reason,
            ccr_risk_acknowledged=ccr_risk_acknowledged,
            material_risk_acknowledged=material_risk_acknowledged,
        ),
        "Decision": decision,
        "DecidedBy": normalized_actor,
        "DecidedAt": decided_at.isoformat(),
        "Reason": normalized_reason,
        "CcrRiskAcknowledged": bool(ccr_risk_acknowledged),
        "MaterialRiskAcknowledged": bool(material_risk_acknowledged),
    }


def accepted_evaluation_record(
    *,
    evaluation: Mapping[str, object],
    write_set: PlanningReservationWriteSet,
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
    if evaluation["Status"] != "AwaitingPlannerDecision":
        raise OrderCommitmentConflict("Evaluation is not decision-eligible.")
    if decision not in ACCEPTANCE_ACTION_CONTEXT:
        raise OrderCommitmentConflict("Decision is not an acceptance action.")
    updated = deepcopy(dict(evaluation))
    evidence = _decision_evidence(
        evaluation=evaluation,
        decision_id=decision_id,
        decision=decision,
        decided_by=decided_by,
        decided_at=decided_at,
        reason=reason,
        ccr_risk_acknowledged=ccr_risk_acknowledged,
        material_risk_acknowledged=material_risk_acknowledged,
    )
    evidence.update({
        "AcceptedPromiseAt": write_set.demand_commitment["AcceptedPromiseAt"],
        "DemandCommitmentID": write_set.demand_commitment["DemandCommitmentID"],
        "ReservationBatchID": write_set.batch["ReservationBatchID"],
        "ExternalOrderAcceptance": "NotPerformed",
        "PlanningRunCreation": "NotPerformed",
        "ProductionMutation": "NotPerformed",
    })
    updated["Decision"] = evidence
    updated["Status"] = "AcceptedPendingFormalSchedule"
    updated["RecordVersion"] = int(evaluation["RecordVersion"]) + 1
    return updated


def rejected_evaluation_record(
    *,
    evaluation: Mapping[str, object],
    decision_id: str,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    reason: str,
    ccr_risk_acknowledged: bool,
    material_risk_acknowledged: bool,
) -> dict[str, object]:
    if (
        evaluation["Status"] != "AwaitingPlannerDecision"
        or decision != "Reject"
        or decision not in evaluation["Recommendation"]["AllowedActions"]
    ):
        raise OrderCommitmentConflict("Rejection is not allowed.")
    updated = deepcopy(dict(evaluation))
    updated["Decision"] = _decision_evidence(
        evaluation=evaluation,
        decision_id=decision_id,
        decision=decision,
        decided_by=decided_by,
        decided_at=decided_at,
        reason=reason,
        ccr_risk_acknowledged=ccr_risk_acknowledged,
        material_risk_acknowledged=material_risk_acknowledged,
    )
    updated["Status"] = "Rejected"
    updated["RecordVersion"] = int(evaluation["RecordVersion"]) + 1
    return updated
