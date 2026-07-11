from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import ceil, floor, isfinite
from numbers import Real

from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.planning_reservation_view import ACTIVE_PLANNING_STATUSES
from sdbr.scheduling_solver import CapacityBucket, SetupTransition
from sdbr.sdbr_market_control import classify_ccr_load


SHADOW_ALGORITHM = {
    "Mode": "CCRFirstShadowScheduleV1",
    "Version": 1,
    "CapacitySemantics": "FormalBucketAggregateDeadlineTruncatedV1",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Shadow schedule datetimes must be timezone-aware.")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _utc(value).isoformat()


def _positive_real(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"Shadow schedule {field} must be finite and positive.")
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(f"Shadow schedule {field} must be finite and positive.")
    return normalized


def _validate_shadow_request(
    *,
    order_id: str,
    quantity: object,
    requested_due_at: datetime,
    evaluated_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> None:
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("Shadow schedule order_id must be non-empty.")
    _positive_real(quantity, "quantity")
    _utc(requested_due_at)
    _utc(evaluated_at)
    if (
        isinstance(downstream_protection_minutes, bool)
        or not isinstance(downstream_protection_minutes, int)
        or downstream_protection_minutes < 0
    ):
        raise ValueError("Shadow schedule protection must be non-negative.")
    threshold = _positive_real(
        protection_threshold_percent,
        "protection threshold",
    )
    if threshold > 100:
        raise ValueError("Shadow schedule threshold must be in (0, 100].")


def _issue(code: str, *entity_ids: str) -> dict[str, object]:
    return {"Code": code, "EntityIDs": list(entity_ids)}


def _unique_resources(resources: list[Resource]) -> dict[str, Resource]:
    result: dict[str, Resource] = {}
    for resource in resources:
        resource_id = resource.resource_id.strip()
        if not resource_id or resource_id in result:
            raise ValueError("Shadow resources require unique non-empty IDs.")
        if resource.capacity_units <= 0 or resource.efficiency_percent <= 0:
            raise ValueError("Shadow resource capacity and efficiency must be positive.")
        result[resource_id] = resource
    return result


def _extract_route_operations(
    *,
    order_id: str,
    quantity: float,
    routing: Routing | None,
    resources: list[Resource],
    setup_transitions: list[SetupTransition],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if routing is None:
        return [], [], [_issue("ROUTING_NOT_FOUND")]
    resources_by_id = _unique_resources(resources)
    ordered = sorted(routing.operations, key=lambda row: row.sequence)
    operation_ids = [row.operation_id.strip() for row in ordered]
    sequences = [row.sequence for row in ordered]
    if (
        any(not item for item in operation_ids)
        or len(operation_ids) != len(set(operation_ids))
        or len(sequences) != len(set(sequences))
    ):
        raise ValueError("Route operations require unique IDs and sequences.")
    all_operations: list[dict[str, object]] = []
    ccr_operations: list[dict[str, object]] = []
    for operation in ordered:
        resource = resources_by_id.get(operation.resource_id)
        if resource is None:
            return [], [], [_issue("RESOURCE_NOT_FOUND", operation.operation_id)]
        base_duration = int(
            _positive_real(operation.duration_minutes, "duration")
            * _positive_real(quantity, "quantity")
        )
        effective_duration = max(
            1,
            ceil(base_duration * 100 / resource.efficiency_percent),
        )
        record = {
            "RouteSequence": operation.sequence,
            "OperationID": f"{order_id.strip()}:{operation.operation_id.strip()}",
            "SourceOperationID": operation.operation_id.strip(),
            "ResourceID": resource.resource_id,
            "DurationMinutes": effective_duration,
            "AlternateResourceIDs": sorted(operation.alternate_resource_ids or []),
            "IsPrimaryCcr": resource.is_constraint,
        }
        all_operations.append(record)
        if not resource.is_constraint:
            continue
        target_family = operation.setup_family or routing.product_id
        unresolved_setup = any(
            transition.resource_id == resource.resource_id
            and transition.to_family == target_family
            and transition.setup_minutes > 0
            for transition in setup_transitions
        )
        if unresolved_setup:
            return [], [], [
                _issue(
                    "CCR_SETUP_LOAD_REQUIRES_REVIEW",
                    operation.operation_id,
                    resource.resource_id,
                )
            ]
        ccr_operations.append(record)
    if not ccr_operations:
        return all_operations, [], [_issue("CCR_OPERATION_NOT_FOUND")]
    return all_operations, ccr_operations, []
