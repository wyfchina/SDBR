from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sdbr.release_authorization import ReleaseAuthorization, build_dispatch_package
from sdbr.shop_floor_execution import (
    build_schedule_execution_variance,
    summarize_execution_events,
)


RATE_GREEN = 90.0
RATE_YELLOW = 75.0


def build_ddom_operational_metrics(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    release_workbench: dict[str, object] | None,
    buffer_workbench: dict[str, object] | None,
    dispatch_workbench: dict[str, object] | None,
    authorizations: list[ReleaseAuthorization],
    execution_events: list[dict[str, object]],
    evaluated_at: datetime,
) -> dict[str, object]:
    """Build the minimum DDOM flow-based metrics set.

    The metrics intentionally aggregate existing DDOM execution read models. They
    do not replace financial KPIs, DDS&OP model governance, or MES real-time
    control.
    """

    run_id = str(planning_run.get("RunID") or "")
    schedule = _dict(planning_run.get("Schedule"))
    run_authorizations = [
        authorization
        for authorization in authorizations
        if authorization.request_id == run_id
    ]
    dispatch_packages = [
        build_dispatch_package(authorization)
        for authorization in run_authorizations
        if authorization.status == "Authorized"
    ]
    variance = build_schedule_execution_variance(
        dispatch_packages=dispatch_packages,
        events=execution_events,
    )
    execution_summary = summarize_execution_events(execution_events)
    release_summary = _dict((release_workbench or {}).get("Summary"))
    dispatch_summary = _dict((dispatch_workbench or {}).get("Summary"))
    buffer_counts = _buffer_counts(buffer_workbench, schedule)
    load_summary = _load_summary(schedule)
    scheduled_order_count = _scheduled_order_count(schedule, master_data_version)

    categories = [
        _reliability_metrics(
            buffer_counts=buffer_counts,
            release_summary=release_summary,
            variance_summary=_dict(variance.get("Summary")),
            scheduled_order_count=scheduled_order_count,
            authorization_count=len(dispatch_packages),
        ),
        _stability_metrics(
            buffer_counts=buffer_counts,
            execution_summary=execution_summary,
            execution_events=execution_events,
            load_summary=load_summary,
        ),
        _speed_metrics(
            variance_summary=_dict(variance.get("Summary")),
            dispatch_summary=dispatch_summary,
            release_workbench=release_workbench or {},
            scheduled_order_count=scheduled_order_count,
        ),
    ]
    for category in categories:
        category["Status"] = _worst_status(
            str(metric["Status"]) for metric in _dict_list(category.get("Metrics"))
        )
        category["Score"] = _category_score(_dict_list(category.get("Metrics")))

    return {
        "RunID": run_id,
        "EvaluatedAt": evaluated_at.isoformat(),
        "MetricSetID": "DDOM-FLOW-METRICS-V1",
        "MetricSetName": "DDOM 运营流动指标最小集",
        "OverallStatus": _worst_status(str(item["Status"]) for item in categories),
        "OverallScore": _category_score(
            [
                {"Value": item.get("Score"), "Unit": "Score", "DataCoverage": "Available"}
                for item in categories
            ]
        ),
        "Applicability": {
            "AppliesTo": [
                "DDOM daily operations",
                "Release gating and buffer execution",
                "MES dispatch suggestion review",
                "Execution variance feedback to DDS&OP",
            ],
            "DoesNotApplyTo": [
                "Financial cost attribution",
                "DDS&OP model configuration or scenario governance",
                "MES second-by-second machine control",
                "Long-term capacity investment decisions",
            ],
        },
        "Categories": categories,
        "VarianceFeedback": {
            "FeedbackScope": "DDOMPerformanceForDDSOP",
            "ReliabilityStatus": categories[0]["Status"],
            "StabilityStatus": categories[1]["Status"],
            "SpeedStatus": categories[2]["Status"],
            "RecommendedActions": _recommended_actions(categories),
            "DataCoverageIssues": _data_coverage_issues(categories),
        },
        "Evidence": {
            "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
            "OperationalStateSnapshotID": planning_run.get("OperationalStateSnapshotID"),
            "ScheduleFingerprint": planning_run.get("ScheduleFingerprint"),
            "AuthorizedReleaseCount": len(dispatch_packages),
            "ExecutionEventCount": len(execution_events),
        },
    }


