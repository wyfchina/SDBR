from __future__ import annotations

from datetime import datetime, timezone

from sdbr.master_data_validation import MaterialRequirement
from sdbr.operational_state import OperationalStateSnapshot
from sdbr.plan_publication import build_plan_publication_view
from sdbr.release_authorization import ReleaseAuthorization
from sdbr.test_data import test_case_catalog
from sdbr.work_order_release_view import build_release_management_workbench


DEFAULT_CASE_EVALUATED_AT = datetime(2026, 7, 2, 12, tzinfo=timezone.utc)


def build_test_case_acceptance_workbench(
    *,
    planning_runs: dict[str, dict[str, object]],
    master_data_versions: dict[str, dict[str, object]],
    operational_state_snapshots: dict[str, OperationalStateSnapshot],
    release_authorizations: list[ReleaseAuthorization],
    acceptance_decisions: list[dict[str, object]] | None = None,
    evaluated_at: datetime = DEFAULT_CASE_EVALUATED_AT,
) -> dict[str, object]:
    decisions = acceptance_decisions or []
    cases = [
        _case_row(
            case=case.to_dict(),
            planning_runs=planning_runs,
            master_data_versions=master_data_versions,
            operational_state_snapshots=operational_state_snapshots,
            release_authorizations=release_authorizations,
            acceptance_decisions=decisions,
            evaluated_at=evaluated_at,
        )
        for case in test_case_catalog()
    ]
    latest_decisions = _latest_decisions_by_case(decisions)
    return {
        "AcceptancePackageID": "TST-ACP-BASELINE-20260619",
        "DatasetID": "TST-DATASET-BASELINE-20260619",
        "EvaluatedAt": evaluated_at.isoformat(),
        "EnvironmentBoundary": "TestOnly",
        "ExecutionPlan": {
            "StepCount": 4,
            "Steps": [
                "Reset or seed the isolated test database.",
                "Execute each TST-RUN-* Planning Run with OR-Tools CP-SAT.",
                "Evaluate schedule output, release gate and publication state.",
                "Record human confirmation or rejection for passed cases.",
            ],
        },
        "Summary": {
            "CaseCount": len(cases),
            "PassedCount": sum(1 for case in cases if case["AcceptanceStatus"] == "Passed"),
            "NeedsExecutionCount": sum(
                1 for case in cases if case["AcceptanceStatus"] == "NeedsExecution"
            ),
            "FailedCount": sum(1 for case in cases if case["AcceptanceStatus"] == "Failed"),
            "ConfirmedCount": sum(
                1
                for decision in latest_decisions.values()
                if decision.get("Decision") == "Confirm"
            ),
            "RejectedCount": sum(
                1
                for decision in latest_decisions.values()
                if decision.get("Decision") == "Reject"
            ),
            "PendingHumanDecisionCount": sum(
                1
                for case in cases
                if case["AcceptanceStatus"] == "Passed"
                and case["CaseID"] not in latest_decisions
            ),
        },
        "DecisionRecords": sorted(
            decisions,
            key=lambda item: str(item.get("DecidedAt", "")),
            reverse=True,
        ),
        "Cases": cases,
    }


