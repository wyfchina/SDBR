from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from math import isfinite
from typing import Any

from sdbr.planning_reservation_view import reservation_load_by_bucket


PROTECTIVE_CAPACITY_TARGET_PERCENT = 80.0
PLANNED_LOAD_WARNING_PERCENT = 90.0
ZONE_RANK = {
    "Late": 0,
    "Red": 1,
    "Yellow": 2,
    "Green": 3,
    "AboveGreen": 4,
    "Early": 5,
}


def build_ccr_planned_load(
    *,
    gantt_rows: list[dict[str, object]],
    resources: list[dict[str, object]],
    orders: list[dict[str, object]],
    ddmrp_lines: list[dict[str, object]],
    horizon_start: datetime,
    horizon_days: int = 14,
    protective_capacity_target_percent: float = PROTECTIVE_CAPACITY_TARGET_PERCENT,
    capacity_reservations: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    resources_by_id = {str(item.get("ResourceID")): item for item in resources}
    orders_by_id = {str(item.get("OrderID")): item for item in orders}
    horizon_dates = {
        (horizon_start.date() + timedelta(days=offset)).isoformat()
        for offset in range(max(horizon_days, 1))
    }
    buckets: dict[tuple[str, str], dict[str, object]] = {}

    for resource in resources:
        if not _is_controlled_resource(resource):
            continue
        resource_id = str(resource.get("ResourceID"))
        for bucket_date, capacity in _daily_capacity(resource).items():
            if bucket_date not in horizon_dates:
                continue
            buckets[(resource_id, bucket_date)] = {
                "ResourceID": resource_id,
                "ResourceName": resource.get("Name")
                or resource.get("ResourceName")
                or resource_id,
                "Date": bucket_date,
                "CapacityMinutes": int(capacity),
                "MtoLoadMinutes": 0,
                "MtaLoadMinutes": 0,
                "TotalPlannedLoadMinutes": 0,
                "LoadPercent": 0.0,
                "Status": "Protected",
                "DemandBreakdown": [],
            }

    for row in gantt_rows:
        resource_id = str(row.get("ResourceID"))
        resource = resources_by_id.get(resource_id)
        if not resource or not _is_controlled_resource(resource):
            continue
        for bar in _dict_list(row.get("Bars")):
            if bar.get("BarType") not in {None, "Processing"}:
                continue
            start = _parse_datetime(bar.get("Start"))
            if start is None:
                continue
            bucket = buckets.get((resource_id, start.date().isoformat()))
            if bucket is None:
                continue
            order_id = str(bar.get("OrderID"))
            demand_class = _demand_class(orders_by_id.get(order_id, {}))
            duration = _duration_minutes(bar)
            if demand_class == "MTA":
                bucket["MtaLoadMinutes"] = _checked_finite_sum(
                    int(bucket["MtaLoadMinutes"]), duration, "MtaLoadMinutes"
                )
            else:
                bucket["MtoLoadMinutes"] = _checked_finite_sum(
                    int(bucket["MtoLoadMinutes"]), duration, "MtoLoadMinutes"
                )
            _dict_list(bucket["DemandBreakdown"]).append(
                {
                    "OrderID": order_id,
                    "OperationID": bar.get("OperationID"),
                    "DemandClass": demand_class,
                    "DurationMinutes": duration,
                }
            )

    for key, reservation_load in reservation_load_by_bucket(
        capacity_reservations or []
    ).items():
        bucket = buckets.get(key)
        if bucket is None:
            continue
        mto_minutes = reservation_load["MtoReservationMinutes"]
        mta_minutes = reservation_load["MtaReservationMinutes"]
        bucket["MtoLoadMinutes"] = _checked_finite_sum(
            int(bucket["MtoLoadMinutes"]), mto_minutes, "MtoLoadMinutes"
        )
        bucket["MtaLoadMinutes"] = _checked_finite_sum(
            int(bucket["MtaLoadMinutes"]), mta_minutes, "MtaLoadMinutes"
        )
        bucket["ReservationLoadMinutes"] = reservation_load["ReservationLoadMinutes"]

    for bucket in buckets.values():
        bucket.setdefault("ReservationLoadMinutes", 0)

    rows = []
    for bucket in buckets.values():
        total = _checked_finite_sum(
            bucket["MtoLoadMinutes"],
            bucket["MtaLoadMinutes"],
            "TotalPlannedLoadMinutes",
        )
        capacity = int(bucket["CapacityMinutes"])
        load_percent = _finite_load_percent(total, capacity)
        bucket["TotalPlannedLoadMinutes"] = total
        bucket["LoadPercent"] = load_percent
        bucket["Status"] = _load_status(
            load_percent,
            protective_capacity_target_percent=protective_capacity_target_percent,
        )
        rows.append(bucket)
    rows.sort(key=lambda item: (str(item["Date"]), str(item["ResourceID"])))

    mta_load = build_mta_replenishment_load(
        ddmrp_lines=ddmrp_lines,
        orders=orders,
    )
    max_load = _finite_value(
        max((float(item["LoadPercent"]) for item in rows), default=0.0),
        "Summary.MaxLoadPercent",
    )
    status = _summary_load_status(rows)
    return {
        "Mode": "SDBRCCRPlannedLoadV1",
        "Boundary": (
            "Consumes frozen schedule and runtime inputs; does not require a new "
            "DDAE protocol."
        ),
        "Buckets": rows,
        "MTAReplenishmentLoad": mta_load,
        "Summary": {
            "Status": status,
            "BucketCount": len(rows),
            "ResourceCount": len({str(item["ResourceID"]) for item in rows}),
            "MtoLoadMinutes": _checked_finite_total(
                (item["MtoLoadMinutes"] for item in rows),
                "Summary.MtoLoadMinutes",
            ),
            "MtaLoadMinutes": _checked_finite_total(
                (item["MtaLoadMinutes"] for item in rows),
                "Summary.MtaLoadMinutes",
            ),
            "MaxLoadPercent": round(max_load, 2),
            "ProtectiveCapacityTargetPercent": protective_capacity_target_percent,
            "MappedMtaSuggestionCount": mta_load["MappedSuggestionCount"],
            "UnmappedMtaSuggestionCount": mta_load["UnmappedSuggestionCount"],
        },
    }


def build_mto_safe_date_summary(
    *,
    ccr_planned_load: dict[str, object],
    time_buffer_minutes: int,
    evaluated_at: datetime | None = None,
) -> dict[str, object]:
    evaluated_at = _normalize_datetime(evaluated_at)
    for bucket in _dict_list(ccr_planned_load.get("Buckets")):
        if bucket.get("Status") != "Protected":
            continue
        safe_date = str(bucket.get("Date"))
        half_buffer = max(int(time_buffer_minutes), 0) // 2
        safe_at = datetime.combine(
            datetime.fromisoformat(safe_date).date(),
            time(0, 0),
            tzinfo=timezone.utc,
        ) + timedelta(minutes=half_buffer)
        if evaluated_at is not None and safe_at < evaluated_at:
            return {
                "Status": "Expired",
                "EarliestSafeDate": safe_date,
                "SafePromiseAt": safe_at.isoformat(),
                "Rule": "FirstProtectedCcrBucketPlusHalfTimeBuffer",
                "BusinessMeaning": (
                    "该 MTO 安全承诺日期已过期，不能作为当前插单或客户承诺依据；"
                    "需要按最新排程、约束负荷和缓冲状态重新评估。"
                ),
            }
        return {
            "Status": "Available",
            "EarliestSafeDate": safe_date,
            "SafePromiseAt": safe_at.isoformat(),
            "Rule": "FirstProtectedCcrBucketPlusHalfTimeBuffer",
            "BusinessMeaning": (
                "首个受保护的约束负荷窗口可作为 MTO 插单或承诺前的初步安全日期。"
            ),
        }
    return {
        "Status": "NeedsCapacityReview",
        "EarliestSafeDate": None,
        "SafePromiseAt": None,
        "Rule": "NoProtectedCcrBucketInVisibleHorizon",
        "BusinessMeaning": "可见窗口内没有受保护的约束负荷日期，需要人工评审产能。",
    }


def build_mta_replenishment_load(
    *,
    ddmrp_lines: list[dict[str, object]],
    orders: list[dict[str, object]],
) -> dict[str, object]:
    mta_orders_by_product = {
        str(item.get("ProductID") or item.get("ItemID")): item
        for item in orders
        if _demand_class(item) == "MTA"
    }
    mapped = []
    unmapped = []
    issues = []
    for line in ddmrp_lines:
        qty = float(line.get("SuggestedReplenishmentQty") or 0)
        if qty <= 0:
            continue
        item_id = str(line.get("ItemID"))
        order = mta_orders_by_product.get(item_id)
        entry = {
            "ItemID": item_id,
            "LocationID": line.get("LocationID"),
            "PlanningStatus": line.get("PlanningStatus"),
            "SuggestedReplenishmentQty": qty,
            "OrderID": order.get("OrderID") if order else None,
        }
        if order:
            mapped.append(entry)
        else:
            unmapped.append(entry)
            issues.append(
                {
                    "Code": "MTA_REPLENISHMENT_EXECUTION_ORDER_MISSING",
                    "ItemID": item_id,
                    "LocationID": line.get("LocationID"),
                    "BusinessMeaning": (
                        "该补货建议没有对应的可执行 MTA 工单，暂不计入约束负荷。"
                    ),
                }
            )
    return {
        "Mode": "MTAReplenishmentLoadBridgeV1",
        "MappedSuggestionCount": len(mapped),
        "UnmappedSuggestionCount": len(unmapped),
        "MappedSuggestions": mapped,
        "UnmappedSuggestions": unmapped,
        "Issues": issues,
    }


def build_unified_buffer_priority(
    *,
    mto_candidates: list[dict[str, object]],
    mta_lines: list[dict[str, object]],
    evaluated_at: datetime | None = None,
) -> dict[str, object]:
    rows = []
    for candidate in mto_candidates:
        penetration, zone = _mto_time_buffer_position(
            candidate=candidate,
            evaluated_at=evaluated_at,
        )
        rows.append(
            {
                "DemandClass": _demand_class(candidate),
                "PriorityZone": zone,
                "PriorityPenetrationPercent": penetration,
                "OrderID": candidate.get("OrderID"),
                "SuggestedReleaseAt": candidate.get("SuggestedReleaseAt"),
                "ScheduledStart": candidate.get("ScheduledStart"),
                "RecommendedAction": _priority_action(zone, "MTO"),
                "Source": "MTOTimeBuffer",
            }
        )
    for line in mta_lines:
        qty = float(line.get("SuggestedReplenishmentQty") or 0)
        if qty <= 0:
            continue
        zone = _zone(line.get("PlanningStatus"))
        rows.append(
            {
                "DemandClass": "MTA",
                "PriorityZone": zone,
                "PriorityPenetrationPercent": float(
                    line.get("BufferPenetrationPercent")
                    or line.get("BufferPercent")
                    or 0
                ),
                "ItemID": line.get("ItemID"),
                "LocationID": line.get("LocationID"),
                "SuggestedReplenishmentQty": qty,
                "RecommendedAction": _priority_action(zone, "MTA"),
                "Source": "MTAStockBuffer",
            }
        )

    rows.sort(
        key=lambda item: (
            ZONE_RANK.get(str(item.get("PriorityZone")), 99),
            -float(item.get("PriorityPenetrationPercent") or 0),
            str(item.get("SuggestedReleaseAt") or ""),
            str(item.get("OrderID") or item.get("ItemID") or ""),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["MarketPriorityRank"] = index

    return {
        "Mode": "UnifiedBufferPriorityV1",
        "Rows": rows,
        "Summary": {
            "TotalCount": len(rows),
            "RedCount": _count_zone(rows, "Red") + _count_zone(rows, "Late"),
            "YellowCount": _count_zone(rows, "Yellow"),
            "GreenCount": _count_zone(rows, "Green") + _count_zone(rows, "AboveGreen"),
        },
    }


def _count_zone(rows: list[dict[str, object]], zone: str) -> int:
    return sum(1 for row in rows if row.get("PriorityZone") == zone)


def _daily_capacity(resource: dict[str, object]) -> dict[str, int]:
    raw = resource.get("DailyCapacityMinutes") or resource.get("CapacityByDate") or {}
    if isinstance(raw, dict):
        return {str(day): int(value or 0) for day, value in raw.items()}
    return {}


def _demand_class(item: dict[str, object]) -> str:
    value = str(item.get("DemandClass") or item.get("DemandType") or "MTO").upper()
    return "MTA" if value in {"MTA", "MTS", "STOCKREPLENISHMENT"} else "MTO"


def _dict_list(value: Any) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _duration_minutes(bar: dict[str, object]) -> int:
    if bar.get("DurationMinutes") is not None:
        return int(bar.get("DurationMinutes") or 0)
    start = _parse_datetime(bar.get("Start"))
    end = _parse_datetime(bar.get("End"))
    if not start or not end:
        return 0
    return max(int((end - start).total_seconds() // 60), 0)


def _checked_finite_sum(
    left: int | float,
    right: int | float,
    field: str,
) -> int | float:
    try:
        total = left + right
    except OverflowError as error:
        raise ValueError(f"{field} aggregate overflow.") from error
    return _finite_value(total, field)


def _checked_finite_total(
    values: object,
    field: str,
) -> int | float:
    total: int | float = 0
    for value in values:
        total = _checked_finite_sum(total, value, field)
    return total


def _finite_load_percent(total: int | float, capacity: int) -> float:
    if capacity <= 0:
        return 0.0
    try:
        load_percent = total / capacity * 100
    except OverflowError as error:
        raise ValueError("LoadPercent aggregate overflow.") from error
    return round(_finite_value(load_percent, "LoadPercent"), 2)


def _finite_value(value: int | float, field: str) -> int | float:
    try:
        is_value_finite = isfinite(float(value))
    except OverflowError as error:
        raise ValueError(f"{field} aggregate overflow.") from error
    if not is_value_finite:
        raise ValueError(f"{field} aggregate overflow.")
    return value


def _mto_time_buffer_position(
    *,
    candidate: dict[str, object],
    evaluated_at: datetime | None,
) -> tuple[float, str]:
    release_at = _parse_datetime(candidate.get("SuggestedReleaseAt"))
    start_at = _parse_datetime(candidate.get("ScheduledStart"))
    evaluated_at = _normalize_datetime(evaluated_at)
    if (
        evaluated_at is not None
        and release_at is not None
        and start_at is not None
        and start_at > release_at
    ):
        penetration = round(
            (evaluated_at - release_at).total_seconds()
            / (start_at - release_at).total_seconds()
            * 100,
            2,
        )
        if penetration > 100:
            return penetration, "Late"
        if penetration >= 66:
            return max(penetration, 0.0), "Red"
        if penetration >= 33:
            return max(penetration, 0.0), "Yellow"
        return max(penetration, 0.0), "Green"
    return (
        float(candidate.get("BufferPenetrationPercent") or 0),
        _zone(candidate.get("BufferZone")),
    )


def _is_controlled_resource(resource: dict[str, object]) -> bool:
    role = str(resource.get("ResourceRole") or resource.get("Role") or "").upper()
    return bool(resource.get("IsConstraint")) or bool(
        resource.get("IsCandidateConstraint")
    ) or role in {"CCR", "CONSTRAINT", "CONTROLPOINT", "BUFFERPROTECTED"}


def _load_status(
    load_percent: float,
    *,
    protective_capacity_target_percent: float,
) -> str:
    if load_percent > 100:
        return "Overloaded"
    if load_percent > PLANNED_LOAD_WARNING_PERCENT:
        return "NearLimit"
    if load_percent > protective_capacity_target_percent:
        return "Watch"
    return "Protected"


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _normalize_datetime(value)
    if not value:
        return None
    try:
        return _normalize_datetime(
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
    except ValueError:
        return None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _priority_action(zone: str, demand_class: str) -> str:
    subject = "MTA补货" if demand_class == "MTA" else "MTO工单"
    if zone in {"Late", "Red"}:
        return f"{subject}进入红区，优先保护市场承诺"
    if zone == "Yellow":
        return f"{subject}进入黄区，纳入释放关注"
    return f"{subject}保持观察"


def _summary_load_status(rows: list[dict[str, object]]) -> str:
    statuses = {str(row.get("Status")) for row in rows}
    if "Overloaded" in statuses:
        return "Overloaded"
    if "NearLimit" in statuses:
        return "NearLimit"
    if "Watch" in statuses:
        return "Watch"
    return "Protected"


def _zone(value: object) -> str:
    text = str(value or "Green")
    normalized = text.strip().lower()
    if normalized == "late":
        return "Late"
    if normalized == "red":
        return "Red"
    if normalized == "yellow":
        return "Yellow"
    if normalized in {"abovegreen", "above_green", "above green"}:
        return "AboveGreen"
    if normalized == "early":
        return "Early"
    return "Green"
