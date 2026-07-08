from __future__ import annotations

from datetime import date, timedelta


PROTECTIVE_CAPACITY_TARGET_PERCENT = 80.0
PLANNED_LOAD_WARNING_PERCENT = 90.0


def build_sdbr_flow_control(
    *,
    system_load_rows: list[dict[str, object]],
    resource_load_rows: list[dict[str, object]],
    release_recommendations: list[dict[str, object]],
) -> dict[str, object]:
    """Build S-DBR operating signals without turning them into hard constraints."""

    critical_resources = [
        row
        for row in system_load_rows
        if bool(row.get("IsConstraint")) or bool(row.get("IsCandidateConstraint"))
    ]
    protective_resources = [
        _protective_capacity_row(row)
        for row in system_load_rows
        if not bool(row.get("IsConstraint"))
    ]
    overloaded_resources = [
        row for row in critical_resources if float(row.get("LoadPercent", 0)) > 100
    ]
    warning_resources = [
        row
        for row in critical_resources
        if 90 < float(row.get("LoadPercent", 0)) <= 100
    ]
    release_dates = [
        str(item.get("SuggestedReleaseDate"))
        for item in release_recommendations
        if item.get("SuggestedReleaseDate")
    ]

    return {
        "Policy": {
            "Mode": "SDBRFlowControl",
            "ProtectiveCapacityTargetPercent": PROTECTIVE_CAPACITY_TARGET_PERCENT,
            "PlannedLoadWarningPercent": PLANNED_LOAD_WARNING_PERCENT,
            "NonConstraintCapacityTreatment": "MonitorOnly",
            "ReplanPrinciple": "BufferFirstReplanByException",
        },
        "PlannedLoad": _planned_load_summary(
            critical_resources=critical_resources,
            overloaded_resources=overloaded_resources,
            warning_resources=warning_resources,
        ),
        "SafeDate": _safe_date_summary(resource_load_rows),
        "ReleaseDiscipline": {
            "Rule": "DoNotReleaseBeforeSuggestedDate",
            "EarliestSuggestedReleaseAt": min(release_dates) if release_dates else None,
            "RecommendationCount": len(release_dates),
            "BusinessMeaning": (
                "释放按绳长建议日期执行，提前释放会增加 WIP 并消耗约束前保护。"
            ),
        },
        "StabilityGuidance": {
            "DefaultAction": "AbsorbWithBufferAndProtectiveCapacity",
            "ReplanTrigger": "OnlyWhenBufferOrLoadThresholdIsBreached",
            "BusinessMeaning": (
                "一般插单、停机和小延迟先通过缓冲、抢修、加班和优先级吸收；"
                "只有红区、约束负荷或连续阻塞达到阈值时才建议重排。"
            ),
        },
        "ProtectiveCapacity": {
            "Rows": protective_resources,
            "AtRiskCount": sum(
                1 for row in protective_resources if row["Status"] != "Healthy"
            ),
            "BusinessMeaning": (
                "非约束资源不默认变成 CP-SAT 硬约束；这里用于发现保护产能是否正在被吃掉。"
            ),
        },
    }


def _planned_load_summary(
    *,
    critical_resources: list[dict[str, object]],
    overloaded_resources: list[dict[str, object]],
    warning_resources: list[dict[str, object]],
) -> dict[str, object]:
    max_row = max(
        critical_resources,
        key=lambda row: float(row.get("LoadPercent", 0)),
        default=None,
    )
    if overloaded_resources:
        status = "Overloaded"
        recommended_action = "CoordinateBeforeReleaseOrPromise"
    elif warning_resources:
        status = "NearLimit"
        recommended_action = "ReviewBeforeInsertOrder"
    else:
        status = "Protected"
        recommended_action = "OperateByBufferPriority"
    return {
        "Status": status,
        "CriticalResourceCount": len(critical_resources),
        "OverloadedResourceCount": len(overloaded_resources),
        "WarningResourceCount": len(warning_resources),
        "MaxLoadResourceID": max_row.get("ResourceID") if max_row else None,
        "MaxLoadPercent": round(float(max_row.get("LoadPercent", 0)), 2)
        if max_row
        else 0.0,
        "RecommendedAction": recommended_action,
    }


def _safe_date_summary(resource_load_rows: list[dict[str, object]]) -> dict[str, object]:
    by_date: dict[str, list[dict[str, object]]] = {}
    for row in resource_load_rows:
        if not (bool(row.get("IsConstraint")) or bool(row.get("IsCandidateConstraint"))):
            continue
        by_date.setdefault(str(row.get("Date")), []).append(row)
    safe_dates = []
    for day, rows in by_date.items():
        if rows and all(
            float(row.get("LoadPercent", 0)) <= PROTECTIVE_CAPACITY_TARGET_PERCENT
            for row in rows
        ):
            safe_dates.append(day)
    if safe_dates:
        return {
            "Status": "Available",
            "EarliestSafeDate": min(safe_dates),
            "BusinessMeaning": "该日期起约束/候选约束负荷低于保护上限，可作为插单初步安全窗口。",
        }
    latest = max(by_date, default=None)
    suggested = _next_day(latest)
    return {
        "Status": "NeedsCapacityReview",
        "EarliestSafeDate": suggested,
        "BusinessMeaning": "当前可见范围内关键资源保护能力不足，插单前需要人工协调或扩展排程窗口。",
    }


def _protective_capacity_row(row: dict[str, object]) -> dict[str, object]:
    load_percent = round(float(row.get("LoadPercent", 0)), 2)
    if load_percent > 100:
        status = "CandidateConstraint"
        action = "EscalateCapacityOrReplanReview"
    elif load_percent > PLANNED_LOAD_WARNING_PERCENT:
        status = "AtRisk"
        action = "ProtectiveCapacityReview"
    elif load_percent > PROTECTIVE_CAPACITY_TARGET_PERCENT:
        status = "Watch"
        action = "MonitorBeforeInsertOrder"
    else:
        status = "Healthy"
        action = "NoHardConstraintNeeded"
    return {
        "ResourceID": row.get("ResourceID"),
        "ResourceName": row.get("ResourceName"),
        "LoadPercent": load_percent,
        "Status": status,
        "RecommendedAction": action,
        "Treatment": "MonitorOnly",
    }


def _next_day(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return (date.fromisoformat(value) + timedelta(days=1)).isoformat()
    except ValueError:
        return None