def _case_row(
    *,
    case: dict[str, object],
    planning_runs: dict[str, dict[str, object]],
    master_data_versions: dict[str, dict[str, object]],
    operational_state_snapshots: dict[str, OperationalStateSnapshot],
    release_authorizations: list[ReleaseAuthorization],
    acceptance_decisions: list[dict[str, object]],
    evaluated_at: datetime,
) -> dict[str, object]:
    run_id = str(case["PlanningRunID"])
    planning_run = planning_runs.get(run_id)
    if planning_run is None:
        return {
            **case,
            "AcceptanceStatus": "Failed",
            "FailureReasons": ["PLANNING_RUN_NOT_FOUND"],
            "Expected": _expected_summary(case),
            "ActualVsExpected": _actual_vs_expected(case=case, actual={}, release={}),
            "LatestDecision": _latest_decision(case["CaseID"], acceptance_decisions),
            "Actual": {},
        }

    actual: dict[str, object] = {
        "PlanningRunStatus": planning_run.get("Status"),
        "SolverBackendID": planning_run.get("SolverBackendID"),
        "SolverStatus": planning_run.get("SolverStatus"),
        "PublicationStatus": build_plan_publication_view(planning_run=planning_run)[
            "PublicationStatus"
        ],
    }
    if isinstance(planning_run.get("Schedule"), dict):
        schedule = planning_run["Schedule"]
        actual["OrderCount"] = schedule.get("OrderCount")
        actual["GeneratedAt"] = schedule.get("GeneratedAt")
        actual["DiagnosticCodes"] = _diagnostic_codes(schedule)
        actual["ScheduleAssertions"] = _schedule_assertions(schedule=schedule, case=case)

    if not isinstance(
        planning_run.get("Schedule"), dict
    ):
        return {
            **case,
            "AcceptanceStatus": "NeedsExecution",
            "FailureReasons": ["PLANNING_RUN_NOT_COMPLETED"],
            "Expected": _expected_summary(case),
            "ActualVsExpected": _actual_vs_expected(case=case, actual=actual, release={}),
            "LatestDecision": _latest_decision(case["CaseID"], acceptance_decisions),
            "Actual": actual,
        }

    release = (
        _release_summary(
            planning_run=planning_run,
            master_data_versions=master_data_versions,
            operational_state_snapshots=operational_state_snapshots,
            release_authorizations=release_authorizations,
            evaluated_at=evaluated_at,
        )
        if planning_run.get("Status") == "Completed"
        else {
            "Status": "NotEvaluatedForNonCompletedPlan",
            "Summary": {},
            "BlockingCodes": [],
        }
    )
    actual["Release"] = release
    failures = _case_failures(case=case, actual=actual, release=release)
    return {
        **case,
        "AcceptanceStatus": "Passed" if not failures else "Failed",
        "FailureReasons": failures,
        "Expected": _expected_summary(case),
        "ActualVsExpected": _actual_vs_expected(case=case, actual=actual, release=release),
        "LatestDecision": _latest_decision(case["CaseID"], acceptance_decisions),
        "Actual": actual,
    }


def _release_summary(
    *,
    planning_run: dict[str, object],
    master_data_versions: dict[str, dict[str, object]],
    operational_state_snapshots: dict[str, OperationalStateSnapshot],
    release_authorizations: list[ReleaseAuthorization],
    evaluated_at: datetime,
) -> dict[str, object]:
    snapshot = operational_state_snapshots.get(
        str(planning_run.get("OperationalStateSnapshotID"))
    )
    if snapshot is None:
        return {"Status": "OperationalStateSnapshotNotFound"}
    master_data = master_data_versions.get(str(planning_run.get("MasterDataVersionID")), {})
    workbench = build_release_management_workbench(
        planning_run=planning_run,
        evaluated_at=evaluated_at,
        inventory_buffers=snapshot.inventory_buffers,
        material_requirements=_material_requirements(master_data),
        wip_limits=snapshot.wip_limits,
        material_availability=snapshot.material_availability,
        operational_state_status="Fresh",
        operational_state_captured_at=snapshot.captured_at,
        authorizations=release_authorizations,
    )
    blocking_codes = sorted(
        {
            str(reason.get("Code"))
            for candidate in workbench["Candidates"]
            for reason in candidate.get("BlockingReasons", [])
            if reason.get("Code")
        }
    )
    return {
        "Status": "Available",
        "Summary": workbench["Summary"],
        "BlockingCodes": blocking_codes,
    }


def _material_requirements(
    master_data: dict[str, object],
) -> list[MaterialRequirement]:
    result = []
    for item in master_data.get("MaterialRequirements", []):
        if not isinstance(item, dict):
            continue
        result.append(
            MaterialRequirement(
                order_id=str(item.get("OrderID")),
                item_id=str(item.get("ItemID")),
                location_id=str(item.get("LocationID")),
                required_qty=float(item.get("RequiredQty") or 0),
            )
        )
    return result


