from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from sdbr.buffer_execution_view import buffer_zone
from sdbr.release_authorization import ReleaseAuthorization
from sdbr.schedule_output import scheduled_work_order_rows_from_schedule


ZONE_RANK = {"Late": 0, "Red": 1, "Yellow": 2, "Green": 3, "Early": 4}
DISPATCH_REPLAN_THRESHOLD = 2


def build_mes_dispatch_priority_queue(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    release_workbench: dict[str, object],
    authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> dict[str, object]:
    schedule = _dict(planning_run.get("Schedule"))
    resources = _resources_by_id(master_data_version)
    authorizations_by_order = {
        authorization.order_id: authorization
        for authorization in authorizations
        if authorization.request_id == planning_run.get("RunID")
        and authorization.status == "Authorized"
    }
    release_candidates = {
        str(candidate.get("OrderID")): candidate
        for candidate in _dict_list(release_workbench.get("Candidates"))
    }
    open_operations = [
        operation
        for operation in scheduled_work_order_rows_from_schedule(schedule)
        if not _operation_completed(operation, execution_events)
    ]
    plan_rank = _plan_rank_by_resource(open_operations)

    rows = []
    for operation in open_operations:
        order_id = str(operation.get("OrderID"))
        resource_id = str(operation.get("ResourceID"))
        authorization = authorizations_by_order.get(order_id)
        candidate = release_candidates.get(order_id, {})
        zone = _dispatch_zone(
            authorization=authorization,
            candidate=candidate,
            evaluated_at=evaluated_at,
        )
        penetration = float(candidate.get("BufferPenetrationPercent") or 0)
        release_status = "Authorized" if authorization is not None else "CandidateOnly"
        gate = _dispatch_gate(candidate=candidate, authorization=authorization)
        shop_floor = _shop_floor_status(operation=operation, events=execution_events)
        if gate["Allowed"] and shop_floor["DispatchBlockingReason"] is not None:
            gate = {
                "Allowed": False,
                "Status": str(shop_floor["DispatchBlockingReason"]),
                "BlockingReasons": [
                    {
                        "Code": shop_floor["DispatchBlockingReason"],
                        "Category": "MES",
                        "Details": {
                            "CurrentExecutionStatus": shop_floor["ExecutionStatus"],
                        },
                    }
                ],
            }
        rows.append(
            {
                "OrderID": order_id,
                "OperationID": operation.get("OperationID"),
                "ResourceID": resource_id,
                "WorkCenterID": resource_id,
                "ResourceName": resources.get(resource_id, {}).get("Name"),
                "IsConstraintResource": bool(resources.get(resource_id, {}).get("IsConstraint")),
                "ScheduledStart": operation.get("Start"),
                "ScheduledEnd": operation.get("End"),
                "DurationMinutes": operation.get("DurationMinutes"),
                "AuthorizationID": (
                    authorization.authorization_id if authorization is not None else None
                ),
                "ReleaseStatus": release_status,
                "DispatchEligibility": (
                    "Dispatchable" if gate["Allowed"] and authorization is not None else "CandidateOnly"
                ),
                "ExecutionStatus": shop_floor["ExecutionStatus"],
                "ArrivalStatus": shop_floor["ArrivalStatus"],
                "CurrentProcessing": shop_floor["CurrentProcessing"],
                "LastMesEventType": shop_floor["LastEventType"],
                "LastMesEventAt": shop_floor["LastEventAt"],
                "DispatchRecommendation": None,
                "RecommendationReason": None,
                "BufferZone": zone,
                "BufferPenetrationPercent": penetration,
                "DemandClass": candidate.get("DemandClass") or "MTO",
                "MarketPriorityRank": candidate.get("MarketPriorityRank"),
                "MarketPriorityReason": candidate.get("MarketPriorityReason"),
                "LatestGateStatus": gate["Status"],
                "LatestGateBlockingReasons": gate["BlockingReasons"],
                "PlanSequence": plan_rank[_operation_key(operation)],
                "CustomerDueDate": _order_due_date(master_data_version, order_id),
            }
        )

    dispatchable = [row for row in rows if row["DispatchEligibility"] == "Dispatchable"]
    candidates = [row for row in rows if row["DispatchEligibility"] != "Dispatchable"]
    dispatchable.sort(key=_dispatch_sort_key)
    candidates.sort(key=_candidate_sort_key)

    resources_payload = []
    for resource_id in sorted({str(row["ResourceID"]) for row in rows}):
        queue_rows = [row for row in dispatchable if row["ResourceID"] == resource_id]
        candidate_rows = [row for row in candidates if row["ResourceID"] == resource_id]
        _enrich_dispatch_conflicts(queue_rows, execution_events)
        for rank, row in enumerate(queue_rows, start=1):
            row["DispatchRank"] = rank
            _enrich_dispatch_recommendation(row)
        for row in candidate_rows:
            _enrich_dispatch_recommendation(row)
        resources_payload.append(
            {
                "ResourceID": resource_id,
                "WorkCenterID": resource_id,
                "ResourceName": resources.get(resource_id, {}).get("Name"),
                "IsConstraintResource": bool(resources.get(resource_id, {}).get("IsConstraint")),
                "Queue": queue_rows,
                "CandidateWarnings": candidate_rows,
                "QueueCount": len(queue_rows),
                "CandidateWarningCount": len(candidate_rows),
            }
        )

    return {
        "RunID": planning_run.get("RunID"),
        "EvaluatedAt": evaluated_at.isoformat(),
        "OperationalStateSnapshotID": release_workbench.get("OperationalStateSnapshotID"),
        "ReleasePolicyVersionID": release_workbench.get("ReleasePolicyVersionID"),
        "DispatchPolicy": {
            "PriorityBasis": [
                "AuthorizedRelease",
                "BufferZone",
                "BufferPenetration",
                "ConstraintResourceScheduledStart",
                "CustomerDueDate",
            ],
            "AllowsQueueJump": True,
            "ReleaseIsHardGate": True,
            "RecheckMaterialAndWipBeforeIssue": True,
            "ReplanSuggestionThresholdExclusive": DISPATCH_REPLAN_THRESHOLD,
            "MesReceiptEvents": [
                "DispatchAccepted",
                "StartedOperation",
                "CompletedOperation",
                "DispatchRejected",
                "ExceptionReported",
            ],
        },
        "Summary": {
            "ResourceCount": len(resources_payload),
            "DispatchableOperationCount": len(dispatchable),
            "CandidateWarningCount": len(candidates),
            "QueueJumpSuggestionCount": sum(
                1 for row in dispatchable if row["ConflictResult"] == "SuggestQueueJump"
            ),
            "PlannerConfirmationCount": sum(
                1 for row in dispatchable if row["RequiresPlannerConfirmation"]
            ),
            "ReplanSuggestionCount": sum(
                1 for row in dispatchable if row["ConflictResult"] == "NeedsReplan"
            ),
        },
        "Resources": resources_payload,
    }


def build_mes_dispatch_suggestion_package(
    *,
    dispatch_workbench: dict[str, object],
    schedule_fingerprint: str | None = None,
    generated_at: datetime,
    target_system: str = "MES-MOCK",
) -> dict[str, object]:
    run_id = str(dispatch_workbench.get("RunID"))
    fingerprint = schedule_fingerprint or ""
    package_id = f"MES-DISPATCH-{run_id}-{_package_digest(dispatch_workbench, fingerprint)}"
    resource_queues = []
    for resource in _dict_list(dispatch_workbench.get("Resources")):
        queue = [
            _suggestion_row(row)
            for row in _dict_list(resource.get("Queue"))
        ]
        warnings = [
            _suggestion_row(row)
            for row in _dict_list(resource.get("CandidateWarnings"))
        ]
        resource_queues.append(
            {
                "ResourceID": resource.get("ResourceID"),
                "WorkCenterID": resource.get("WorkCenterID"),
                "ResourceName": resource.get("ResourceName"),
                "IsConstraintResource": resource.get("IsConstraintResource"),
                "Queue": queue,
                "CandidateWarnings": warnings,
                "QueueCount": len(queue),
                "CandidateWarningCount": len(warnings),
            }
        )
    return {
        "PackageID": package_id,
        "PackageType": "MESDispatchSuggestionPackage",
        "MessageType": "DispatchQueueIssued",
        "RunID": run_id,
        "ScheduleFingerprint": fingerprint or None,
        "OperationalStateSnapshotID": dispatch_workbench.get("OperationalStateSnapshotID"),
        "ReleasePolicyVersionID": dispatch_workbench.get("ReleasePolicyVersionID"),
        "GeneratedAt": generated_at.isoformat(),
        "TargetSystem": target_system,
        "DeliveryMode": "MockAPIRecommendationOnly",
        "SendsToMes": False,
        "DispatchPolicy": dispatch_workbench.get("DispatchPolicy"),
        "Summary": dispatch_workbench.get("Summary"),
        "ResourceQueues": resource_queues,
        "RecommendedActions": _recommended_actions(resource_queues),
        "CanonicalPayloadVersion": "MES-DISPATCH-SUGGESTION-V1",
    }


def _enrich_dispatch_conflicts(
    rows: list[dict[str, object]],
    execution_events: list[dict[str, object]],
) -> None:
    consecutive_jumps_by_resource = _consecutive_queue_jumps_by_resource(execution_events)
    for dispatch_rank, row in enumerate(rows, start=1):
        plan_sequence = int(row["PlanSequence"])
        is_queue_jump = dispatch_rank < plan_sequence
        row["PlanSequenceDelta"] = plan_sequence - dispatch_rank
        row["QueueJumpSuggested"] = is_queue_jump
        row["RequiresPlannerConfirmation"] = False
        row["PlannerConfirmationReasons"] = []
        if not is_queue_jump:
            row["ConflictResult"] = "FollowPlan"
            row["ConflictResultLabelZh"] = "按计划执行"
            continue
        if int(consecutive_jumps_by_resource.get(str(row["ResourceID"]), 0)) > DISPATCH_REPLAN_THRESHOLD:
            row["ConflictResult"] = "NeedsReplan"
            row["ConflictResultLabelZh"] = "需要重排"
        else:
            row["ConflictResult"] = "SuggestQueueJump"
            row["ConflictResultLabelZh"] = "建议插队"
        if row["IsConstraintResource"]:
            row["RequiresPlannerConfirmation"] = True
            row["PlannerConfirmationReasons"] = [
                "ConstraintResourceSetupOrIdleRisk",
                "RedZoneCanOverrideSetupLossOnlyAfterPlannerConfirmation",
            ]


def _enrich_dispatch_recommendation(row: dict[str, object]) -> None:
    if row.get("DispatchEligibility") != "Dispatchable":
        row["DispatchRecommendation"] = "Hold"
        status = row.get("LatestGateStatus")
        if status == "ReleaseNotAuthorized":
            row["RecommendationReason"] = "未授权释放，暂不进入 MES 正式派工队列"
        elif status == "ArrivalNotConfirmed":
            row["RecommendationReason"] = "缺少现场到达确认，作为候选预警"
        elif status == "DispatchRejected":
            row["RecommendationReason"] = "MES 已拒绝派工，需处理原因后再派工"
        elif status == "ExceptionReported":
            row["RecommendationReason"] = "MES 已上报异常，需处理异常后再派工"
        elif row.get("LatestGateBlockingReasons"):
            row["RecommendationReason"] = _gate_blocking_recommendation_reason(row)
        else:
            row["RecommendationReason"] = "暂不满足正式派工条件"
        return
    conflict = row.get("ConflictResult")
    if conflict == "NeedsReplan":
        row["DispatchRecommendation"] = "ReviewAndReplan"
        row["RecommendationReason"] = "连续插队已超过阈值，建议调度员复核并重排"
    elif conflict == "SuggestQueueJump":
        row["DispatchRecommendation"] = "QueueJump"
        row["RecommendationReason"] = "缓冲风险高于计划顺序，建议插队加工"
    else:
        row["DispatchRecommendation"] = "FollowPlan"
        row["RecommendationReason"] = "释放、物料、WIP 和现场状态通过，按计划顺序加工"


def _gate_blocking_recommendation_reason(row: dict[str, object]) -> str:
    codes = {
        str(reason.get("Code"))
        for reason in _dict_list(row.get("LatestGateBlockingReasons"))
    }
    if "WIP_LIMIT_EXCEEDED" in codes:
        return "释放后 WIP 将超过上限，保留为候选预警，暂不进入 MES 正式派工队列"
    if "MATERIAL_SHORTAGE" in codes:
        return "物料可用性未通过，保留为候选预警，暂不进入 MES 正式派工队列"
    if "MATERIAL_INBOUND_PENDING" in codes:
        return "物料仍在途中，保留为候选预警，暂不进入 MES 正式派工队列"
    if any(code.startswith("OPERATIONAL_SNAPSHOT_") for code in codes):
        return "运行状态快照不可用，请刷新快照并重新评估后再派工"
    return "最新释放门控未通过，保留为候选预警，暂不进入 MES 正式派工队列"


def _dispatch_sort_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        ZONE_RANK.get(str(row["BufferZone"]), 9),
        -float(row["BufferPenetrationPercent"] or 0),
        str(row.get("ScheduledStart") or ""),
        str(row.get("CustomerDueDate") or ""),
        str(row.get("OrderID") or ""),
        str(row.get("OperationID") or ""),
    )


