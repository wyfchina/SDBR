from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sdbr.release_stability import (
    ReleaseStabilityInput,
    ReleaseStabilityPolicy,
    evaluate_release_stability,
)


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    order_id: str
    event_type: str
    event_at: datetime
    target_start_at: datetime
    exception_code: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionEventResult:
    accepted: bool
    status: str
    message: str
    requires_exception_code: bool
    requires_review: bool


@dataclass(frozen=True, slots=True)
class ExceptionCodeDefinition:
    code: str
    display_name: str
    category: str


def validate_execution_event(event: ExecutionEvent) -> ExecutionEventResult:
    if event.exception_code and event.exception_code not in default_exception_codes():
        return ExecutionEventResult(
            accepted=False,
            status="Rejected",
            message="Unknown exception code.",
            requires_exception_code=False,
            requires_review=False,
        )
    if _is_late_buffer_arrival(event) and not event.exception_code:
        return ExecutionEventResult(
            accepted=False,
            status="Rejected",
            message="Late buffer arrival requires an exception code.",
            requires_exception_code=True,
            requires_review=False,
        )
    if _is_late_buffer_arrival(event):
        return ExecutionEventResult(
            accepted=True,
            status="AcceptedWithException",
            message="Execution event recorded with exception code.",
            requires_exception_code=False,
            requires_review=True,
        )
    return ExecutionEventResult(
        accepted=True,
        status="Accepted",
        message="Execution event recorded.",
        requires_exception_code=False,
        requires_review=False,
    )


def _is_late_buffer_arrival(event: ExecutionEvent) -> bool:
    return event.event_type == "ArrivedBuffer" and event.event_at > event.target_start_at


def summarize_execution_events(events: list[dict[str, object]]) -> dict[str, object]:
    exception_counts: dict[str, int] = {}
    exception_category_counts: dict[str, int] = {}
    exception_codes = default_exception_codes()
    for event in events:
        exception_code = event.get("ExceptionCode")
        if isinstance(exception_code, str) and exception_code:
            exception_counts[exception_code] = exception_counts.get(exception_code, 0) + 1
            definition = exception_codes.get(exception_code)
            category = definition.category if definition is not None else "Unclassified"
            exception_category_counts[category] = exception_category_counts.get(category, 0) + 1

    transitions = _process_transitions(events)
    return {
        "TotalEvents": len(events),
        "RequiresReviewCount": sum(1 for event in events if event.get("RequiresReview") is True),
        "ExceptionCodeCounts": exception_counts,
        "ExceptionCategoryCounts": exception_category_counts,
        "TopExceptionCategories": _top_exception_categories(exception_category_counts),
        "LateArrivalSummary": _late_arrival_summary(events),
        "ReworkLoopCount": sum(transition["Count"] for transition in transitions if transition["IsReworkLoop"]),
        "ProcessTransitions": transitions,
    }


def build_authorized_execution_status(
    dispatch_packages: list[dict[str, object]],
    events: list[dict[str, object]],
) -> list[dict[str, object]]:
    events_by_authorization: dict[str, list[dict[str, object]]] = {}
    for event in events:
        authorization_id = event.get("AuthorizationID")
        if isinstance(authorization_id, str):
            events_by_authorization.setdefault(authorization_id, []).append(event)

    rows = []
    for package in dispatch_packages:
        authorization_id = str(package["AuthorizationID"])
        authorization_events = sorted(
            events_by_authorization.get(authorization_id, []),
            key=lambda item: str(item.get("EventAt", "")),
        )
        last_event = authorization_events[-1] if authorization_events else None
        exception_codes = [
            code
            for code in (
                event.get("ExceptionCode")
                for event in authorization_events
            )
            if isinstance(code, str) and code
        ]
        requires_review = any(
            event.get("RequiresReview") is True
            for event in authorization_events
        )
        rows.append(
            {
                "AuthorizationID": authorization_id,
                "RequestID": package.get("RequestID"),
                "OrderID": package.get("OrderID"),
                "ScheduledStart": package.get("ScheduledStart"),
                "ScheduledEnd": package.get("ScheduledEnd"),
                "ExecutionStatus": _execution_status_from_last_event(last_event),
                "LastEventType": last_event.get("EventType") if last_event else None,
                "LastEventAt": last_event.get("EventAt") if last_event else None,
                "RequiresReview": requires_review,
                "ExceptionCodes": sorted(set(exception_codes)),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            not bool(item["RequiresReview"]),
            _execution_status_rank(str(item["ExecutionStatus"])),
            str(item.get("ScheduledStart") or ""),
            str(item["AuthorizationID"]),
        ),
    )