def _case_failures(
    *,
    case: dict[str, object],
    actual: dict[str, object],
    release: dict[str, object],
) -> list[str]:
    failures = []
    if actual.get("SolverBackendID") != case.get("ExpectedSolverBackendID"):
        failures.append("SOLVER_BACKEND_MISMATCH")
    if actual.get("PlanningRunStatus") != case.get("ExpectedPlanningRunStatus"):
        failures.append("PLANNING_RUN_STATUS_MISMATCH")
    if actual.get("SolverStatus") not in case.get("ExpectedSolverStatuses", []):
        failures.append("SOLVER_STATUS_MISMATCH")
    diagnostic_codes = set(actual.get("DiagnosticCodes", []))
    for code in case.get("ExpectedDiagnosticCodes", []):
        if code not in diagnostic_codes:
            failures.append(f"EXPECTED_DIAGNOSTIC_CODE_MISSING:{code}")
    passed_assertions = {
        str(item.get("AssertionID"))
        for item in actual.get("ScheduleAssertions", [])
        if isinstance(item, dict) and item.get("Passed") is True
    }
    for assertion_id in case.get("ExpectedScheduleAssertions", []):
        if assertion_id not in passed_assertions:
            failures.append(f"SCHEDULE_ASSERTION_FAILED:{assertion_id}")
    if case.get("ExpectedPlanningRunStatus") != "Completed":
        if actual.get("PublicationStatus") != case.get("ExpectedPublicationStatus"):
            failures.append("PUBLICATION_STATUS_MISMATCH")
        return failures
    if release.get("Status") != "Available":
        failures.append(str(release.get("Status") or "RELEASE_SUMMARY_UNAVAILABLE"))
        return failures
    summary = release.get("Summary", {})
    if isinstance(summary, dict) and int(summary.get("ReadyCount") or 0) < int(
        case.get("ExpectedReleaseReadyMin") or 0
    ):
        failures.append("RELEASE_READY_COUNT_BELOW_EXPECTATION")
    blocking_codes = set(release.get("BlockingCodes", []))
    for code in case.get("ExpectedBlockingCodes", []):
        if code not in blocking_codes:
            failures.append(f"EXPECTED_BLOCKING_CODE_MISSING:{code}")
    if actual.get("PublicationStatus") != case.get("ExpectedPublicationStatus"):
        failures.append("PUBLICATION_STATUS_MISMATCH")
    return failures


def _expected_summary(case: dict[str, object]) -> dict[str, object]:
    return {
        "SolverBackendID": case.get("ExpectedSolverBackendID"),
        "PlanningRunStatus": case.get("ExpectedPlanningRunStatus"),
        "SolverStatuses": case.get("ExpectedSolverStatuses", []),
        "ReleaseReadyMin": case.get("ExpectedReleaseReadyMin"),
        "BlockingCodes": case.get("ExpectedBlockingCodes", []),
        "PublicationStatus": case.get("ExpectedPublicationStatus"),
        "InputSummaryZh": case.get("InputSummaryZh"),
        "ScheduleZh": case.get("ExpectedScheduleZh"),
        "ReleaseZh": case.get("ExpectedReleaseZh"),
        "PublicationZh": case.get("ExpectedPublicationZh"),
        "ScheduleAssertions": case.get("ExpectedScheduleAssertions", []),
        "DiagnosticCodes": case.get("ExpectedDiagnosticCodes", []),
    }


def _actual_vs_expected(
    *,
    case: dict[str, object],
    actual: dict[str, object],
    release: dict[str, object],
) -> list[dict[str, object]]:
    summary = release.get("Summary", {}) if isinstance(release, dict) else {}
    blocking_codes = release.get("BlockingCodes", []) if isinstance(release, dict) else []
    comparisons = [
        (
            "SolverBackendID",
            case.get("ExpectedSolverBackendID"),
            actual.get("SolverBackendID"),
            actual.get("SolverBackendID") == case.get("ExpectedSolverBackendID"),
        ),
        (
            "PlanningRunStatus",
            case.get("ExpectedPlanningRunStatus"),
            actual.get("PlanningRunStatus"),
            actual.get("PlanningRunStatus") == case.get("ExpectedPlanningRunStatus"),
        ),
        (
            "SolverStatus",
            case.get("ExpectedSolverStatuses"),
            actual.get("SolverStatus"),
            actual.get("SolverStatus") in case.get("ExpectedSolverStatuses", []),
        ),
        (
            "ReleaseReadyMin",
            case.get("ExpectedReleaseReadyMin"),
            summary.get("ReadyCount") if isinstance(summary, dict) else None,
            isinstance(summary, dict)
            and int(summary.get("ReadyCount") or 0)
            >= int(case.get("ExpectedReleaseReadyMin") or 0),
        ),
        (
            "BlockingCodes",
            case.get("ExpectedBlockingCodes"),
            blocking_codes,
            set(case.get("ExpectedBlockingCodes", [])) <= set(blocking_codes or []),
        ),
        (
            "PublicationStatus",
            case.get("ExpectedPublicationStatus"),
            actual.get("PublicationStatus"),
            actual.get("PublicationStatus") == case.get("ExpectedPublicationStatus"),
        ),
        (
            "DiagnosticCodes",
            case.get("ExpectedDiagnosticCodes", []),
            actual.get("DiagnosticCodes", []),
            set(case.get("ExpectedDiagnosticCodes", []))
            <= set(actual.get("DiagnosticCodes", [])),
        ),
        (
            "ScheduleAssertions",
            case.get("ExpectedScheduleAssertions", []),
            actual.get("ScheduleAssertions", []),
            set(case.get("ExpectedScheduleAssertions", []))
            <= {
                str(item.get("AssertionID"))
                for item in actual.get("ScheduleAssertions", [])
                if isinstance(item, dict) and item.get("Passed") is True
            },
        ),
    ]
    return [
        {
            "CheckID": check_id,
            "Expected": expected,
            "Actual": actual_value,
            "Passed": passed,
        }
        for check_id, expected, actual_value, passed in comparisons
    ]