def _reliability_metrics(
    *,
    buffer_counts: dict[str, int],
    release_summary: dict[str, object],
    variance_summary: dict[str, object],
    scheduled_order_count: int,
    authorization_count: int,
) -> dict[str, object]:
    total_buffer = int(buffer_counts.get("Total", 0))
    protected = total_buffer - int(buffer_counts.get("Red", 0)) - int(buffer_counts.get("Late", 0))
    release_total = int(release_summary.get("TotalCount") or scheduled_order_count or 0)
    actionable_release = int(release_summary.get("ReadyCount") or 0) + int(
        release_summary.get("AuthorizedCount") or 0
    )
    variance_total = int(variance_summary.get("OrderCount") or 0)
    started_or_pending = variance_total - int(variance_summary.get("StartLateCount") or 0)
    return {
        "CategoryID": "Reliability",
        "NameZh": "运营可靠性",
        "NameEn": "Operational Reliability",
        "QuestionZh": "是否按既定 DDOM 模型运行？",
        "FocusZh": "按模型做。",
        "Metrics": [
            _rate_metric(
                "StrategicBufferIntegrityRate",
                "战略缓冲完整率",
                "未进入红区或迟到区的战略缓冲占比。",
                protected,
                total_buffer,
                coverage="Available" if total_buffer else "NoActiveBufferOrders",
            ),
            _rate_metric(
                "SupplySignalTimelyProcessingRate",
                "供给信号及时处理率",
                "释放信号中已具备处理条件或已授权的占比。",
                actionable_release,
                release_total,
                coverage="Available" if release_total else "NoReleaseCandidates",
            ),
            _rate_metric(
                "ScheduledReleaseRate",
                "制造订单按时释放率",
                "已授权释放的制造订单占计划订单的比例。",
                authorization_count,
                scheduled_order_count,
                coverage="Available" if scheduled_order_count else "NoScheduledOrders",
            ),
            _rate_metric(
                "ControlPointPlanAdherenceRate",
                "控制点计划遵守率",
                "已释放工单中未出现开工迟到的占比。",
                started_or_pending,
                variance_total,
                coverage="Available" if variance_total else "NoExecutionEvents",
            ),
        ],
    }


def _stability_metrics(
    *,
    buffer_counts: dict[str, int],
    execution_summary: dict[str, object],
    execution_events: list[dict[str, object]],
    load_summary: dict[str, int],
) -> dict[str, object]:
    total_buffer = int(buffer_counts.get("Total", 0))
    red_late = int(buffer_counts.get("Red", 0)) + int(buffer_counts.get("Late", 0))
    late_summary = _dict(execution_summary.get("LateArrivalSummary"))
    late_count = int(late_summary.get("LateArrivalCount") or 0)
    arrival_count = sum(1 for event in execution_events if event.get("EventType") == "ArrivedBuffer")
    alert_count = int(execution_summary.get("RequiresReviewCount") or 0)
    overload_minutes = int(load_summary.get("OverloadMinutes") or 0)
    return {
        "CategoryID": "Stability",
        "NameZh": "运营稳定性",
        "NameEn": "Operational Stability",
        "QuestionZh": "波动是否被缓冲吸收，而不是继续扩散？",
        "FocusZh": "不要把波动传下去。",
        "Metrics": [
            _bad_rate_metric(
                "RedZonePenetrationRate",
                "库存/时间缓冲红区穿透率",
                "进入红区或迟到区的缓冲对象占比。",
                red_late,
                total_buffer,
                coverage="Available" if total_buffer else "NoActiveBufferOrders",
            ),
            _count_metric(
                "SyncAlertCountAndAge",
                "同步告警数及账龄",
                "当前需要人工复核的同步告警数量。",
                alert_count,
                warning_threshold=1,
                red_threshold=3,
                unit="Alerts",
            ),
            _bad_rate_metric(
                "BufferLateArrivalRate",
                "缓冲晚到率",
                "到达缓冲的事件中晚到的比例。",
                late_count,
                arrival_count,
                coverage="Available" if arrival_count else "NoArrivalEvents",
            ),
            _count_metric(
                "CapacityBufferBreachMinutes",
                "产能缓冲突破时间",
                "计划负荷超过可用能力的分钟数。",
                overload_minutes,
                warning_threshold=1,
                red_threshold=60,
                unit="Minutes",
            ),
        ],
    }


