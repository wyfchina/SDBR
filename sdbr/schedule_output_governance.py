from __future__ import annotations

from datetime import datetime, timezone

from sdbr.plan_publication import build_plan_publication_view
from sdbr.release_authorization import ReleaseAuthorization
from sdbr.schedule_output import (
    scheduled_order_rows_from_schedule,
    scheduled_work_order_rows_from_schedule,
)


def build_schedule_output_governance(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object] | None,
    operational_state_snapshot: object | None,
    release_authorizations: list[ReleaseAuthorization],
    audit_events: list[dict[str, object]],
    superseded_by_run_id: str | None = None,
) -> dict[str, object]:
    publication = build_plan_publication_view(
        planning_run=planning_run,
        superseded_by_run_id=superseded_by_run_id,
    )
    schedule = _dict(planning_run.get("Schedule"))
    completeness = _output_completeness(
        planning_run=planning_run,
        schedule=schedule,
        master_data_version=master_data_version,
        operational_state_snapshot=operational_state_snapshot,
    )
    scoped_authorizations = _authorizations_for_run(
        release_authorizations=release_authorizations,
        run_id=str(planning_run.get("RunID")),
    )
    governance = {
        "RunID": planning_run.get("RunID"),
        "ProblemID": planning_run.get("ProblemID"),
        "PlanningRunStatus": planning_run.get("Status"),
        "SolverBackendID": planning_run.get("SolverBackendID"),
        "SolverStatus": planning_run.get("SolverStatus"),
        "ScheduleFingerprint": publication.get("ScheduleFingerprint"),
        "OutputPackageID": _output_package_id(planning_run, publication),
        "OutputAvailability": (
            "Available" if completeness["IsOutputAvailable"] else "Unavailable"
        ),
        "Completeness": completeness,
        "Publication": {
            "PublicationStatus": publication.get("PublicationStatus"),
            "AllowedActions": publication.get("AllowedActions", []),
            "PublicationPackage": publication.get("PublicationPackage"),
            "SupersedesRunID": publication.get("SupersedesRunID"),
            "SupersededByRunID": publication.get("SupersededByRunID"),
        },
        "Release": _release_governance(
            schedule=schedule,
            release_authorizations=scoped_authorizations,
        ),
        "Audit": _audit_governance(audit_events),
        "FrozenInputs": _frozen_input_summary(planning_run),
    }
    return governance


def build_schedule_output_package(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object] | None,
    operational_state_snapshot: object | None,
    release_authorizations: list[ReleaseAuthorization],
    audit_events: list[dict[str, object]],
    generated_at: datetime | None = None,
    superseded_by_run_id: str | None = None,
) -> dict[str, object]:
    governance = build_schedule_output_governance(
        planning_run=planning_run,
        master_data_version=master_data_version,
        operational_state_snapshot=operational_state_snapshot,
        release_authorizations=release_authorizations,
        audit_events=audit_events,
        superseded_by_run_id=superseded_by_run_id,
    )
    if not governance["Completeness"]["IsOutputAvailable"]:
        return {
            "RunID": planning_run.get("RunID"),
            "Status": "OutputPackageUnavailable",
            "Completeness": governance["Completeness"],
        }
    schedule = _dict(planning_run.get("Schedule"))
    generated = generated_at or datetime.now(timezone.utc)
    work_orders = scheduled_order_rows_from_schedule(schedule)
    operations = scheduled_work_order_rows_from_schedule(schedule)
    return {
        "PackageID": governance["OutputPackageID"],
        "PackageType": "InternalScheduleOutputPackage",
        "RunID": planning_run.get("RunID"),
        "ProblemID": planning_run.get("ProblemID"),
        "ScheduleFingerprint": governance["ScheduleFingerprint"],
        "GeneratedAt": generated.isoformat(),
        "PublicationStatus": governance["Publication"]["PublicationStatus"],
        "WorkOrders": _work_order_output_rows(
            work_orders=work_orders,
            master_data_version=master_data_version or {},
            schedule=schedule,
        ),
        "Operations": operations,
        "ResourceLoadSummary": _resource_load_summary(schedule),
        "GanttSummary": _gantt_summary(schedule),
        "ReleaseRecommendations": _dict_list(
            schedule.get("ReleaseRecommendations")
        ),
        "FrozenInputs": governance["FrozenInputs"],
        "Diagnostics": {
            "SolverDiagnostics": _dict_list(schedule.get("SolverDiagnostics")),
            "Risks": {
                "BottleneckCandidates": _dict_list(
                    schedule.get("BottleneckCandidates")
                ),
                "BufferSummary": _dict(schedule.get("BufferSummary")),
            },
        },
        "Governance": governance,
        "ExternalDelivery": {
            "Status": "NotSent",
            "Reason": "External ERP/MES delivery is owned by BE-INT-* integrations.",
        },
    }