def _diagnostic_codes(schedule: dict[str, object]) -> list[str]:
    return sorted(
        {
            str(item.get("Code"))
            for item in schedule.get("SolverDiagnostics", [])
            if isinstance(item, dict) and item.get("Code")
        }
    )


def _schedule_assertions(
    *,
    schedule: dict[str, object],
    case: dict[str, object],
) -> list[dict[str, object]]:
    requested = set(case.get("ExpectedScheduleAssertions", []))
    checks: list[dict[str, object]] = []
    if "ALL_ORDERS_SCHEDULED" in requested:
        scheduled = _scheduled_order_count(schedule)
        expected = int(schedule.get("OrderCount") or 0)
        checks.append(
            _assertion(
                "ALL_ORDERS_SCHEDULED",
                expected > 0 and scheduled == expected,
                f"{scheduled} / {expected} orders have scheduled bars.",
            )
        )
    if "FINITE_RESOURCE_NO_OVERLAP" in requested:
        checks.append(_finite_resource_no_overlap(schedule))
    if "ALTERNATE_RESOURCE_USED" in requested:
        checks.append(
            _assertion(
                "ALTERNATE_RESOURCE_USED",
                any("ALT" in str(bar.get("ResourceID", "")) for bar in _bars(schedule)),
                "At least one scheduled bar is assigned to an alternate resource.",
            )
        )
    if "CALENDAR_OVERRIDE_APPLIED" in requested:
        summary = schedule.get("CalendarOverrideSummary", {})
        checks.append(
            _assertion(
                "CALENDAR_OVERRIDE_APPLIED",
                isinstance(summary, dict)
                and int(summary.get("AppliedOverrideCount") or 0) > 0,
                f"Applied overrides: {summary.get('AppliedOverrideCount') if isinstance(summary, dict) else 0}.",
            )
        )
    if "MAINTENANCE_WINDOW_AVOIDED" in requested:
        checks.append(_maintenance_window_avoided(schedule))
    if "OVERTIME_WINDOW_USED" in requested:
        checks.append(_overtime_window_used(schedule))
    if "EFFICIENCY_DURATION_APPLIED" in requested:
        checks.append(_operation_duration_assertion(schedule, "EFFICIENCY_DURATION_APPLIED", 120))
    if "SETUP_LAG_APPLIED" in requested:
        checks.append(_setup_lag_applied(schedule))
    if "INFEASIBLE_DIAGNOSTIC_REPORTED" in requested:
        checks.append(
            _assertion(
                "INFEASIBLE_DIAGNOSTIC_REPORTED",
                "ORTOOLS_INFEASIBLE" in _diagnostic_codes(schedule),
                "Solver diagnostics include ORTOOLS_INFEASIBLE.",
            )
        )
    return checks


def _assertion(assertion_id: str, passed: bool, evidence: str) -> dict[str, object]:
    return {"AssertionID": assertion_id, "Passed": bool(passed), "Evidence": evidence}


def _bars(schedule: dict[str, object]) -> list[dict[str, object]]:
    result = []
    rows = schedule.get("GanttRows", [])
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        for bar in row.get("Bars", []):
            if isinstance(bar, dict):
                result.append({**bar, "ResourceID": row.get("ResourceID")})
    return result


def _scheduled_order_count(schedule: dict[str, object]) -> int:
    return len({str(bar.get("OrderID")) for bar in _bars(schedule) if bar.get("OrderID")})