def _candidate_sort_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        ZONE_RANK.get(str(row["BufferZone"]), 9),
        str(row.get("ScheduledStart") or ""),
        str(row.get("OrderID") or ""),
    )


def _dispatch_gate(
    *,
    candidate: dict[str, object],
    authorization: ReleaseAuthorization | None,
) -> dict[str, object]:
    blocking = _dict_list(candidate.get("BlockingReasons"))
    if authorization is None:
        return {
            "Allowed": False,
            "Status": "ReleaseNotAuthorized",
            "BlockingReasons": blocking,
        }
    if blocking:
        return {
            "Allowed": False,
            "Status": "LatestOperationalStateBlocked",
            "BlockingReasons": blocking,
        }
    if candidate.get("RecommendedAction") != "ReadyForRelease":
        return {
            "Allowed": False,
            "Status": "LatestOperationalStateNotReady",
            "BlockingReasons": blocking,
        }
    return {"Allowed": True, "Status": "Clear", "BlockingReasons": []}


def _dispatch_zone(
    *,
    authorization: ReleaseAuthorization | None,
    candidate: dict[str, object],
    evaluated_at: datetime,
) -> str:
    if candidate.get("BufferZone") is not None:
        return str(candidate["BufferZone"])
    if authorization is None:
        return "Early"
    return buffer_zone(
        suggested_release_at=authorization.suggested_release_at,
        scheduled_start=authorization.scheduled_start,
        evaluated_at=evaluated_at,
    )