def build_schedule_execution_variance(
    dispatch_packages: list[dict[str, object]],
    events: list[dict[str, object]],
) -> dict[str, object]:
    events_by_authorization: dict[str, list[dict[str, object]]] = {}
    for event in events:
        authorization_id = event.get("AuthorizationID")
        if isinstance(authorization_id, str):
            events_by_authorization.setdefault(authorization_id, []).append(event)

    rows = []
    for package in dispatch_packages:
        authorization_id = str(package["AuthorizationID"])
        authorization_events = sorted(
            events_by_authorization.get(authorization_id, []),
            key=lambda item: str(item.get("EventAt", "")),
        )
        start_event = next(
            (
                event
                for event in authorization_events
                if event.get("EventType") == "StartedOperation"
            ),
            None,
        )
        shipped_event = next(
            (
                event
                for event in authorization_events
                if event.get("EventType") == "Shipped"
            ),
            None,
        )
        completed_events = [
            event
            for event in authorization_events
            if event.get("EventType") == "CompletedOperation"
        ]
        completion_event = shipped_event or (
            completed_events[-1] if completed_events else None
        )
        planned_start = _parse_event_at(package.get("ScheduledStart"))
        planned_completion = _parse_event_at(package.get("ScheduledEnd"))
        actual_start = _parse_event_at(
            start_event.get("EventAt") if start_event is not None else None
        )
        actual_completion = _parse_event_at(
            completion_event.get("EventAt")
            if completion_event is not None
            else None
        )
        start_deviation = _deviation_minutes(planned_start, actual_start)
        completion_deviation = _deviation_minutes(
            planned_completion,
            actual_completion,
        )
        rows.append(
            {
                "AuthorizationID": authorization_id,
                "OrderID": package.get("OrderID"),
                "PlannedStartAt": _datetime_to_iso(planned_start),
                "ActualStartAt": _datetime_to_iso(actual_start),
                "StartDeviationMinutes": start_deviation,
                "StartTimingStatus": _timing_status(start_deviation),
                "PlannedCompletionAt": _datetime_to_iso(planned_completion),
                "ActualCompletionAt": _datetime_to_iso(actual_completion),
                "CompletionDeviationMinutes": completion_deviation,
                "CompletionTimingStatus": _timing_status(completion_deviation),
                "CompletionBasis": (
                    completion_event.get("EventType")
                    if completion_event is not None
                    else None
                ),
            }
        )

    summary = {
        "OrderCount": len(rows),
        "StartedCount": sum(row["ActualStartAt"] is not None for row in rows),
        "CompletedCount": sum(
            row["ActualCompletionAt"] is not None for row in rows
        ),
        "PendingStartCount": sum(
            row["StartTimingStatus"] == "Pending" for row in rows
        ),
        "PendingCompletionCount": sum(
            row["CompletionTimingStatus"] == "Pending" for row in rows
        ),
        "StartLateCount": sum(
            row["StartTimingStatus"] == "Late" for row in rows
        ),
        "CompletionLateCount": sum(
            row["CompletionTimingStatus"] == "Late" for row in rows
        ),
        "MaxAbsoluteDeviationMinutes": max(
            (
                abs(int(deviation))
                for row in rows
                for deviation in (
                    row["StartDeviationMinutes"],
                    row["CompletionDeviationMinutes"],
                )
                if deviation is not None
            ),
            default=0,
        ),
    }
    if summary["StartLateCount"] or summary["CompletionLateCount"]:
        variance_status = "Late"
    elif summary["PendingStartCount"] or summary["PendingCompletionCount"]:
        variance_status = "Pending"
    else:
        variance_status = "OnTime"
    return {
        "VarianceStatus": variance_status,
        "Summary": summary,
        "Rows": rows,
    }