def output_context_for_order(
    *,
    planning_run: dict[str, object],
    superseded_by_run_id: str | None = None,
) -> dict[str, object]:
    publication = build_plan_publication_view(
        planning_run=planning_run,
        superseded_by_run_id=superseded_by_run_id,
    )
    return {
        "OutputPackageID": _output_package_id(planning_run, publication),
        "ScheduleFingerprint": publication.get("ScheduleFingerprint"),
        "PublicationStatus": publication.get("PublicationStatus"),
        "SupersedesRunID": publication.get("SupersedesRunID"),
        "SupersededByRunID": publication.get("SupersededByRunID"),
        "IsSuperseded": publication.get("PublicationStatus") == "Superseded"
        or publication.get("SupersededByRunID") is not None,
    }


def audit_context_for_order(
    *,
    order_id: str,
    audit_events: list[dict[str, object]],
) -> dict[str, object]:
    related = [
        event
        for event in audit_events
        if order_id in _dict(event.get("Details")).get("OrderIDs", [])
    ]
    return {
        "OrderAuditEventCount": len(related),
        "Events": sorted(
            related,
            key=lambda item: str(item.get("OccurredAt", "")),
            reverse=True,
        ),
        "Actions": sorted({str(item.get("Action")) for item in related}),
    }


def release_context_for_order(
    *,
    order_id: str,
    planning_run: dict[str, object],
    authorizations: list[ReleaseAuthorization],
) -> dict[str, object]:
    schedule = _dict(planning_run.get("Schedule"))
    recommendation = next(
        (
            item
            for item in _dict_list(schedule.get("ReleaseRecommendations"))
            if str(item.get("OrderID")) == order_id
        ),
        None,
    )
    authorization = next(
        (
            item
            for item in authorizations
            if item.request_id == planning_run.get("RunID")
            and item.order_id == order_id
            and item.status == "Authorized"
        ),
        None,
    )
    return {
        "SuggestedReleaseAt": (
            recommendation.get("SuggestedReleaseDate")
            if isinstance(recommendation, dict)
            else None
        ),
        "Authorization": (
            {
                "AuthorizationID": authorization.authorization_id,
                "ReleasedBy": authorization.released_by,
                "ReleasedAt": authorization.released_at.isoformat(),
                "Status": authorization.status,
                "OperationalStateSnapshotID": authorization.operational_state_snapshot_id,
                "OperationalStateCapturedAt": authorization.operational_state_captured_at,
                "ReleasePolicyVersionID": authorization.release_policy_version_id,
            }
            if authorization is not None
            else None
        ),
        "LatestReleaseEvaluationSnapshotID": (
            authorization.operational_state_snapshot_id
            if authorization is not None
            else planning_run.get("OperationalStateSnapshotID")
        ),
    }


def _output_completeness(
    *,
    planning_run: dict[str, object],
    schedule: dict[str, object],
    master_data_version: dict[str, object] | None,
    operational_state_snapshot: object | None,
) -> dict[str, object]:
    checks = [
        _check(
            "PLANNING_RUN_COMPLETED",
            planning_run.get("Status") == "Completed",
            "Planning Run must be Completed.",
        ),
        _check("SCHEDULE_PRESENT", bool(schedule), "Schedule payload must exist."),
        _check(
            "WORK_ORDERS_PRESENT",
            bool(scheduled_order_rows_from_schedule(schedule)),
            "Schedule must contain at least one work order.",
        ),
        _check(
            "OPERATIONS_PRESENT",
            bool(scheduled_work_order_rows_from_schedule(schedule)),
            "Schedule must contain operation rows.",
        ),
        _check(
            "MASTER_DATA_VERSION_PRESENT",
            bool(master_data_version),
            "Master data version must be available.",
        ),
        _check(
            "OPERATIONAL_STATE_SNAPSHOT_PRESENT",
            operational_state_snapshot is not None,
            "Operational state snapshot must be available.",
        ),
    ]
    return {
        "IsOutputAvailable": all(item["Passed"] for item in checks),
        "Checks": checks,
        "FailureCodes": [
            str(item["CheckID"]) for item in checks if item["Passed"] is False
        ],
    }


def _check(check_id: str, passed: bool, message: str) -> dict[str, object]:
    return {"CheckID": check_id, "Passed": bool(passed), "Message": message}