def _operation_completed(
    operation: dict[str, object],
    execution_events: list[dict[str, object]],
) -> bool:
    order_id = operation.get("OrderID")
    operation_id = operation.get("OperationID")
    return any(
        event.get("EventType") in {"CompletedOperation", "Shipped"}
        and event.get("OrderID") == order_id
        and (
            event.get("OperationID") in {None, operation_id}
            or event.get("OperationID") == operation_id
        )
        for event in execution_events
    )


def _shop_floor_status(
    *,
    operation: dict[str, object],
    events: list[dict[str, object]],
) -> dict[str, object]:
    order_id = operation.get("OrderID")
    operation_id = operation.get("OperationID")
    resource_id = operation.get("ResourceID")
    relevant = [
        event
        for event in events
        if event.get("OrderID") == order_id
        and (
            event.get("OperationID") in {None, operation_id}
            or event.get("OperationID") == operation_id
        )
        and (
            event.get("ResourceID") in {None, resource_id}
            or event.get("ResourceID") == resource_id
        )
    ]
    last = max(relevant, key=lambda item: str(item.get("EventAt") or ""), default={})
    event_type = last.get("EventType")
    status = "NotArrived"
    arrival = "MissingArrivalConfirmation"
    blocking: str | None = "ArrivalNotConfirmed"
    processing = False
    if event_type in {"ArrivedBuffer", "DispatchAccepted"}:
        status = "Arrived"
        arrival = "Arrived"
        blocking = None
    elif event_type == "StartedOperation":
        status = "Processing"
        arrival = "Arrived"
        processing = True
        blocking = None
    elif event_type == "CompletedOperation":
        status = "Completed"
        arrival = "Arrived"
        blocking = "OperationAlreadyCompleted"
    elif event_type == "DispatchRejected":
        status = "DispatchRejected"
        arrival = "Arrived"
        blocking = "DispatchRejected"
    elif event_type == "ExceptionReported":
        status = "ExceptionReported"
        arrival = "Arrived"
        blocking = "ExceptionReported"
    return {
        "ExecutionStatus": status,
        "ArrivalStatus": arrival,
        "CurrentProcessing": processing,
        "DispatchBlockingReason": blocking,
        "LastEventType": event_type,
        "LastEventAt": last.get("EventAt"),
    }