def build_execution_variance_stability(
    variance_rows: list[dict[str, object]],
    *,
    policy: ReleaseStabilityPolicy | None = None,
    last_replan_at: datetime | None = None,
) -> dict[str, object]:
    rows = []
    for variance in variance_rows:
        if variance.get("ActualCompletionAt") is not None:
            deviation_basis = "Completion"
            planned_at = _parse_event_at(variance.get("PlannedCompletionAt"))
            actual_at = _parse_event_at(variance.get("ActualCompletionAt"))
        elif variance.get("ActualStartAt") is not None:
            deviation_basis = "Start"
            planned_at = _parse_event_at(variance.get("PlannedStartAt"))
            actual_at = _parse_event_at(variance.get("ActualStartAt"))
        else:
            rows.append(
                {
                    "AuthorizationID": variance.get("AuthorizationID"),
                    "OrderID": variance.get("OrderID"),
                    "DeviationBasis": "Pending",
                    "DeviationMinutes": None,
                    "AbsoluteDeviationMinutes": None,
                    "TimingStatus": "Pending",
                    "Severity": "Normal",
                    "Action": "Monitor",
                    "ReplanRequired": False,
                    "ReasonCode": "ExecutionPending",
                }
            )
            continue
        if planned_at is None or actual_at is None:
            raise ValueError("Execution variance requires valid planned and actual times.")
        stability = evaluate_release_stability(
            ReleaseStabilityInput(
                order_id=str(variance.get("OrderID")),
                planned_release_at=planned_at,
                evaluated_release_at=actual_at,
                gate_allowed=True,
                last_replan_at=last_replan_at,
            ),
            policy=policy,
        )
        rows.append(
            {
                "AuthorizationID": variance.get("AuthorizationID"),
                "OrderID": variance.get("OrderID"),
                "DeviationBasis": deviation_basis,
                "DeviationMinutes": stability.deviation_minutes,
                "AbsoluteDeviationMinutes": stability.absolute_deviation_minutes,
                "TimingStatus": stability.timing_status,
                "Severity": stability.severity,
                "Action": stability.action,
                "ReplanRequired": stability.replan_required,
                "ReasonCode": stability.reason_code,
            }
        )
    overall_action = min(
        (str(row["Action"]) for row in rows),
        key=lambda action: {"Replan": 0, "Review": 1, "Monitor": 2}.get(
            action,
            3,
        ),
        default="Monitor",
    )
    return {
        "OverallAction": overall_action,
        "ReplanRequired": any(row["ReplanRequired"] is True for row in rows),
        "Rows": rows,
    }


