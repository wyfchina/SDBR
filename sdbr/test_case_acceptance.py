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
    if planning_run.get("Status") != "Completed" or not isinstance(
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

    schedule = planning_run["Schedule"]
    if isinstance(schedule, dict):
        actual["OrderCount"] = schedule.get("OrderCount")
        actual["GeneratedAt"] = schedule.get("GeneratedAt")

    release = _release_summary(
        planning_run=planning_run,
        master_data_versions=master_data_versions,
        operational_state_snapshots=operational_state_snapshots,
        release_authorizations=release_authorizations,
        evaluated_at=evaluated_at,
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