def _finite_resource_no_overlap(schedule: dict[str, object]) -> dict[str, object]:
    rows = schedule.get("GanttRows", [])
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        bars = sorted(
            [
                bar
                for bar in row.get("Bars", [])
                if isinstance(bar, dict) and bar.get("Start") and bar.get("End")
            ],
            key=lambda item: str(item.get("Start")),
        )
        for left, right in zip(bars, bars[1:]):
            if str(left.get("End")) > str(right.get("Start")):
                return _assertion(
                    "FINITE_RESOURCE_NO_OVERLAP",
                    False,
                    f"{row.get('ResourceID')} overlaps {left.get('OperationID')} and {right.get('OperationID')}.",
                )
    return _assertion("FINITE_RESOURCE_NO_OVERLAP", True, "No overlapping bars on scheduled resources.")


def _maintenance_window_avoided(schedule: dict[str, object]) -> dict[str, object]:
    maint_start = "2026-06-22T08:00:00+00:00"
    maint_end = "2026-06-22T12:00:00+00:00"
    for bar in _bars(schedule):
        if str(bar.get("ResourceID")) != "TST-CP-CAL":
            continue
        if str(bar.get("Start")) < maint_end and str(bar.get("End")) > maint_start:
            return _assertion("MAINTENANCE_WINDOW_AVOIDED", False, "Processing bar overlaps the maintenance window.")
    return _assertion("MAINTENANCE_WINDOW_AVOIDED", True, "No processing bar overlaps the maintenance window.")


def _overtime_window_used(schedule: dict[str, object]) -> dict[str, object]:
    for bar in _bars(schedule):
        if str(bar.get("ResourceID")) == "TST-CP-CAL" and str(bar.get("Start")).startswith("2026-06-22T18:"):
            return _assertion("OVERTIME_WINDOW_USED", True, "A processing bar starts in the overtime window.")
    return _assertion("OVERTIME_WINDOW_USED", False, "No processing bar used the configured overtime window.")


def _operation_duration_assertion(
    schedule: dict[str, object],
    assertion_id: str,
    expected_minutes: int,
) -> dict[str, object]:
    durations = [int(bar.get("DurationMinutes") or 0) for bar in _bars(schedule)]
    return _assertion(
        assertion_id,
        expected_minutes in durations,
        f"Observed durations: {durations}; expected {expected_minutes} minutes.",
    )


def _setup_lag_applied(schedule: dict[str, object]) -> dict[str, object]:
    bars = sorted(
        [bar for bar in _bars(schedule) if str(bar.get("ResourceID")) == "TST-CP-SETUP"],
        key=lambda item: str(item.get("Start")),
    )
    if len(bars) < 2:
        return _assertion("SETUP_LAG_APPLIED", False, "Less than two setup-case bars were scheduled.")
    left_end = datetime.fromisoformat(str(bars[0]["End"]))
    right_start = datetime.fromisoformat(str(bars[1]["Start"]))
    lag = int((right_start - left_end).total_seconds() / 60)
    return _assertion(
        "SETUP_LAG_APPLIED",
        lag >= 45,
        f"Observed setup lag is {lag} minutes.",
    )


def _latest_decision(
    case_id: object,
    decisions: list[dict[str, object]],
) -> dict[str, object] | None:
    latest = _latest_decisions_by_case(decisions).get(str(case_id))
    return dict(latest) if latest else None


def _latest_decisions_by_case(
    decisions: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for decision in sorted(decisions, key=lambda item: str(item.get("DecidedAt", ""))):
        result[str(decision.get("CaseID"))] = decision
    return result


def create_test_case_acceptance_decision(
    *,
    case: dict[str, object],
    decision: str,
    actor_id: str,
    decided_at: datetime,
    comment: str | None,
    existing_decisions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "DecisionID": f"TST-ACD-{len(existing_decisions) + 1:06d}",
        "AcceptancePackageID": "TST-ACP-BASELINE-20260619",
        "DatasetID": "TST-DATASET-BASELINE-20260619",
        "CaseID": case["CaseID"],
        "Decision": decision,
        "AcceptanceStatusAtDecision": case["AcceptanceStatus"],
        "ActorID": actor_id,
        "DecidedAt": decided_at.isoformat(),
        "Comment": comment,
        "FailureReasonsAtDecision": case.get("FailureReasons", []),
        "ActualSnapshot": case.get("Actual", {}),
    }