def _release_governance(
    *,
    schedule: dict[str, object],
    release_authorizations: list[ReleaseAuthorization],
) -> dict[str, object]:
    recommendation_count = len(_dict_list(schedule.get("ReleaseRecommendations")))
    authorized_count = len(release_authorizations)
    return {
        "RecommendationCount": recommendation_count,
        "AuthorizedCount": authorized_count,
        "UnauthorizedCount": max(recommendation_count - authorized_count, 0),
        "AuthorizedOrderIDs": sorted({item.order_id for item in release_authorizations}),
        "LatestEvaluationSnapshotIDs": sorted(
            {
                item.operational_state_snapshot_id
                for item in release_authorizations
                if item.operational_state_snapshot_id
            }
        ),
        "UsedLatestOperationalStateForAuthorization": any(
            item.operational_state_snapshot_id is not None
            for item in release_authorizations
        ),
    }


def _audit_governance(audit_events: list[dict[str, object]]) -> dict[str, object]:
    actions = [str(item.get("Action")) for item in audit_events]
    return {
        "AuditEventCount": len(audit_events),
        "ScenarioSelectionCount": actions.count("ScheduleScenarioSelected"),
        "WorkOrderCommandCount": sum(
            1 for action in actions if action.startswith("ScheduledWorkOrders")
        ),
        "PublicationActionCount": sum(
            1 for action in actions if action.startswith("PlanPublication")
        ),
        "ReleaseAuthorizationCount": sum(
            1 for action in actions if action.endswith("ReleaseAuthorized")
        ),
        "Actions": sorted(set(actions)),
        "RecentEvents": sorted(
            audit_events,
            key=lambda item: str(item.get("OccurredAt", "")),
            reverse=True,
        )[:10],
    }


def _frozen_input_summary(planning_run: dict[str, object]) -> dict[str, object]:
    return {
        "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
        "OperationalStateSnapshotID": planning_run.get("OperationalStateSnapshotID"),
        "ReleasePolicyVersionID": planning_run.get("ReleasePolicyVersionID"),
        "ObjectiveStrategyID": planning_run.get("ObjectiveStrategyID", "balanced"),
        "FrozenSchedulingStrategy": planning_run.get("FrozenSchedulingStrategy"),
        "FrozenCalendarOverrideCount": len(
            _dict_list(planning_run.get("FrozenCalendarOverrides"))
        ),
        "SetupTransitionCount": len(_dict_list(planning_run.get("SetupTransitions"))),
    }


def _work_order_output_rows(
    *,
    work_orders: list[dict[str, object]],
    master_data_version: dict[str, object],
    schedule: dict[str, object],
) -> list[dict[str, object]]:
    orders_by_id = {
        str(item.get("OrderID")): item
        for item in _dict_list(master_data_version.get("Orders"))
    }
    release_by_order = {
        str(item.get("OrderID")): item.get("SuggestedReleaseDate")
        for item in _dict_list(schedule.get("ReleaseRecommendations"))
    }
    rows = []
    for row in work_orders:
        order_id = str(row.get("OrderID"))
        master = orders_by_id.get(order_id, {})
        rows.append(
            {
                **row,
                "ProductID": master.get("ProductID"),
                "Quantity": master.get("Quantity"),
                "DueDate": master.get("DueDate"),
                "SuggestedReleaseAt": release_by_order.get(order_id),
            }
        )
    return rows


def _resource_load_summary(schedule: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for row in _dict_list(schedule.get("LoadGraphRows")):
        cells = _dict_list(row.get("Cells"))
        rows.append(
            {
                "ResourceID": row.get("ResourceID"),
                "ResourceName": row.get("ResourceName"),
                "IsConstraint": bool(row.get("IsConstraint", False)),
                "RequiredMinutes": sum(
                    int(cell.get("RequiredMinutes") or 0) for cell in cells
                ),
                "CapacityMinutes": sum(
                    int(cell.get("CapacityMinutes") or 0) for cell in cells
                ),
                "OverloadMinutes": sum(
                    int(cell.get("OverloadMinutes") or 0) for cell in cells
                ),
            }
        )
    return rows


def _gantt_summary(schedule: dict[str, object]) -> dict[str, object]:
    rows = _dict_list(schedule.get("GanttRows"))
    bars = [
        bar
        for row in rows
        for bar in _dict_list(row.get("Bars"))
    ]
    return {
        "ResourceCount": len(rows),
        "OperationBarCount": len(bars),
        "Start": min((str(item.get("Start")) for item in bars), default=None),
        "End": max((str(item.get("End")) for item in bars), default=None),
    }


def _authorizations_for_run(
    *,
    release_authorizations: list[ReleaseAuthorization],
    run_id: str,
) -> list[ReleaseAuthorization]:
    return [
        item
        for item in release_authorizations
        if item.request_id == run_id and item.status == "Authorized"
    ]


def _output_package_id(
    planning_run: dict[str, object],
    publication: dict[str, object],
) -> str | None:
    fingerprint = publication.get("ScheduleFingerprint")
    if not fingerprint:
        return None
    return f"OUT-{planning_run.get('RunID')}-{str(fingerprint)[:12]}"


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