def _speed_metrics(
    *,
    variance_summary: dict[str, object],
    dispatch_summary: dict[str, object],
    release_workbench: dict[str, object],
    scheduled_order_count: int,
) -> dict[str, object]:
    dispatchable = int(dispatch_summary.get("DispatchableOperationCount") or 0)
    replan = int(dispatch_summary.get("ReplanSuggestionCount") or 0)
    jump = int(dispatch_summary.get("QueueJumpSuggestionCount") or 0)
    completed = int(variance_summary.get("CompletedCount") or 0)
    pending_completion = int(variance_summary.get("PendingCompletionCount") or 0)
    late_completion = int(variance_summary.get("CompletionLateCount") or 0)
    wip_overage = _blocking_reason_count(release_workbench, "WIP_LIMIT_EXCEEDED")
    return {
        "CategoryID": "SpeedVelocity",
        "NameZh": "运营速度 / 流速",
        "NameEn": "Operational Speed / Velocity",
        "QuestionZh": "正确的工作是否足够快地向前流动？",
        "FocusZh": "让正确工作尽快向前走。",
        "Metrics": [
            _rate_metric(
                "PriorityExecutionRate",
                "正确优先级执行率",
                "正式派工队列中不需要重排的工序占比。",
                max(dispatchable - replan, 0),
                dispatchable,
                coverage="Available" if dispatchable else "NoDispatchableOperations",
                evidence={"QueueJumpSuggestionCount": jump, "ReplanSuggestionCount": replan},
            ),
            _rate_metric(
                "WorkOrderProgressAttainmentRate",
                "工单进度达成率",
                "已完成执行反馈的工单占计划订单的比例。",
                completed,
                scheduled_order_count,
                coverage="Available" if scheduled_order_count else "NoScheduledOrders",
                evidence={"PendingCompletionCount": pending_completion},
            ),
            _bad_rate_metric(
                "NextControlPointLateArrivalRate",
                "下一关键节点晚到率",
                "已释放工单中完工迟到的比例。",
                late_completion,
                int(variance_summary.get("OrderCount") or 0),
                coverage=(
                    "Available"
                    if int(variance_summary.get("OrderCount") or 0)
                    else "NoExecutionEvents"
                ),
            ),
            _count_metric(
                "WipOverageExceptionCount",
                "WIP 超龄异常数",
                "释放评估中因 WIP 超限被阻塞的工单数。",
                wip_overage,
                warning_threshold=1,
                red_threshold=3,
                unit="Orders",
            ),
        ],
    }


