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
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
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


def _parse_aware(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{field} must be an aware ISO datetime.") from error
    else:
        raise ValueError(f"{field} must be an aware ISO datetime.")
    return _utc(parsed)


def _build_window_states(
    *,
    resources: list[Resource],
    capacity_buckets: list[CapacityBucket],
    ccr_resource_ids: set[str],
    gantt_rows: list[dict[str, object]],
    active_capacity_reservations: list[dict[str, object]],
) -> dict[tuple[str, datetime, datetime], dict[str, object]]:
    resources_by_id = _unique_resources(resources)
    states: dict[tuple[str, datetime, datetime], dict[str, object]] = {}
    for bucket in capacity_buckets:
        if bucket.resource_id not in ccr_resource_ids:
            continue
        start = _utc(bucket.bucket_start)
        end = _utc(bucket.bucket_end)
        key = (bucket.resource_id, start, end)
        resource = resources_by_id.get(bucket.resource_id)
        if (
            resource is None
            or end <= start
            or bucket.capacity_minutes <= 0
            or key in states
        ):
            raise ValueError("CCR capacity buckets are malformed or duplicated.")
        states[key] = {
            "ResourceID": bucket.resource_id,
            "WindowStart": start,
            "WindowEnd": end,
            "CapacityMinutes": bucket.capacity_minutes,
            "CapacityUnits": resource.capacity_units,
            "ProcessingIntervals": [],
            "ScheduledFullMinutes": 0,
            "ExistingReservationMinutes": 0,
            "CandidateAssignments": [],
        }
    seen_bars: set[tuple[object, ...]] = set()
    for resource_row in gantt_rows:
        resource_id = str(resource_row.get("ResourceID") or "")
        if resource_id not in ccr_resource_ids:
            continue
        bars = resource_row.get("Bars")
        if not isinstance(bars, list):
            raise ValueError("Relevant Gantt row Bars must be a list.")
        for bar in bars:
            if not isinstance(bar, Mapping):
                raise ValueError("Relevant Gantt bars must be objects.")
            if bar.get("BarType") not in {None, "Processing"}:
                continue
            start = _parse_aware(bar.get("Start"), "Gantt Start")
            end = _parse_aware(bar.get("End"), "Gantt End")
            identity = (
                resource_id,
                bar.get("OrderID"),
                bar.get("OperationID"),
                start,
                end,
            )
            if end <= start or identity in seen_bars:
                raise ValueError("Relevant processing bars are malformed or duplicated.")
            seen_bars.add(identity)
            for key, state in states.items():
                if key[0] != resource_id or end <= key[1] or start >= key[2]:
                    continue
                state["ProcessingIntervals"].append((start, end))
                state["ScheduledFullMinutes"] += _overlap_minutes(
                    [(start, end)], key[1], key[2]
                )
    seen_reservations: set[str] = set()
    for row in active_capacity_reservations:
        if row.get("Status") not in ACTIVE_PLANNING_STATUSES:
            continue
        resource_id = str(row.get("ResourceID") or "")
        start = _parse_aware(row.get("WindowStartAt"), "WindowStartAt")
        end = _parse_aware(row.get("WindowEndAt"), "WindowEndAt")
        key = (resource_id, start, end)
        if key not in states:
            continue
        reservation_id = str(row.get("CapacityReservationID") or "").strip()
        latest = _parse_aware(
            row.get("LatestAllowedCompletionAt"),
            "LatestAllowedCompletionAt",
        )
        minutes = _positive_real(row.get("ReservedMinutes"), "reserved minutes")
        if (
            not reservation_id
            or reservation_id in seen_reservations
            or not start < latest <= end
        ):
            raise ValueError("Relevant capacity reservations are malformed or duplicated.")
        seen_reservations.add(reservation_id)
        states[key]["ExistingReservationMinutes"] += int(minutes)
    return states


def _route_deadlines(
    *,
    all_route_operations: list[dict[str, object]],
    requested_due_at: datetime,
    downstream_protection_minutes: int,
) -> dict[str, datetime]:
    cursor = requested_due_at - timedelta(
        minutes=downstream_protection_minutes
    )
    deadlines: dict[str, datetime] = {}
    for operation in reversed(all_route_operations):
        source_id = str(operation["SourceOperationID"])
        deadlines[source_id] = cursor
        cursor -= timedelta(minutes=int(operation["DurationMinutes"]))
    return deadlines


def _requested_candidate(
    *,
    order_id: str,
    requested_due_at: datetime,
    capacity_assessment_cutoff_at: datetime,
    ccr_operations: list[dict[str, object]],
    deadlines: Mapping[str, datetime],
    source_states: Mapping[
        tuple[str, datetime, datetime], dict[str, object]
    ],
    protection_threshold_percent: float,
) -> dict[str, object]:
    states = deepcopy(dict(source_states))
    assessments: list[dict[str, object]] = []
    requests: list[dict[str, object]] = []
    considered: set[tuple[str, str, str]] = set()
    cutoff = _utc(capacity_assessment_cutoff_at)
    for operation in reversed(ccr_operations):
        resource_id = str(operation["ResourceID"])
        deadline = deadlines[str(operation["SourceOperationID"])]
        fitting: list[tuple[dict[str, object], dict[str, object]]] = []
        for key, state in states.items():
            if (
                key[0] != resource_id
                or key[2] <= cutoff
                or key[1] >= deadline
            ):
                continue
            considered.add((key[0], _utc_iso(key[1]), _utc_iso(key[2])))
            metrics = _window_metrics(
                state,
                usable_start=max(key[1], cutoff),
                deadline=deadline,
                candidate_minutes=int(operation["DurationMinutes"]),
            )
            if metrics["Fits"]:
                fitting.append((state, metrics))
        selected = max(
            fitting,
            key=lambda item: (
                item[0]["WindowStart"], item[0]["WindowEnd"]
            ),
            default=None,
        )
        if selected is None:
            return {
                "Feasible": False,
                "PromiseAt": _utc_iso(requested_due_at),
                "WindowAssessments": [],
                "ReservationRequests": [],
                "ConsideredWindowKeys": sorted(considered),
            }
        state, metrics = selected
        latest = _parse_aware(
            metrics["LatestAllowedCompletionAt"],
            "LatestAllowedCompletionAt",
        )
        _commit_candidate(
            state,
            minutes=int(operation["DurationMinutes"]),
            latest_allowed_completion_at=latest,
        )
        assessments.append(
            {
                **metrics,
                "RouteSequence": operation["RouteSequence"],
                "OperationID": operation["OperationID"],
                "ResourceID": resource_id,
                "LoadStatus": classify_ccr_load(
                    load_percent=float(metrics["LoadAfterPercent"]),
                    protective_capacity_target_percent=(
                        protection_threshold_percent
                    ),
                ),
                "ThresholdExceeded": (
                    float(metrics["LoadAfterPercent"])
                    > protection_threshold_percent
                ),
            }
        )
        requests.append(
            _reservation_request(
                order_id=order_id,
                operation=operation,
                state=state,
                operation_deadline=deadline,
            )
        )
    return {
        "Feasible": True,
        "PromiseAt": _utc_iso(requested_due_at),
        "WindowAssessments": sorted(
            assessments, key=lambda row: int(row["RouteSequence"])
        ),
        "ReservationRequests": sorted(
            requests,
            key=lambda row: str(row["OperationID"]),
        ),
        "ConsideredWindowKeys": sorted(considered),
    }


def _earliest_safe_candidate(
    *,
    order_id: str,
    all_route_operations: list[dict[str, object]],
    source_states: Mapping[
        tuple[str, datetime, datetime], dict[str, object]
    ],
    capacity_assessment_cutoff_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> dict[str, object] | None:
    states = deepcopy(dict(source_states))
    cursor = capacity_assessment_cutoff_at
    assessments: list[dict[str, object]] = []
    requests: list[dict[str, object]] = []
    considered: set[tuple[str, str, str]] = set()
    for operation in sorted(
        all_route_operations,
        key=lambda row: int(row["RouteSequence"]),
    ):
        duration = int(operation["DurationMinutes"])
        if not bool(operation["IsPrimaryCcr"]):
            cursor += timedelta(minutes=duration)
            continue
        resource_id = str(operation["ResourceID"])
        fitting: list[tuple[dict[str, object], dict[str, object]]] = []
        for key, state in states.items():
            if key[0] != resource_id or key[2] <= cursor:
                continue
            considered.add((key[0], _utc_iso(key[1]), _utc_iso(key[2])))
            metrics = _window_metrics(
                state,
                usable_start=cursor,
                deadline=key[2],
                candidate_minutes=duration,
            )
            if metrics["Fits"]:
                fitting.append((state, metrics))
        selected = min(
            fitting,
            key=lambda item: (
                item[0]["WindowEnd"], item[0]["WindowStart"]
            ),
            default=None,
        )
        if selected is None:
            return None
        state, metrics = selected
        completion_at = state["WindowEnd"]
        assert isinstance(completion_at, datetime)
        _commit_candidate(
            state,
            minutes=duration,
            latest_allowed_completion_at=completion_at,
        )
        assessments.append(
            {
                **metrics,
                "RouteSequence": operation["RouteSequence"],
                "OperationID": operation["OperationID"],
                "ResourceID": resource_id,
                "LoadStatus": classify_ccr_load(
                    load_percent=float(metrics["LoadAfterPercent"]),
                    protective_capacity_target_percent=(
                        protection_threshold_percent
                    ),
                ),
                "ThresholdExceeded": (
                    float(metrics["LoadAfterPercent"])
                    > protection_threshold_percent
                ),
            }
        )
        requests.append(
            _reservation_request(
                order_id=order_id,
                operation=operation,
                state=state,
                operation_deadline=completion_at,
            )
        )
        cursor = completion_at
    return {
        "Feasible": True,
        "PromiseAt": _utc_iso(
            cursor + timedelta(minutes=downstream_protection_minutes)
        ),
        "WindowAssessments": assessments,
        "ReservationRequests": requests,
        "ConsideredWindowKeys": sorted(considered),
    }


def _not_assessable_result(
    *,
    requested_due_at: datetime,
    capacity_assessment_cutoff_at: datetime,
    issues: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "Algorithm": deepcopy(SHADOW_ALGORITHM),
        "Status": "NotAssessable",
        "CapacityAssessmentCutoffAt": _utc_iso(
            capacity_assessment_cutoff_at
        ),
        "RequestedDueAt": _utc_iso(requested_due_at),
        "LatestCcrCompletionAt": None,
        "RequestedDateAssessment": {"Feasible": False},
        "EarliestSafeAssessment": None,
        "SelectedAssessment": None,
        "RelevantCapacityWindowKeys": [],
        "Issues": deepcopy(issues),
        "Summary": {
            "CcrOperationCount": 0,
            "SelectedWindowCount": 0,
            "MaximumLoadAfterPercent": None,
        },
    }


def evaluate_ccr_shadow_schedule(
    *,
    order_id: str,
    quantity: float,
    routing: Routing | None,
    resources: list[Resource],
    capacity_buckets: list[CapacityBucket],
    setup_transitions: list[SetupTransition],
    gantt_rows: list[dict[str, object]],
    active_capacity_reservations: list[dict[str, object]],
    requested_due_at: datetime,
    evaluated_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> dict[str, object]:
    _validate_shadow_request(
        order_id=order_id,
        quantity=quantity,
        requested_due_at=requested_due_at,
        evaluated_at=evaluated_at,
        downstream_protection_minutes=downstream_protection_minutes,
        protection_threshold_percent=protection_threshold_percent,
    )
    requested_due_at = _utc(requested_due_at)
    cutoff = _utc(evaluated_at)
    all_operations, ccr_operations, issues = _extract_route_operations(
        order_id=order_id,
        quantity=quantity,
        routing=routing,
        resources=resources,
        setup_transitions=setup_transitions,
    )
    if issues:
        return _not_assessable_result(
            requested_due_at=requested_due_at,
            capacity_assessment_cutoff_at=cutoff,
            issues=issues,
        )
    try:
        states = _build_window_states(
            resources=resources,
            capacity_buckets=capacity_buckets,
            ccr_resource_ids={
                str(row["ResourceID"]) for row in ccr_operations
            },
            gantt_rows=gantt_rows,
            active_capacity_reservations=active_capacity_reservations,
        )
    except ValueError as error:
        return _not_assessable_result(
            requested_due_at=requested_due_at,
            capacity_assessment_cutoff_at=cutoff,
            issues=[_issue("CAPACITY_EVIDENCE_INVALID", str(error))],
        )
    deadlines = _route_deadlines(
        all_route_operations=all_operations,
        requested_due_at=requested_due_at,
        downstream_protection_minutes=downstream_protection_minutes,
    )
    requested = _requested_candidate(
        order_id=order_id,
        requested_due_at=requested_due_at,
        capacity_assessment_cutoff_at=cutoff,
        ccr_operations=ccr_operations,
        deadlines=deadlines,
        source_states=states,
        protection_threshold_percent=protection_threshold_percent,
    )
    earliest_safe = None
    status = "OnTime"
    selected = requested
    if not bool(requested["Feasible"]):
        earliest_safe = _earliest_safe_candidate(
            order_id=order_id,
            all_route_operations=all_operations,
            source_states=states,
            capacity_assessment_cutoff_at=cutoff,
            downstream_protection_minutes=downstream_protection_minutes,
            protection_threshold_percent=protection_threshold_percent,
        )
        if earliest_safe is None:
            return _not_assessable_result(
                requested_due_at=requested_due_at,
                capacity_assessment_cutoff_at=cutoff,
                issues=[_issue("NO_SAFE_CCR_WINDOW")],
            )
        status = "LaterSafeDate"
        selected = earliest_safe
    considered = {
        tuple(row)
        for assessment in (requested, earliest_safe)
        if isinstance(assessment, Mapping)
        for row in assessment.get("ConsideredWindowKeys", [])
    }
    window_rows = list(selected["WindowAssessments"])
    return {
        "Algorithm": deepcopy(SHADOW_ALGORITHM),
        "Status": status,
        "CapacityAssessmentCutoffAt": _utc_iso(cutoff),
        "RequestedDueAt": _utc_iso(requested_due_at),
        "LatestCcrCompletionAt": _utc_iso(
            requested_due_at
            - timedelta(minutes=downstream_protection_minutes)
        ),
        "RequestedDateAssessment": requested,
        "EarliestSafeAssessment": earliest_safe,
        "SelectedAssessment": selected,
        "RelevantCapacityWindowKeys": sorted(considered),
        "Issues": [],
        "Summary": {
            "CcrOperationCount": len(ccr_operations),
            "SelectedWindowCount": len(
                selected["ReservationRequests"]
            ),
            "MaximumLoadAfterPercent": max(
                (
                    float(row["LoadAfterPercent"])
                    for row in window_rows
                ),
                default=None,
            ),
        },
    }
