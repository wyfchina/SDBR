from __future__ import annotations

from datetime import datetime

from sdbr.master_data_validation import MaterialRequirement
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_authorization import ReleaseAuthorization
from sdbr.release_candidates import (
    MaterialAvailability,
    WipLimit,
    release_candidate_rows_from_schedule,
)
from sdbr.release_policy import release_policy_evidence, release_policy_settings
from sdbr.release_stability import ReleaseStabilityInput, evaluate_release_stability
from sdbr.schedule_output import (
    scheduled_order_rows_from_schedule,
    scheduled_work_order_rows_from_schedule,
)


def build_scheduled_work_order_workbench(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    audit_events: list[dict[str, object]],
    authorizations: list[ReleaseAuthorization],
) -> dict[str, object]:
    schedule = _dict(planning_run.get("Schedule"))
    order_master = {
        str(item.get("OrderID")): item
        for item in _dict_list(master_data_version.get("Orders"))
    }
    routing_by_product = _routing_by_product(master_data_version)
    release_by_order = {
        str(item.get("OrderID")): item.get("SuggestedReleaseDate")
        for item in _dict_list(schedule.get("ReleaseRecommendations"))
    }
    priority_by_order = {
        str(item.get("OrderID")): item
        for item in _dict_list(schedule.get("ExecutionPriorityQueue"))
    }
    authorized_orders = {
        item.order_id for item in authorizations if item.status == "Authorized"
    }
    overrides = _work_order_overrides(audit_events)
    rows = []
    for scheduled in scheduled_order_rows_from_schedule(schedule):
        order_id = str(scheduled["OrderID"])
        master = order_master.get(order_id, {})
        due = _parse_datetime(master.get("DueDate"))
        completion = _parse_datetime(scheduled.get("ScheduledEnd"))
        delta_days = None
        if due is not None and completion is not None:
            delta_days = round((completion - due).total_seconds() / 86400, 2)
        priority = priority_by_order.get(order_id, {})
        override = overrides.get(order_id, {})
        routing = routing_by_product.get(str(master.get("ProductID")), {})
        rows.append(
            {
                "OrderID": order_id,
                "ProductID": master.get("ProductID"),
                "Quantity": master.get("Quantity"),
                "OrderDate": master.get("OrderDate"),
                "PlannedReleaseAt": release_by_order.get(order_id),
                "FinalDemandDate": master.get("DueDate"),
                "PromiseDate": master.get("PromiseDate")
                or master.get("DueDate"),
                "PlannedStartAt": scheduled.get("ScheduledStart"),
                "PlannedCompletionAt": scheduled.get("ScheduledEnd"),
                "OnTimeStatus": (
                    "Late"
                    if delta_days is not None and delta_days > 0
                    else "OnTime"
                    if delta_days is not None
                    else "Unknown"
                ),
                "ScheduleDeltaDays": delta_days,
                "ReleaseStatus": (
                    "Authorized" if order_id in authorized_orders else "NotReleased"
                ),
                "ExecutionPriority": override.get("Priority")
                or priority.get("Rank"),
                "BufferZone": priority.get("Zone"),
                "RoutingID": routing.get("RoutingID"),
                "OrderFamily": master.get("OrderFamily"),
                "ResourceIDs": list(scheduled.get("ResourceIDs", [])),
                "IsLocked": bool(override.get("IsLocked", False)),
                "OperationCount": scheduled.get("OperationCount"),
                "TotalDurationMinutes": scheduled.get("TotalDurationMinutes"),
            }
        )
    return {
        "RunID": planning_run.get("RunID"),
        "Rows": rows,
        "ViewMetadata": {
            "GeneratedAt": schedule.get("GeneratedAt")
            or planning_run.get("CompletedAt"),
            "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
            "OperationalStateSnapshotID": planning_run.get(
                "OperationalStateSnapshotID"
            ),
            "IsStale": False,
        },
        "FilterOptions": {
            "Products": _distinct(rows, "ProductID"),
            "ReleaseStatuses": _distinct(rows, "ReleaseStatus"),
            "BufferZones": _distinct(rows, "BufferZone"),
            "RoutingIDs": _distinct(rows, "RoutingID"),
            "OrderFamilies": _distinct(rows, "OrderFamily"),
            "ResourceIDs": sorted(
                {
                    resource_id
                    for row in rows
                    for resource_id in row["ResourceIDs"]
                }
            ),
        },
    }