def build_authorized_execution_alerts(
    *,
    dispatch_packages: list[dict[str, object]],
    events: list[dict[str, object]],
    evaluated_at: datetime,
) -> list[dict[str, object]]:
    status_rows = build_authorized_execution_status(dispatch_packages, events)
    alerts = []
    for row in status_rows:
        exception_codes = row["ExceptionCodes"]
        if row["RequiresReview"]:
            alerts.append(
                {
                    "AuthorizationID": row["AuthorizationID"],
                    "OrderID": row["OrderID"],
                    "AlertType": "ExceptionReview",
                    "Severity": "Warning",
                    "Message": f"Order {row['OrderID']} has execution exceptions requiring review.",
                    "MinutesLate": 0,
                    "ExceptionCodes": exception_codes,
                }
            )
            continue

        scheduled_start = _parse_event_at(row.get("ScheduledStart"))
        if (
            scheduled_start is not None
            and evaluated_at > scheduled_start
            and row["ExecutionStatus"] == "Authorized"
        ):
            alerts.append(
                {
                    "AuthorizationID": row["AuthorizationID"],
                    "OrderID": row["OrderID"],
                    "AlertType": "StartMissed",
                    "Severity": "Critical",
                    "Message": f"Order {row['OrderID']} has not started by the scheduled start time.",
                    "MinutesLate": int((evaluated_at - scheduled_start).total_seconds() / 60),
                    "ExceptionCodes": exception_codes,
                }
            )
            continue

        scheduled_end = _parse_event_at(row.get("ScheduledEnd"))
        if (
            scheduled_end is not None
            and evaluated_at > scheduled_end
            and row["ExecutionStatus"] in {"ArrivedBuffer", "InProcess"}
        ):
            alerts.append(
                {
                    "AuthorizationID": row["AuthorizationID"],
                    "OrderID": row["OrderID"],
                    "AlertType": "CompletionMissed",
                    "Severity": "Warning",
                    "Message": f"Order {row['OrderID']} has not completed by the scheduled end time.",
                    "MinutesLate": int((evaluated_at - scheduled_end).total_seconds() / 60),
                    "ExceptionCodes": exception_codes,
                }
            )
    return sorted(
        alerts,
        key=lambda item: (
            _alert_severity_rank(str(item["Severity"])),
            -int(item["MinutesLate"]),
            str(item["AuthorizationID"]),
        ),
    )


def default_exception_codes() -> dict[str, ExceptionCodeDefinition]:
    definitions = [
        ExceptionCodeDefinition(
            code="MATERIAL_SHORTAGE",
            display_name="Material shortage",
            category="Supply",
        ),
        ExceptionCodeDefinition(
            code="EQUIPMENT_DOWN",
            display_name="Equipment down",
            category="Equipment",
        ),
        ExceptionCodeDefinition(
            code="STAFF_ABSENCE",
            display_name="Staff absence",
            category="Labor",
        ),
        ExceptionCodeDefinition(
            code="QUALITY_REWORK",
            display_name="Quality rework",
            category="Quality",
        ),
    ]
    return {definition.code: definition for definition in definitions}


def _execution_status_from_last_event(event: dict[str, object] | None) -> str:
    if event is None:
        return "Authorized"
    event_type = event.get("EventType")
    if event_type == "ArrivedBuffer":
        return "ArrivedBuffer"
    if event_type == "StartedOperation":
        return "InProcess"
    if event_type == "CompletedOperation":
        return "Completed"
    if event_type == "Shipped":
        return "Shipped"
    return "InExecution"


def _execution_status_rank(status: str) -> int:
    return {
        "ArrivedBuffer": 0,
        "InProcess": 1,
        "Authorized": 2,
        "Completed": 3,
        "Shipped": 4,
    }.get(status, 5)


def _alert_severity_rank(severity: str) -> int:
    return {
        "Critical": 0,
        "Warning": 1,
    }.get(severity, 2)