def _consecutive_queue_jumps_by_resource(
    execution_events: list[dict[str, object]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in sorted(execution_events, key=lambda item: str(item.get("EventAt") or "")):
        resource_id = event.get("ResourceID")
        if not isinstance(resource_id, str):
            continue
        if event.get("DispatchConflictResult") in {"SuggestQueueJump", "NeedsReplan"}:
            counts[resource_id] = counts.get(resource_id, 0) + 1
        elif event.get("EventType") in {"StartedOperation", "CompletedOperation"}:
            counts[resource_id] = 0
    return counts


def _resources_by_id(master_data_version: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(resource.get("ResourceID")): resource
        for resource in _dict_list(master_data_version.get("Resources"))
    }


def _order_due_date(master_data_version: dict[str, object], order_id: str) -> object:
    for order in _dict_list(master_data_version.get("Orders")):
        if order.get("OrderID") == order_id:
            return order.get("DueDate") or order.get("PromiseDate")
    return None


def _operation_key(operation: dict[str, object]) -> tuple[str, str]:
    return (str(operation.get("OrderID")), str(operation.get("OperationID")))


def _plan_rank_by_resource(
    operations: list[dict[str, object]],
) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    by_resource: dict[str, list[dict[str, object]]] = {}
    for operation in operations:
        by_resource.setdefault(str(operation.get("ResourceID")), []).append(operation)
    for resource_operations in by_resource.values():
        for index, operation in enumerate(
            sorted(
                resource_operations,
                key=lambda item: (
                    str(item.get("Start") or ""),
                    str(item.get("OrderID") or ""),
                    str(item.get("OperationID") or ""),
                ),
            ),
            start=1,
        ):
            result[_operation_key(operation)] = index
    return result


def _suggestion_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "DispatchRank": row.get("DispatchRank"),
        "PlanSequence": row.get("PlanSequence"),
        "OrderID": row.get("OrderID"),
        "OperationID": row.get("OperationID"),
        "ResourceID": row.get("ResourceID"),
        "WorkCenterID": row.get("WorkCenterID"),
        "ScheduledStart": row.get("ScheduledStart"),
        "ScheduledEnd": row.get("ScheduledEnd"),
        "BufferZone": row.get("BufferZone"),
        "BufferPenetrationPercent": row.get("BufferPenetrationPercent"),
        "DemandClass": row.get("DemandClass"),
        "MarketPriorityRank": row.get("MarketPriorityRank"),
        "MarketPriorityReason": row.get("MarketPriorityReason"),
        "ReleaseStatus": row.get("ReleaseStatus"),
        "DispatchEligibility": row.get("DispatchEligibility"),
        "ExecutionStatus": row.get("ExecutionStatus"),
        "ArrivalStatus": row.get("ArrivalStatus"),
        "ConflictResult": row.get("ConflictResult"),
        "RequiresPlannerConfirmation": row.get("RequiresPlannerConfirmation"),
        "Recommendation": row.get("DispatchRecommendation"),
        "RecommendationReason": row.get("RecommendationReason"),
        "LatestGateStatus": row.get("LatestGateStatus"),
        "LatestGateBlockingReasons": row.get("LatestGateBlockingReasons"),
    }


def _recommended_actions(resource_queues: list[dict[str, object]]) -> list[dict[str, object]]:
    actions = []
    for resource in resource_queues:
        for row in _dict_list(resource.get("Queue")):
            actions.append(
                {
                    "ResourceID": resource.get("ResourceID"),
                    "OrderID": row.get("OrderID"),
                    "OperationID": row.get("OperationID"),
                    "Action": row.get("Recommendation"),
                    "Reason": row.get("RecommendationReason"),
                    "RequiresPlannerConfirmation": row.get("RequiresPlannerConfirmation"),
                }
            )
    return actions


def _package_digest(dispatch_workbench: dict[str, object], fingerprint: str) -> str:
    payload = "|".join(
        [
            str(dispatch_workbench.get("RunID") or ""),
            str(dispatch_workbench.get("EvaluatedAt") or ""),
            str(dispatch_workbench.get("OperationalStateSnapshotID") or ""),
            str(dispatch_workbench.get("ReleasePolicyVersionID") or ""),
            fingerprint,
        ]
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:12].upper()


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