def build_scheduled_work_order_detail(
    *,
    order_id: str,
    workbench: dict[str, object],
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    audit_events: list[dict[str, object]],
    authorizations: list[ReleaseAuthorization],
) -> dict[str, object] | None:
    order = next(
        (
            item
            for item in _dict_list(workbench.get("Rows"))
            if item.get("OrderID") == order_id
        ),
        None,
    )
    if order is None:
        return None
    operations = [
        item
        for item in scheduled_work_order_rows_from_schedule(
            _dict(planning_run.get("Schedule"))
        )
        if item.get("OrderID") == order_id
    ]
    related_audit = [
        item
        for item in audit_events
        if order_id in _dict(item.get("Details")).get("OrderIDs", [])
    ]
    related_audit.sort(key=lambda item: str(item.get("OccurredAt", "")), reverse=True)
    master_order = next(
        (
            item
            for item in _dict_list(master_data_version.get("Orders"))
            if item.get("OrderID") == order_id
        ),
        {},
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
        "Order": order,
        "Operations": operations,
        "PlanningContext": {
            "RunID": planning_run.get("RunID"),
            "ProblemID": planning_run.get("ProblemID"),
            "SourceRunID": planning_run.get("SourceRunID"),
            "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
            "OperationalStateSnapshotID": planning_run.get(
                "OperationalStateSnapshotID"
            ),
            "ReleasePolicyVersionID": planning_run.get("ReleasePolicyVersionID"),
            "PublicationStatus": planning_run.get("PublicationStatus"),
            "SolverStatus": planning_run.get("SolverStatus"),
        },
        "CommercialContext": {
            "CustomerID": master_order.get("CustomerID"),
            "SalesOrderID": master_order.get("SalesOrderID"),
            "PromiseDate": master_order.get("PromiseDate") or master_order.get("DueDate"),
            "Priority": master_order.get("Priority"),
        },
        "ProductionContext": {
            "ProductID": master_order.get("ProductID") or order.get("ProductID"),
            "Quantity": master_order.get("Quantity") or order.get("Quantity"),
            "RoutingID": order.get("RoutingID"),
            "ResourceIDs": order.get("ResourceIDs", []),
            "IsLocked": order.get("IsLocked", False),
        },
        "ReleaseContext": (
            {
                "AuthorizationID": authorization.authorization_id,
                "ReleasedBy": authorization.released_by,
                "ReleasedAt": authorization.released_at.isoformat(),
                "DispatchStatus": authorization.status,
            }
            if authorization is not None
            else {
                "AuthorizationID": None,
                "DispatchStatus": order.get("ReleaseStatus"),
            }
        ),
        "Notes": master_order.get("Notes", []),
        "UserDefinedFields": master_order.get("UserDefinedFields", {}),
        "AuditEvents": related_audit,
    }


