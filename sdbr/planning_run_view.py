from __future__ import annotations

from datetime import datetime


STATUS_ACTIONS = {
    "Pending": ["Enqueue", "Execute", "Cancel"],
    "Queued": [],
    "Running": [],
    "Completed": ["OpenResults"],
    "Failed": [],
    "DeadLetter": ["Recover"],
    "Cancelled": [],
}


def build_planning_run_workbench(
    *,
    planning_runs: list[dict[str, object]],
    ortools_available: bool,
) -> dict[str, object]:
    rows = [planning_run_row(item) for item in planning_runs]
    rows.sort(key=lambda item: (str(item["RequestedAt"]), str(item["RunID"])), reverse=True)
    statuses = [
        "Pending",
        "Queued",
        "Running",
        "Completed",
        "Failed",
        "DeadLetter",
        "Cancelled",
    ]
    return {
        "Total": len(rows),
        "ByStatus": {
            status: sum(1 for row in rows if row["Status"] == status)
            for status in statuses
        },
        "Rows": rows,
        "Capabilities": {
            "Solvers": [
                {
                    "BackendID": "ortools",
                    "Available": ortools_available,
                    "Status": "Available" if ortools_available else "Unavailable",
                },
                {
                    "BackendID": "gurobi",
                    "Available": False,
                    "Status": "Paused",
                },
            ],
            "Simio": {
                "Available": False,
                "Status": "Paused",
            },
        },
    }


def planning_run_row(planning_run: dict[str, object]) -> dict[str, object]:
    return {
        "RunID": planning_run.get("RunID"),
        "ProblemID": planning_run.get("ProblemID"),
        "Status": planning_run.get("Status"),
        "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
        "OperationalStateSnapshotID": planning_run.get(
            "OperationalStateSnapshotID"
        ),
        "SolverBackendID": planning_run.get("SolverBackendID"),
        "SolverStatus": planning_run.get("SolverStatus"),
        "RequestedBy": planning_run.get("RequestedBy"),
        "RequestedAt": planning_run.get("RequestedAt"),
        "StartedAt": planning_run.get("StartedAt"),
        "CompletedAt": planning_run.get("CompletedAt"),
        "DurationSeconds": _duration_seconds(planning_run),
        "AttemptCount": int(planning_run.get("AttemptCount", 0)),
        "MaxAttempts": planning_run.get("MaxAttempts", 3),
        "TimeLimitSeconds": planning_run.get("TimeLimitSeconds", 300),
        "RetryDelaySeconds": planning_run.get("RetryDelaySeconds", 60),
        "WorkerID": planning_run.get("WorkerID"),
        "AllowedActions": list(
            STATUS_ACTIONS.get(str(planning_run.get("Status")), [])
        ),
    }


def build_planning_run_detail(
    *,
    planning_run: dict[str, object],
    audit_events: list[dict[str, object]],
) -> dict[str, object]:
    row = planning_run_row(planning_run)
    return {
        **row,
        "ScheduleStartAt": planning_run.get("ScheduleStartAt"),
        "SourceRunID": planning_run.get("SourceRunID"),
        "ReleasePolicyVersionID": planning_run.get("ReleasePolicyVersionID"),
        "FrozenReleasePolicy": planning_run.get("FrozenReleasePolicy"),
        "FrozenCalendarOverrides": list(
            planning_run.get("FrozenCalendarOverrides", [])
        ),
        "FrozenCalendarOverrideSummary": {
            "FrozenOverrideCount": len(
                planning_run.get("FrozenCalendarOverrides", [])
            ),
            "AppliedOverrideCount": _applied_calendar_override_count(planning_run),
        },
        "TimeBufferMinutes": planning_run.get("TimeBufferMinutes"),
        "FreezeWindowMinutes": planning_run.get("FreezeWindowMinutes", 0),
        "ObjectiveStrategyID": planning_run.get("ObjectiveStrategyID", "balanced"),
        "SetupTransitions": list(planning_run.get("SetupTransitions", [])),
        "TimeLimitSeconds": planning_run.get("TimeLimitSeconds"),
        "SolverMessage": planning_run.get("SolverMessage"),
        "FrozenInputs": {
            "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
            "MasterDataCapturedAt": planning_run.get("MasterDataCapturedAt"),
            "OperationalStateSnapshotID": planning_run.get(
                "OperationalStateSnapshotID"
            ),
            "OperationalStateCapturedAt": planning_run.get(
                "OperationalStateCapturedAt"
            ),
            "SourceRunID": planning_run.get("SourceRunID"),
            "ReleasePolicyVersionID": planning_run.get("ReleasePolicyVersionID"),
        },
        "Worker": (
            {
                "WorkerID": planning_run.get("WorkerID"),
                "LeaseClaimedAt": planning_run.get("LeaseClaimedAt"),
                "LeaseExpiresAt": planning_run.get("LeaseExpiresAt"),
                "LeaseRenewalCount": int(
                    planning_run.get("LeaseRenewalCount", 0)
                ),
            }
            if planning_run.get("WorkerID")
            else None
        ),
        "Timeline": list(planning_run.get("StatusHistory", [])),
        "Diagnostics": _diagnostics(planning_run),
        "Retry": {
            "AttemptCount": int(planning_run.get("AttemptCount", 0)),
            "MaxAttempts": planning_run.get("MaxAttempts"),
            "NextAttemptAt": planning_run.get("NextAttemptAt"),
            "LastFailure": planning_run.get("LastFailure"),
            "DeadLetterReason": planning_run.get("DeadLetterReason"),
            "PreviousDeadLetter": planning_run.get("PreviousDeadLetter"),
        },
        "AuditEvents": sorted(
            audit_events,
            key=lambda item: str(item.get("OccurredAt", "")),
            reverse=True,
        ),
    }


def _duration_seconds(planning_run: dict[str, object]) -> float | None:
    start = _parse_datetime(planning_run.get("StartedAt"))
    end = _parse_datetime(planning_run.get("CompletedAt"))
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 2)


def _diagnostics(planning_run: dict[str, object]) -> list[dict[str, object]]:
    schedule = planning_run.get("Schedule")
    if isinstance(schedule, dict):
        diagnostics = schedule.get("SolverDiagnostics")
        if isinstance(diagnostics, list):
            return diagnostics
    message = planning_run.get("SolverMessage")
    if not message:
        return []
    return [
        {
            "Severity": (
                "Error"
                if planning_run.get("Status") in {"Failed", "DeadLetter"}
                else "Information"
            ),
            "Code": str(planning_run.get("SolverStatus") or "SOLVER_STATUS"),
            "Message": message,
            "EntityID": planning_run.get("RunID"),
        }
    ]


def _applied_calendar_override_count(planning_run: dict[str, object]) -> int:
    summary = planning_run.get("CalendarOverrideSummary")
    if isinstance(summary, dict):
        return int(summary.get("AppliedOverrideCount", 0))
    schedule = planning_run.get("Schedule")
    if isinstance(schedule, dict):
        schedule_summary = schedule.get("CalendarOverrideSummary")
        if isinstance(schedule_summary, dict):
            return int(schedule_summary.get("AppliedOverrideCount", 0))
    return 0


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