def _process_transitions(events: list[dict[str, object]]) -> list[dict[str, object]]:
    events_by_order: dict[str, list[dict[str, object]]] = {}
    for event in events:
        order_id = event.get("OrderID")
        if isinstance(order_id, str):
            events_by_order.setdefault(order_id, []).append(event)

    transition_stats: dict[tuple[str, str], dict[str, object]] = {}
    for order_events in events_by_order.values():
        ordered_events = sorted(order_events, key=lambda item: str(item.get("EventAt", "")))
        for previous, current in zip(ordered_events, ordered_events[1:]):
            previous_type = previous.get("EventType")
            current_type = current.get("EventType")
            if not isinstance(previous_type, str) or not isinstance(current_type, str):
                continue

            key = (previous_type, current_type)
            stats = transition_stats.setdefault(
                key,
                {
                    "count": 0,
                    "elapsed_minutes": 0.0,
                    "review_count": 0,
                    "is_rework_loop": _is_rework_transition(previous_type, current_type),
                },
            )
            stats["count"] = int(stats["count"]) + 1
            stats["elapsed_minutes"] = float(stats["elapsed_minutes"]) + _elapsed_minutes(previous, current)
            if previous.get("RequiresReview") is True or current.get("RequiresReview") is True:
                stats["review_count"] = int(stats["review_count"]) + 1

    return [
        {
            "From": source,
            "To": target,
            "Count": int(stats["count"]),
            "AverageElapsedMinutes": round(float(stats["elapsed_minutes"]) / int(stats["count"]), 2),
            "RequiresReviewCount": int(stats["review_count"]),
            "IsReworkLoop": bool(stats["is_rework_loop"]),
        }
        for (source, target), stats in sorted(transition_stats.items())
    ]


def _top_exception_categories(category_counts: dict[str, int]) -> list[dict[str, object]]:
    total = sum(category_counts.values())
    if total == 0:
        return []
    ranked = sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "Rank": index + 1,
            "Category": category,
            "Count": count,
            "Percent": round((count / total) * 100, 2),
            "RecommendedAction": _exception_category_action(category),
        }
        for index, (category, count) in enumerate(ranked)
    ]


def _exception_category_action(category: str) -> str:
    actions = {
        "Supply": "Expedite replenishment and review supplier reliability.",
        "Equipment": "Review equipment downtime and maintenance coverage.",
        "Labor": "Review staffing coverage and cross-training.",
        "Quality": "Review quality gates and rework loops.",
    }
    return actions.get(category, "Review recurring execution exceptions.")


def _late_arrival_summary(events: list[dict[str, object]]) -> dict[str, object]:
    late_minutes = []
    for event in events:
        if event.get("EventType") != "ArrivedBuffer":
            continue
        event_at = _parse_event_at(event.get("EventAt"))
        target_start_at = _parse_event_at(event.get("TargetStartAt"))
        if event_at is None or target_start_at is None or event_at <= target_start_at:
            continue
        late_minutes.append((event_at - target_start_at).total_seconds() / 60)

    if not late_minutes:
        return {
            "LateArrivalCount": 0,
            "AverageLateMinutes": 0.0,
            "MaxLateMinutes": 0.0,
        }
    return {
        "LateArrivalCount": len(late_minutes),
        "AverageLateMinutes": round(sum(late_minutes) / len(late_minutes), 2),
        "MaxLateMinutes": round(max(late_minutes), 2),
    }


def _elapsed_minutes(previous: dict[str, object], current: dict[str, object]) -> float:
    previous_at = _parse_event_at(previous.get("EventAt"))
    current_at = _parse_event_at(current.get("EventAt"))
    if previous_at is None or current_at is None:
        return 0.0
    return max(0.0, (current_at - previous_at).total_seconds() / 60)


def _parse_event_at(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


def _deviation_minutes(
    planned_at: datetime | None,
    actual_at: datetime | None,
) -> int | None:
    if planned_at is None or actual_at is None:
        return None
    return int((actual_at - planned_at).total_seconds() / 60)


def _timing_status(deviation_minutes: int | None) -> str:
    if deviation_minutes is None:
        return "Pending"
    if deviation_minutes < 0:
        return "Early"
    if deviation_minutes > 0:
        return "Late"
    return "OnTime"


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _is_rework_transition(previous_type: str, current_type: str) -> bool:
    sequence = {
        "ArrivedBuffer": 10,
        "StartedOperation": 20,
        "CompletedOperation": 30,
        "Shipped": 40,
    }
    previous_rank = sequence.get(previous_type)
    current_rank = sequence.get(current_type)
    return previous_rank is not None and current_rank is not None and current_rank <= previous_rank