def build_release_management_workbench(
    *,
    planning_run: dict[str, object],
    evaluated_at: datetime,
    inventory_buffers: list[InventoryBufferPolicy],
    material_requirements: list[MaterialRequirement],
    wip_limits: list[WipLimit],
    material_availability: list[MaterialAvailability],
    operational_state_status: str,
    operational_state_captured_at: datetime,
    authorizations: list[ReleaseAuthorization],
    operational_state_snapshot_id: str | None = None,
    release_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    schedule = _dict(planning_run.get("Schedule"))
    candidates = release_candidate_rows_from_schedule(
        schedule=schedule,
        evaluated_at=evaluated_at,
        inventory_buffers=inventory_buffers,
        material_requirements=material_requirements,
        wip_limits=wip_limits,
        material_availability=material_availability,
        release_policy=release_policy,
    )
    policy_settings = release_policy_settings(release_policy)
    authorized_by_order = {
        item.order_id: item
        for item in authorizations
        if item.request_id == planning_run.get("RunID")
        and item.status == "Authorized"
    }
    schedule_orders = {
        str(item.get("OrderID")): item
        for item in _dict_list(schedule.get("ScheduledOrders"))
    }
    enriched = []
    for candidate in candidates:
        order_id = str(candidate["OrderID"])
        penetration, zone = _buffer_penetration(
            candidate,
            evaluated_at,
            release_policy=release_policy,
        )
        blocking = _blocking_reasons(
            candidate=candidate,
            operational_state_status=operational_state_status,
            release_policy=release_policy,
        )
        stability = _candidate_stability(
            candidate=candidate,
            evaluated_at=evaluated_at,
            gate_allowed=not blocking
            and candidate.get("RecommendedAction") == "ReadyForRelease",
            release_policy=release_policy,
        )
        authorization = authorized_by_order.get(order_id)
        demand_class = _demand_class(
            schedule_orders.get(order_id, {}).get("DemandClass")
            or candidate.get("DemandClass")
        )
        market_reason = _market_priority_reason(
            demand_class=demand_class,
            zone=zone,
            penetration=penetration,
        )
        enriched.append(
            {
                **candidate,
                "DemandClass": demand_class,
                "BufferZone": zone,
                "BufferPenetrationPercent": penetration,
                "MarketPriorityReason": market_reason,
                "BlockingReasons": blocking,
                "PolicyEvidence": release_policy_evidence(release_policy),
                "Stability": stability,
                "ReleaseStatus": (
                    "Authorized" if authorization is not None else "NotReleased"
                ),
                "AuthorizationID": (
                    authorization.authorization_id
                    if authorization is not None
                    else None
                ),
                "CanAuthorize": (
                    not blocking
                    and candidate.get("RecommendedAction") == "ReadyForRelease"
                    and authorization is None
                ),
            }
        )
    zone_rank = {"Late": 0, "Red": 1, "Yellow": 2, "Green": 3}
    enriched.sort(
        key=lambda item: (
            1 if item["ReleaseStatus"] == "Authorized" else 0,
            zone_rank.get(str(item["BufferZone"]), 4),
            -float(item["BufferPenetrationPercent"]),
            str(item["SuggestedReleaseAt"]),
        )
    )
    for rank, item in enumerate(enriched, start=1):
        item["ExecutionPriority"] = rank
        item["MarketPriorityRank"] = rank
    return {
        "RunID": planning_run.get("RunID"),
        "EvaluatedAt": evaluated_at.isoformat(),
        "OperationalStateSnapshotID": (
            operational_state_snapshot_id
            or planning_run.get("OperationalStateSnapshotID")
        ),
        "OperationalStateCapturedAt": operational_state_captured_at.isoformat(),
        "OperationalStateStatus": operational_state_status,
        "ReleasePolicyVersionID": (
            release_policy.get("VersionID") if release_policy else None
        ),
        "ReleasePolicySnapshot": release_policy,
        "PolicyEvidence": release_policy_evidence(release_policy),
        "Summary": {
            "TotalCount": len(enriched),
            "ReadyCount": sum(1 for item in enriched if item["CanAuthorize"]),
            "BlockedCount": sum(
                1
                for item in enriched
                if item["ReleaseStatus"] != "Authorized"
                and not item["CanAuthorize"]
            ),
            "AuthorizedCount": sum(
                1 for item in enriched if item["ReleaseStatus"] == "Authorized"
            ),
        },
        "Candidates": enriched,
    }


def _work_order_overrides(
    audit_events: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for event in sorted(audit_events, key=lambda item: str(item.get("OccurredAt", ""))):
        details = _dict(event.get("Details"))
        for order_id in details.get("OrderIDs", []):
            override = result.setdefault(str(order_id), {})
            if event.get("Action") == "ScheduledWorkOrdersLocked":
                override["IsLocked"] = True
            elif event.get("Action") == "ScheduledWorkOrdersUnlocked":
                override["IsLocked"] = False
            elif event.get("Action") == "ScheduledWorkOrdersPrioritySet":
                override["Priority"] = details.get("Priority")
    return result


def _routing_by_product(
    master_data_version: dict[str, object],
) -> dict[str, dict[str, object]]:
    result = {}
    for routing in _dict_list(master_data_version.get("Routings")):
        product_id = str(routing.get("ProductID"))
        if product_id not in result or routing.get("IsPrimary") is True:
            result[product_id] = routing
    return result


def _buffer_penetration(
    candidate: dict[str, object],
    evaluated_at: datetime,
    release_policy: dict[str, object] | None = None,
) -> tuple[float, str]:
    release_at = _parse_datetime(candidate.get("SuggestedReleaseAt"))
    start_at = _parse_datetime(candidate.get("ScheduledStart"))
    if release_at is None or start_at is None or start_at <= release_at:
        return 0.0, "Green"
    penetration = round(
        (evaluated_at - release_at).total_seconds()
        / (start_at - release_at).total_seconds()
        * 100,
        2,
    )
    if penetration > 100:
        return penetration, "Late"
    settings = release_policy_settings(release_policy)
    green_boundary = max(0.0, settings.green_zone_ratio * 100)
    yellow_boundary = green_boundary + max(0.0, settings.yellow_zone_ratio * 100)
    if penetration >= yellow_boundary:
        return penetration, "Red"
    if penetration >= green_boundary:
        return penetration, "Yellow"
    return max(penetration, 0.0), "Green"


def _demand_class(value: object) -> str:
    text = str(value or "MTO").upper()
    if text in {"MTA", "MTS", "STOCKREPLENISHMENT"}:
        return "MTA"
    return "MTO"


def _market_priority_reason(
    *,
    demand_class: str,
    zone: str,
    penetration: float,
) -> str:
    class_label = "MTA补货" if demand_class == "MTA" else "MTO工单"
    if zone in {"Late", "Red"}:
        return f"{zone} 区 {class_label}，渗透率 {penetration:.2f}%，优先保护市场承诺"
    if zone == "Yellow":
        return f"黄区 {class_label}，进入释放关注窗口"
    return f"绿区 {class_label}，保持观察"


def _blocking_reasons(
    *,
    candidate: dict[str, object],
    operational_state_status: str,
    release_policy: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    reasons = []
    if operational_state_status != "Fresh":
        action = (
            "RefreshOperationalSnapshotAndReevaluate"
            if operational_state_status == "Stale"
            else "CorrectEvaluationTimeOrSnapshot"
        )
        reasons.append(
            {
                "Code": f"OPERATIONAL_SNAPSHOT_{operational_state_status.upper()}",
                "Category": "Data",
                "Details": {
                    "RecommendedAction": action,
                    "RequiresReschedule": False,
                },
            }
        )
    if candidate.get("RopeStatus") == "Early":
        reasons.append(
            {
                "Code": "ROPE_TIME_NOT_REACHED",
                "Category": "Rope",
                "Details": {
                    "MinutesUntilRelease": candidate.get("MinutesUntilRelease"),
                    "RopeBufferMinutes": release_policy_settings(
                        release_policy
                    ).rope_buffer_minutes,
                    "ReleasePolicyVersionID": release_policy_settings(
                        release_policy
                    ).version_id,
                },
            }
        )
    material_status = candidate.get("MaterialStatus")
    if material_status == "Blocked":
        reasons.append(
            {
                "Code": "MATERIAL_SHORTAGE",
                "Category": "Material",
                "Details": {
                    "Risks": candidate.get("InventoryRisks", []),
                    "MaterialLookaheadMinutes": release_policy_settings(
                        release_policy
                    ).material_lookahead_minutes,
                },
            }
        )
    elif material_status == "PendingInbound":
        reasons.append(
            {
                "Code": "MATERIAL_INBOUND_PENDING",
                "Category": "Material",
                "Details": {
                    "Risks": candidate.get("InventoryRisks", []),
                    "MaterialLookaheadMinutes": release_policy_settings(
                        release_policy
                    ).material_lookahead_minutes,
                },
            }
        )
    if candidate.get("WipStatus") == "Blocked":
        reasons.append(
            {
                "Code": "WIP_LIMIT_EXCEEDED",
                "Category": "WIP",
                "Details": {
                    "Risks": candidate.get("WipRisks", []),
                    "PolicyMaxWipCount": release_policy_settings(
                        release_policy
                    ).max_wip_count,
                },
            }
        )
    return reasons


def _candidate_stability(
    *,
    candidate: dict[str, object],
    evaluated_at: datetime,
    gate_allowed: bool,
    release_policy: dict[str, object] | None,
) -> dict[str, object] | None:
    suggested_release_at = _parse_datetime(candidate.get("SuggestedReleaseAt"))
    if suggested_release_at is None:
        return None
    settings = release_policy_settings(release_policy)
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id=str(candidate.get("OrderID")),
            planned_release_at=suggested_release_at,
            evaluated_release_at=evaluated_at,
            gate_allowed=gate_allowed,
            consecutive_blocked_count=0 if gate_allowed else 1,
        ),
        policy=settings.stability_policy,
    )
    return {
        "DeviationMinutes": result.deviation_minutes,
        "AbsoluteDeviationMinutes": result.absolute_deviation_minutes,
        "TimingStatus": result.timing_status,
        "Severity": result.severity,
        "Action": result.action,
        "ReplanRequired": result.replan_required,
        "ReasonCode": result.reason_code,
        "Policy": release_policy_evidence(release_policy)["StabilityPolicy"],
    }


def _distinct(rows: list[dict[str, object]], key: str) -> list[object]:
    return sorted(
        {row[key] for row in rows if row.get(key) is not None}, key=str
    )


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
