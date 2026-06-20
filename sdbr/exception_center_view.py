from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from hashlib import sha256

from sdbr.release_authorization import ReleaseAuthorization, build_dispatch_package
from sdbr.shop_floor_execution import build_authorized_execution_alerts


def build_exception_center_workbench(
    *,
    planning_runs: list[dict[str, object]],
    audit_events: list[dict[str, object]],
    replan_requests: list[object],
    release_authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    rows.extend(_planning_run_exceptions(planning_runs, audit_events))
    rows.extend(_constraint_buffer_risks(planning_runs))
    rows.extend(_execution_alert_exceptions(release_authorizations, execution_events, evaluated_at))
    rows.extend(_replan_request_exceptions(replan_requests))
    rows = sorted(
        rows,
        key=lambda item: (
            _severity_rank(str(item["Severity"])),
            str(item.get("OccurredAt") or ""),
            str(item["ExceptionID"]),
        ),
        reverse=False,
    )
    return {
        "EvaluatedAt": evaluated_at.isoformat(),
        "Summary": {
            "TotalCount": len(rows),
            "OpenCount": sum(1 for row in rows if row["Status"] == "Open"),
            "CriticalCount": sum(1 for row in rows if row["Severity"] == "Critical"),
            "WarningCount": sum(1 for row in rows if row["Severity"] == "Warning"),
            "InformationCount": sum(1 for row in rows if row["Severity"] == "Information"),
        },
        "FilterOptions": {
            "Severities": _unique(rows, "Severity"),
            "Statuses": _unique(rows, "Status"),
            "Sources": _unique(rows, "Source"),
            "ObjectTypes": _unique(rows, "ObjectType"),
        },
        "Rows": rows,
    }


def build_exception_detail(
    *,
    exception_id: str,
    planning_runs: list[dict[str, object]],
    audit_events: list[dict[str, object]],
    replan_requests: list[object],
    release_authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> dict[str, object]:
    workbench = build_exception_center_workbench(
        planning_runs=planning_runs,
        audit_events=audit_events,
        replan_requests=replan_requests,
        release_authorizations=release_authorizations,
        execution_events=execution_events,
        evaluated_at=evaluated_at,
    )
    row = next(
        (item for item in workbench["Rows"] if item["ExceptionID"] == exception_id),
        None,
    )
    if row is None:
        raise KeyError(exception_id)
    return {
        "Exception": row,
        "RelatedObjects": _related_objects(row, replan_requests),
        "ResolutionActions": _resolution_actions(row),
    }


def _planning_run_exceptions(
    planning_runs: list[dict[str, object]],
    audit_events: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for run in planning_runs:
        status = str(run.get("Status"))
        if status not in {"Failed", "DeadLetter"}:
            continue
        run_id = str(run.get("RunID"))
        reason = str(
            run.get("DeadLetterReason")
            or _dict(run.get("LastFailure")).get("SolverStatus")
            or run.get("SolverStatus")
            or status
        )
        rows.append(
            _row(
                exception_type="PlanningRunDeadLetter" if status == "DeadLetter" else "PlanningRunFailed",
                severity="Critical" if status == "DeadLetter" else "Warning",
                object_type="PlanningRun",
                object_id=run_id,
                occurred_at=str(run.get("CompletedAt") or run.get("RequestedAt") or ""),
                reason_code=reason,
                business_impact_code="ScheduleUnavailable",
                suggested_action_code="RecoverPlanningRun" if status == "DeadLetter" else "ReviewPlanningRunFailure",
                owner_id=str(run.get("RequestedBy") or "planner"),
                source="PlanningRunLifecycle",
                audit_trail=_audit_for_object(audit_events, "RunID", run_id),
            )
        )
    return rows


def _constraint_buffer_risks(planning_runs: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for run in planning_runs:
        schedule = _dict(run.get("Schedule"))
        for item in _dict_list(schedule.get("BufferBoard")):
            zone = str(item.get("Zone") or "")
            if zone not in {"Red", "Late"}:
                continue
            order_id = str(item.get("OrderID"))
            rows.append(
                _row(
                    exception_type="ConstraintBufferRisk",
                    severity="Critical" if zone == "Late" else "Warning",
                    object_type="WorkOrder",
                    object_id=order_id,
                    occurred_at=str(schedule.get("GeneratedAt") or run.get("CompletedAt") or ""),
                    reason_code=f"ConstraintBuffer{zone}",
                    business_impact_code="ConstraintMayStarve",
                    suggested_action_code="ExpediteConstraintBuffer",
                    owner_id=str(run.get("RequestedBy") or "planner"),
                    source="BufferManagement",
                    audit_trail=[],
                )
            )
    return rows


def _execution_alert_exceptions(
    authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> list[dict[str, object]]:
    dispatch_packages = [build_dispatch_package(item) for item in authorizations]
    rows = []
    for alert in build_authorized_execution_alerts(
        dispatch_packages=dispatch_packages,
        events=execution_events,
        evaluated_at=evaluated_at,
    ):
        rows.append(
            _row(
                exception_type="ExecutionAlert",
                severity=str(alert.get("Severity") or "Warning"),
                object_type="WorkOrder",
                object_id=str(alert.get("OrderID")),
                occurred_at=evaluated_at.isoformat(),
                reason_code=str(alert.get("AlertType")),
                business_impact_code="ExecutionThreatensSchedule",
                suggested_action_code="ReviewExecutionAlert",
                owner_id="shop-floor-supervisor",
                source="ShopFloorExecution",
                audit_trail=[],
            )
        )
    return rows


def _replan_request_exceptions(replan_requests: list[object]) -> list[dict[str, object]]:
    rows = []
    for request in replan_requests:
        data = _object_dict(request)
        status = str(data.get("status") or data.get("Status"))
        if status in {"Completed", "Rejected"}:
            continue
        request_id = str(data.get("request_id") or data.get("RequestID"))
        rows.append(
            _row(
                exception_type="ReplanSuggestion",
                severity="Warning" if status == "PendingReview" else "Information",
                object_type="ReplanRequest",
                object_id=request_id,
                occurred_at=_iso(data.get("detected_at") or data.get("DetectedAt")),
                reason_code=str(data.get("reason_code") or data.get("ReasonCode")),
                business_impact_code="ScheduleStabilityAtRisk",
                suggested_action_code="ReviewReplanRequest",
                owner_id=str(data.get("requested_by") or data.get("RequestedBy") or "planner"),
                source=str(data.get("source") or data.get("Source") or "Replanning"),
                audit_trail=[],
            )
        )
    return rows


def _row(
    *,
    exception_type: str,
    severity: str,
    object_type: str,
    object_id: str,
    occurred_at: str,
    reason_code: str,
    business_impact_code: str,
    suggested_action_code: str,
    owner_id: str,
    source: str,
    audit_trail: list[dict[str, object]],
) -> dict[str, object]:
    exception_id = _exception_id(exception_type, object_id, reason_code, occurred_at)
    return {
        "ExceptionID": exception_id,
        "ExceptionType": exception_type,
        "Severity": severity,
        "Status": "Open",
        "ObjectType": object_type,
        "ObjectID": object_id,
        "OccurredAt": occurred_at,
        "ReasonCode": reason_code,
        "BusinessImpactCode": business_impact_code,
        "SuggestedActionCode": suggested_action_code,
        "OwnerID": owner_id,
        "Source": source,
        "AuditTrail": audit_trail,
    }


def _related_objects(row: dict[str, object], replan_requests: list[object]) -> list[dict[str, object]]:
    if row["ExceptionType"] == "ReplanSuggestion":
        request = next(
            (
                _object_dict(item)
                for item in replan_requests
                if str(_object_dict(item).get("request_id")) == row["ObjectID"]
            ),
            {},
        )
        return [
            {
                "ObjectType": "WorkOrder",
                "ObjectID": request.get("order_id"),
                "Relationship": "TriggeredBy",
            }
        ]
    return [
        {
            "ObjectType": row["ObjectType"],
            "ObjectID": row["ObjectID"],
            "Relationship": "Primary",
        }
    ]


def _resolution_actions(row: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "ActionCode": row["SuggestedActionCode"],
            "RequiresComment": row["SuggestedActionCode"] in {"RecoverPlanningRun", "ReviewReplanRequest"},
        }
    ]


def _audit_for_object(
    audit_events: list[dict[str, object]],
    key: str,
    value: str,
) -> list[dict[str, object]]:
    return sorted(
        [event for event in audit_events if str(event.get(key)) == value],
        key=lambda event: str(event.get("OccurredAt") or ""),
        reverse=True,
    )


def _exception_id(exception_type: str, object_id: str, reason_code: str, occurred_at: str) -> str:
    identity = "|".join((exception_type, object_id, reason_code, occurred_at))
    return f"EXC-{sha256(identity.encode('utf-8')).hexdigest()[:16]}"


def _unique(rows: list[dict[str, object]], key: str) -> list[str]:
    return sorted({str(row[key]) for row in rows})


def _severity_rank(severity: str) -> int:
    return {"Critical": 0, "Warning": 1, "Information": 2}.get(severity, 3)


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _object_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        return asdict(value)
    return {}


def _iso(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "")
