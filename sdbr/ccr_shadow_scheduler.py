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


def _floor_minutes(value: timedelta) -> int:
    return floor(value.total_seconds() / 60)


def _overlap_minutes(
    intervals: list[tuple[datetime, datetime]],
    start: datetime,
    end: datetime,
) -> int:
    return sum(
        max(0, _floor_minutes(min(item_end, end) - max(item_start, start)))
        for item_start, item_end in intervals
    )


def _window_metrics(
    state: Mapping[str, object],
    *,
    usable_start: datetime,
    deadline: datetime,
    candidate_minutes: int,
) -> dict[str, object]:
    window_start = state["WindowStart"]
    window_end = state["WindowEnd"]
    assert isinstance(window_start, datetime)
    assert isinstance(window_end, datetime)
    usable_start = max(window_start, usable_start)
    usable_end = min(window_end, deadline)
    if usable_end <= usable_start:
        return {"Fits": False, "Reason": "NO_USABLE_WINDOW"}
    assignments = list(state["CandidateAssignments"])
    candidate_full = sum(int(row["Minutes"]) for row in assignments)
    candidate_before_deadline = sum(
        int(row["Minutes"])
        for row in assignments
        if row["LatestAllowedCompletionAt"] <= usable_end
    )
    scheduled_full = int(state["ScheduledFullMinutes"])
    existing = int(state["ExistingReservationMinutes"])
    aggregate_before = scheduled_full + existing + candidate_full
    intervals = list(state["ProcessingIntervals"])
    scheduled_usable = _overlap_minutes(intervals, usable_start, usable_end)
    temporal_before = scheduled_usable + existing + candidate_before_deadline
    capacity_minutes = int(state["CapacityMinutes"])
    temporal_capacity = (
        _floor_minutes(usable_end - usable_start)
        * int(state["CapacityUnits"])
    )
    aggregate_remaining = capacity_minutes - aggregate_before
    temporal_remaining = temporal_capacity - temporal_before
    load_after = aggregate_before + candidate_minutes
    load_percent = round(load_after / capacity_minutes * 100, 2)
    return {
        "Fits": candidate_minutes <= min(
            aggregate_remaining,
            temporal_remaining,
        ),
        "WindowStartAt": _utc_iso(window_start),
        "WindowEndAt": _utc_iso(window_end),
        "UsableWindowStartAt": _utc_iso(usable_start),
        "UsableWindowEndAt": _utc_iso(usable_end),
        "LatestAllowedCompletionAt": _utc_iso(usable_end),
        "CapacityMinutes": capacity_minutes,
        "UsableTemporalCapacityMinutes": temporal_capacity,
        "ScheduledLoadMinutes": scheduled_full,
        "ScheduledLoadBeforeDeadlineMinutes": scheduled_usable,
        "ExistingReservationMinutes": existing,
        "CandidateLoadMinutes": candidate_minutes,
        "LoadBeforeMinutes": aggregate_before,
        "LoadAfterMinutes": load_after,
        "LoadAfterPercent": load_percent,
        "AggregateRemainingMinutes": aggregate_remaining,
        "TemporalRemainingMinutes": temporal_remaining,
    }


def _commit_candidate(
    state: dict[str, object],
    *,
    minutes: int,
    latest_allowed_completion_at: datetime,
) -> None:
    assignments = list(state["CandidateAssignments"])
    assignments.append(
        {
            "Minutes": minutes,
            "LatestAllowedCompletionAt": latest_allowed_completion_at,
        }
    )
    state["CandidateAssignments"] = assignments


def _reservation_request(
    *,
    order_id: str,
    operation: Mapping[str, object],
    state: Mapping[str, object],
    operation_deadline: datetime,
) -> dict[str, object]:
    window_start = state["WindowStart"]
    window_end = state["WindowEnd"]
    assert isinstance(window_start, datetime)
    assert isinstance(window_end, datetime)
    latest = min(window_end, operation_deadline)
    if not window_start < latest <= window_end:
        raise ValueError("Reservation deadline must be inside its exact window.")
    return {
        "ReservationLineID": (
            f"{operation['OperationID']}:{_utc_iso(window_start)}"
        ),
        "OrderID": order_id,
        "OperationID": operation["OperationID"],
        "ResourceID": operation["ResourceID"],
        "WindowStartAt": _utc_iso(window_start),
        "WindowEndAt": _utc_iso(window_end),
        "ReservedMinutes": int(operation["DurationMinutes"]),
        "LatestAllowedCompletionAt": _utc_iso(latest),
    }