def _rate_metric(
    metric_id: str,
    name_zh: str,
    definition_zh: str,
    numerator: int,
    denominator: int,
    *,
    coverage: str,
    evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    value = _rate(numerator, denominator)
    return {
        "MetricID": metric_id,
        "NameZh": name_zh,
        "DefinitionZh": definition_zh,
        "Value": value,
        "Unit": "Percent",
        "Numerator": numerator,
        "Denominator": denominator,
        "Status": _rate_status(value),
        "DataCoverage": coverage,
        "Evidence": evidence or {},
    }


def _bad_rate_metric(
    metric_id: str,
    name_zh: str,
    definition_zh: str,
    numerator: int,
    denominator: int,
    *,
    coverage: str,
) -> dict[str, object]:
    value = _rate(numerator, denominator)
    return {
        "MetricID": metric_id,
        "NameZh": name_zh,
        "DefinitionZh": definition_zh,
        "Value": value,
        "Unit": "Percent",
        "Numerator": numerator,
        "Denominator": denominator,
        "Status": _bad_rate_status(value),
        "DataCoverage": coverage,
        "Evidence": {},
    }


def _count_metric(
    metric_id: str,
    name_zh: str,
    definition_zh: str,
    value: int,
    *,
    warning_threshold: int,
    red_threshold: int,
    unit: str,
) -> dict[str, object]:
    status = "Green"
    if value >= red_threshold:
        status = "Red"
    elif value >= warning_threshold:
        status = "Yellow"
    return {
        "MetricID": metric_id,
        "NameZh": name_zh,
        "DefinitionZh": definition_zh,
        "Value": value,
        "Unit": unit,
        "Numerator": value,
        "Denominator": None,
        "Status": status,
        "DataCoverage": "Available",
        "Evidence": {"WarningThreshold": warning_threshold, "RedThreshold": red_threshold},
    }


def _buffer_counts(
    buffer_workbench: dict[str, object] | None,
    schedule: dict[str, object],
) -> dict[str, int]:
    counts = {"Total": 0, "Early": 0, "Green": 0, "Yellow": 0, "Red": 0, "Late": 0}
    for row in _dict_list((buffer_workbench or {}).get("Rows")):
        for cell in _dict_list(row.get("Cells")):
            zone = str(cell.get("Zone") or "")
            count = int(cell.get("OrderCount") or 0)
            if zone in counts:
                counts[zone] += count
                counts["Total"] += count
    if counts["Total"]:
        return counts
    for item in _dict_list(schedule.get("BufferBoard")):
        zone = str(item.get("Zone") or "Green")
        if zone in counts:
            counts[zone] += 1
            counts["Total"] += 1
    return counts


def _load_summary(schedule: dict[str, object]) -> dict[str, int]:
    overload = 0
    for row in _dict_list(schedule.get("LoadGraphRows")):
        for cell in _dict_list(row.get("Cells")):
            overload += max(0, int(cell.get("OverloadMinutes") or 0))
    return {"OverloadMinutes": overload}


def _scheduled_order_count(
    schedule: dict[str, object],
    master_data_version: dict[str, object],
) -> int:
    if schedule.get("OrderCount") is not None:
        return int(schedule.get("OrderCount") or 0)
    order_ids = {
        str(bar.get("OrderID"))
        for row in _dict_list(schedule.get("GanttRows"))
        for bar in _dict_list(row.get("Bars"))
        if bar.get("OrderID") is not None
    }
    if order_ids:
        return len(order_ids)
    return len(_dict_list(master_data_version.get("Orders")))


def _blocking_reason_count(workbench: dict[str, object], reason_code: str) -> int:
    count = 0
    for candidate in _dict_list(workbench.get("Candidates")):
        for reason in _dict_list(candidate.get("BlockingReasons")):
            if reason.get("Code") == reason_code:
                count += 1
                break
    return count


def _recommended_actions(categories: list[dict[str, object]]) -> list[dict[str, object]]:
    actions = []
    for category in categories:
        for metric in _dict_list(category.get("Metrics")):
            if metric.get("Status") == "Red":
                actions.append(
                    {
                        "MetricID": metric.get("MetricID"),
                        "ActionZh": f"优先处理：{metric.get('NameZh')}",
                    }
                )
    if not actions:
        actions.append({"MetricID": "Overall", "ActionZh": "继续按当前 DDOM 模型运行并监控。"})
    return actions


def _data_coverage_issues(categories: list[dict[str, object]]) -> list[dict[str, object]]:
    issues = []
    for category in categories:
        for metric in _dict_list(category.get("Metrics")):
            coverage = str(metric.get("DataCoverage") or "")
            if coverage not in {"Available", ""}:
                issues.append(
                    {
                        "MetricID": metric.get("MetricID"),
                        "Coverage": coverage,
                        "MessageZh": f"{metric.get('NameZh')}需要更多执行或现场数据才能完整计算。",
                    }
                )
    return issues


def _category_score(metrics: list[dict[str, object]]) -> float | None:
    values = [
        float(metric["Value"])
        for metric in metrics
        if metric.get("Unit") in {"Percent", "Score"}
        and isinstance(metric.get("Value"), (int, float))
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100, 2)


def _rate_status(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    if value >= RATE_GREEN:
        return "Green"
    if value >= RATE_YELLOW:
        return "Yellow"
    return "Red"


def _bad_rate_status(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    if value <= 5:
        return "Green"
    if value <= 20:
        return "Yellow"
    return "Red"


def _worst_status(statuses: Iterable[str]) -> str:
    ranking = {"Red": 0, "Yellow": 1, "Green": 2, "Unavailable": 3}
    return min(statuses, key=lambda status: ranking.get(status, 4), default="Unavailable")


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
