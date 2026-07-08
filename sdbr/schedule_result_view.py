from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sdbr.release_policy import effective_rope_buffer_minutes
from sdbr.sdbr_flow_control import build_sdbr_flow_control
from sdbr.sdbr_market_control import (
    build_ccr_planned_load,
    build_mta_replenishment_load,
    build_mto_safe_date_summary,
    build_unified_buffer_priority,
)


def build_schedule_result_workbench(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    released_order_ids: set[str] | None = None,
) -> dict[str, object]:
    schedule = _schedule(planning_run)
    resources = _resource_metadata(master_data_version)
    buffer_zones = {
        str(item.get("OrderID")): str(item.get("Zone", "Green"))
        for item in _dict_list(schedule.get("BufferBoard"))
    }
    gantt = _build_gantt(
        schedule=schedule,
        resources=resources,
        buffer_zones=buffer_zones,
        time_buffer_minutes=effective_rope_buffer_minutes(
            release_policy=(
                planning_run.get("FrozenReleasePolicy")
                if isinstance(planning_run.get("FrozenReleasePolicy"), dict)
                else None
            ),
            fallback_time_buffer_minutes=int(planning_run.get("TimeBufferMinutes", 0)),
        ),
        calendar_overrides=_dict_list(planning_run.get("FrozenCalendarOverrides")),
    )
    system_load, resource_load = _build_load_views(
        schedule=schedule,
        resources=resources,
        gantt_rows=gantt["Rows"],
        released_order_ids=released_order_ids or set(),
    )
    order_delivery = _build_order_delivery(
        master_data_version=master_data_version,
        gantt_rows=gantt["Rows"],
    )
    total_overload = sum(
        int(row["OverloadMinutes"]) for row in system_load["Rows"]
    )
    red_count = int(
        _dict(schedule.get("BufferSummary")).get("RedCount", 0)
    )
    max_load = max(
        (float(row["LoadPercent"]) for row in system_load["Rows"]),
        default=0.0,
    )
    return {
        "Context": {
            "RunID": planning_run.get("RunID"),
            "ProblemID": planning_run.get("ProblemID"),
            "MasterDataVersionID": planning_run.get("MasterDataVersionID"),
            "OperationalStateSnapshotID": planning_run.get(
                "OperationalStateSnapshotID"
            ),
            "GeneratedAt": schedule.get("GeneratedAt")
            or planning_run.get("CompletedAt"),
            "SolverBackendID": planning_run.get("SolverBackendID"),
            "SolverStatus": planning_run.get("SolverStatus"),
            "ReleasePolicyVersionID": planning_run.get("ReleasePolicyVersionID"),
        },
        "KPIs": {
            "OrderCount": int(schedule.get("OrderCount", len(order_delivery))),
            "OnTimeOrderCount": sum(
                1 for item in order_delivery if item["Status"] == "OnTime"
            ),
            "LateOrderCount": sum(
                1 for item in order_delivery if item["Status"] == "Late"
            ),
            "ConstraintOverloadCount": int(
                schedule.get("ConstraintOverloadCount", 0)
            ),
            "TotalOverloadMinutes": total_overload,
            "RedBufferCount": red_count,
            "MaxLoadPercent": round(max_load, 2),
        },
        "Gantt": gantt,
        "SystemLoad": system_load,
        "ResourceLoad": resource_load,
        "SDBRFlowControl": build_sdbr_flow_control(
            system_load_rows=_dict_list(system_load.get("Rows")),
            resource_load_rows=_dict_list(resource_load.get("Rows")),
            release_recommendations=_dict_list(
                schedule.get("ReleaseRecommendations")
            ),
        ),
        "SDBRMarketControl": _build_sdbr_market_control(
            planning_run=planning_run,
            master_data_version=master_data_version,
            gantt_rows=_dict_list(gantt.get("Rows")),
            system_load_rows=_dict_list(system_load.get("Rows")),
            resource_load_rows=_dict_list(resource_load.get("Rows")),
            schedule=schedule,
        ),
        "OrderDelivery": order_delivery,
        "Diagnostics": _dict_list(schedule.get("SolverDiagnostics")),
        "Risks": {
            "BottleneckCandidates": _dict_list(
                schedule.get("BottleneckCandidates")
            ),
            "HasCriticalBufferAlert": bool(
                _dict(schedule.get("BufferSummary")).get(
                    "HasCriticalAlert", False
                )
            ),
        },
        "FilterOptions": _filter_options(
            resources=resources,
            gantt_rows=gantt["Rows"],
            buffer_zones=buffer_zones,
        ),
    }


def _build_sdbr_market_control(
    *,
    planning_run: dict[str, object],
    master_data_version: dict[str, object],
    gantt_rows: list[dict[str, object]],
    system_load_rows: list[dict[str, object]],
    resource_load_rows: list[dict[str, object]],
    schedule: dict[str, object],
) -> dict[str, object]:
    ddmrp_lines = _dict_list(master_data_version.get("DdmrpRuntimeLines"))
    orders = _dict_list(master_data_version.get("Orders"))
    ccr_load = build_ccr_planned_load(
        gantt_rows=gantt_rows,
        resources=_market_control_resources(
            system_load_rows=system_load_rows,
            resource_load_rows=resource_load_rows,
        ),
        orders=orders,
        ddmrp_lines=ddmrp_lines,
        horizon_start=_market_control_horizon_start(
            planning_run=planning_run,
            gantt_rows=gantt_rows,
        ),
    )
    mta_load = build_mta_replenishment_load(ddmrp_lines=ddmrp_lines, orders=orders)
    return {
        "Mode": "SDBRMarketControlV1",
        "Boundary": "Internal S-DBR execution read model; no new DDAE protocol required.",
        "CCRPlannedLoad": ccr_load,
        "MTOSafeDate": build_mto_safe_date_summary(
            ccr_planned_load=ccr_load,
            time_buffer_minutes=effective_rope_buffer_minutes(
                release_policy=(
                    planning_run.get("FrozenReleasePolicy")
                    if isinstance(planning_run.get("FrozenReleasePolicy"), dict)
                    else None
                ),
                fallback_time_buffer_minutes=int(
                    planning_run.get("TimeBufferMinutes", 0)
                ),
            ),
        ),
        "MTAReplenishmentLoad": mta_load,
        "UnifiedBufferPriority": build_unified_buffer_priority(
            mto_candidates=_market_control_mto_candidates(schedule),
            mta_lines=ddmrp_lines,
        ),
    }


def _market_control_resources(
    *,
    system_load_rows: list[dict[str, object]],
    resource_load_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    daily_capacity: dict[str, dict[str, int]] = {}
    for row in resource_load_rows:
        resource_id = str(row.get("ResourceID"))
        date_value = str(row.get("Date"))
        daily_capacity.setdefault(resource_id, {})[date_value] = int(
            row.get("CapacityMinutes", 0)
        )
    resources = []
    for row in system_load_rows:
        resource_id = str(row.get("ResourceID"))
        resources.append(
            {
                "ResourceID": resource_id,
                "Name": row.get("ResourceName") or resource_id,
                "IsConstraint": bool(row.get("IsConstraint")),
                "IsCandidateConstraint": bool(row.get("IsCandidateConstraint")),
                "DailyCapacityMinutes": daily_capacity.get(resource_id, {}),
            }
        )
    return resources


def _market_control_horizon_start(
    *,
    planning_run: dict[str, object],
    gantt_rows: list[dict[str, object]],
) -> datetime:
    for value in (
        planning_run.get("ScheduleStartAt"),
        _dict(planning_run.get("Schedule")).get("GeneratedAt"),
        planning_run.get("CompletedAt"),
    ):
        parsed = _parse_datetime(value)
        if parsed is not None:
            return parsed
    for row in gantt_rows:
        for bar in _dict_list(row.get("Bars")):
            parsed = _parse_datetime(bar.get("Start"))
            if parsed is not None:
                return parsed
    return datetime.utcnow()


def _market_control_mto_candidates(
    schedule: dict[str, object],
) -> list[dict[str, object]]:
    release_by_order = {
        str(item.get("OrderID")): item
        for item in _dict_list(schedule.get("ReleaseRecommendations"))
    }
    candidates = []
    for row in _dict_list(schedule.get("BufferBoard")):
        order_id = str(row.get("OrderID"))
        release = release_by_order.get(order_id, {})
        candidates.append(
            {
                "OrderID": order_id,
                "DemandClass": row.get("DemandClass") or "MTO",
                "BufferZone": row.get("Zone") or row.get("BufferZone"),
                "BufferPenetrationPercent": row.get("BufferPenetrationPercent")
                or row.get("PenetrationPercent")
                or 0,
                "SuggestedReleaseAt": row.get("SuggestedReleaseDate")
                or release.get("SuggestedReleaseDate")
                or release.get("SuggestedReleaseAt"),
            }
        )
    return candidates


def compare_schedule_results(
    *,
    baseline: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    baseline_kpis = _dict(baseline.get("KPIs"))
    candidate_kpis = _dict(candidate.get("KPIs"))
    keys = [
        "OnTimeOrderCount",
        "LateOrderCount",
        "ConstraintOverloadCount",
        "TotalOverloadMinutes",
        "RedBufferCount",
        "MaxLoadPercent",
    ]
    delta = {
        key: round(
            float(candidate_kpis.get(key, 0))
            - float(baseline_kpis.get(key, 0)),
            2,
        )
        for key in keys
    }
    baseline_id = str(_dict(baseline.get("Context")).get("RunID"))
    candidate_id = str(_dict(candidate.get("Context")).get("RunID"))
    recommended = (
        candidate_id
        if _scenario_score(candidate_kpis) < _scenario_score(baseline_kpis)
        else baseline_id
    )
    return {
        "Baseline": {"RunID": baseline_id, "KPIs": baseline_kpis},
        "Candidate": {"RunID": candidate_id, "KPIs": candidate_kpis},
        "Delta": delta,
        "RecommendedRunID": recommended,
        "DecisionCodes": _decision_codes(delta, recommended == candidate_id),
    }


def _build_gantt(
    *,
    schedule: dict[str, object],
    resources: dict[str, dict[str, object]],
    buffer_zones: dict[str, str],
    time_buffer_minutes: int,
    calendar_overrides: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    first_bar_by_order: dict[str, tuple[str, dict[str, object]]] = {}
    for source_row in _dict_list(schedule.get("GanttRows")):
        resource_id = str(source_row.get("ResourceID"))
        bars = []
        for source_bar in _dict_list(source_row.get("Bars")):
            order_id = str(source_bar.get("OrderID"))
            bar = {
                **source_bar,
                "BarType": "Processing",
                "BufferZone": buffer_zones.get(order_id),
            }
            bars.append(bar)
            current = first_bar_by_order.get(order_id)
            if current is None or str(bar.get("Start")) < str(
                current[1].get("Start")
            ):
                first_bar_by_order[order_id] = (resource_id, bar)
        metadata = resources.get(resource_id, {})
        rows.append(
            {
                "ResourceID": resource_id,
                "ResourceName": metadata.get("ResourceName", resource_id),
                "IsConstraint": bool(metadata.get("IsConstraint", False)),
                "Bars": bars,
            }
        )
    rows_by_resource = {str(row["ResourceID"]): row for row in rows}
    if time_buffer_minutes > 0:
        for order_id, (resource_id, processing) in first_bar_by_order.items():
            start = _parse_datetime(processing.get("Start"))
            if start is None:
                continue
            rows_by_resource[resource_id]["Bars"].append(
                {
                    "OperationID": "TIME-BUFFER",
                    "OrderID": order_id,
                    "Start": (start - timedelta(minutes=time_buffer_minutes)).isoformat(),
                    "End": start.isoformat(),
                    "DurationMinutes": time_buffer_minutes,
                    "BarType": "TimeBuffer",
                    "BufferZone": buffer_zones.get(order_id, "Green"),
                }
            )
    _append_downtime_bars(
        schedule=schedule,
        resources=resources,
        rows_by_resource=rows_by_resource,
    )
    _append_calendar_override_bars(
        calendar_overrides=calendar_overrides or [],
        resources=resources,
        rows_by_resource=rows_by_resource,
    )
    all_bars = []
    for row in rows:
        row["Bars"].sort(
            key=lambda item: (
                str(item.get("Start")),
                0 if item.get("BarType") == "TimeBuffer" else 1,
            )
        )
        all_bars.extend(row["Bars"])
    return {
        "Range": {
            "Start": min((str(item["Start"]) for item in all_bars), default=None),
            "End": max((str(item["End"]) for item in all_bars), default=None),
        },
        "Rows": rows,
    }


def _build_load_views(
    *,
    schedule: dict[str, object],
    resources: dict[str, dict[str, object]],
    gantt_rows: list[dict[str, object]],
    released_order_ids: set[str],
) -> tuple[dict[str, object], dict[str, object]]:
    released_by_resource_date: dict[tuple[str, str], int] = {}
    for row in gantt_rows:
        resource_id = str(row["ResourceID"])
        for bar in _dict_list(row.get("Bars")):
            if (
                bar.get("BarType") != "Processing"
                or str(bar.get("OrderID")) not in released_order_ids
            ):
                continue
            start = _parse_datetime(bar.get("Start"))
            if start is None:
                continue
            key = (resource_id, start.date().isoformat())
            released_by_resource_date[key] = released_by_resource_date.get(
                key, 0
            ) + int(bar.get("DurationMinutes", 0))
    system_rows = []
    daily_rows = []
    for row in _dict_list(schedule.get("LoadGraphRows")):
        resource_id = str(row.get("ResourceID"))
        metadata = resources.get(resource_id, {})
        cells = _dict_list(row.get("Cells"))
        required = sum(int(cell.get("RequiredMinutes", 0)) for cell in cells)
        capacity = sum(int(cell.get("CapacityMinutes", 0)) for cell in cells)
        released = 0
        for cell in cells:
            date = str(cell.get("Date"))
            cell_required = int(cell.get("RequiredMinutes", 0))
            cell_released = min(
                released_by_resource_date.get((resource_id, date), 0),
                cell_required,
            )
            released += cell_released
            daily_rows.append(
                {
                    "ResourceID": resource_id,
                    "ResourceName": row.get("ResourceName", resource_id),
                    "IsConstraint": bool(row.get("IsConstraint", False)),
                    "Date": date,
                    "RequiredMinutes": cell_required,
                    "CapacityMinutes": int(cell.get("CapacityMinutes", 0)),
                    "LoadPercent": float(cell.get("LoadPercent", 0)),
                    "ReleasedMinutes": cell_released,
                    "UnreleasedMinutes": max(cell_required - cell_released, 0),
                    "CompletedMinutes": 0,
                    "RemainingMinutes": cell_required,
                    "OverloadMinutes": int(cell.get("OverloadMinutes", 0)),
                }
            )
        system_rows.append(
            {
                "ResourceID": resource_id,
                "ResourceName": row.get("ResourceName", resource_id),
                "IsConstraint": bool(row.get("IsConstraint", False)),
                "ResourceType": metadata.get("ResourceType"),
                "LocationID": metadata.get("LocationID"),
                "OwnerID": metadata.get("OwnerID"),
                "Category": metadata.get("Category"),
                "RequiredMinutes": required,
                "CapacityMinutes": capacity,
                "LoadPercent": round(required / capacity * 100, 2)
                if capacity
                else 0.0,
                "ReleasedMinutes": released,
                "UnreleasedMinutes": max(required - released, 0),
                "RemainingMinutes": required,
                "OverloadMinutes": sum(
                    int(cell.get("OverloadMinutes", 0)) for cell in cells
                ),
                "IsCandidateConstraint": not bool(
                    row.get("IsConstraint", False)
                )
                and any(float(cell.get("LoadPercent", 0)) > 100 for cell in cells),
            }
        )
    return {"Rows": system_rows}, {"Rows": daily_rows}


def _build_order_delivery(
    *,
    master_data_version: dict[str, object],
    gantt_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    completion_by_order: dict[str, datetime] = {}
    for row in gantt_rows:
        for bar in _dict_list(row.get("Bars")):
            if bar.get("BarType") != "Processing":
                continue
            order_id = str(bar.get("OrderID"))
            end = _parse_datetime(bar.get("End"))
            if end is not None and (
                order_id not in completion_by_order
                or end > completion_by_order[order_id]
            ):
                completion_by_order[order_id] = end
    result = []
    for order in _dict_list(master_data_version.get("Orders")):
        order_id = str(order.get("OrderID"))
        due = _parse_datetime(order.get("DueDate"))
        completion = completion_by_order.get(order_id)
        if completion is None or due is None:
            status = "Unscheduled"
            delay = None
        else:
            delay = max(int((completion - due).total_seconds() / 60), 0)
            status = "Late" if delay else "OnTime"
        result.append(
            {
                "OrderID": order_id,
                "ProductID": order.get("ProductID"),
                "DueDate": due.isoformat() if due else order.get("DueDate"),
                "PlannedCompletionAt": completion.isoformat()
                if completion
                else None,
                "Status": status,
                "DelayMinutes": delay,
            }
        )
    return result


def _filter_options(
    *,
    resources: dict[str, dict[str, object]],
    gantt_rows: list[dict[str, object]],
    buffer_zones: dict[str, str],
) -> dict[str, object]:
    resource_ids = {str(row["ResourceID"]) for row in gantt_rows}
    orders = sorted(
        {
            str(bar.get("OrderID"))
            for row in gantt_rows
            for bar in _dict_list(row.get("Bars"))
            if bar.get("OrderID")
        }
    )
    return {
        "Resources": [resources[item] for item in sorted(resource_ids)],
        "Orders": orders,
        "BarTypes": ["Processing", "TimeBuffer", "Maintenance", "Unavailable"],
        "BufferZones": sorted(set(buffer_zones.values())),
        "ResourceTypes": _distinct(resources, "ResourceType"),
        "Locations": _distinct(resources, "LocationID"),
        "Owners": _distinct(resources, "OwnerID"),
        "Categories": _distinct(resources, "Category"),
    }


def _resource_metadata(
    master_data_version: dict[str, object],
) -> dict[str, dict[str, object]]:
    result = {}
    for item in _dict_list(master_data_version.get("Resources")):
        resource_id = str(item.get("ResourceID"))
        result[resource_id] = {
            "ResourceID": resource_id,
            "ResourceName": item.get("Name") or item.get("ResourceName") or resource_id,
            "IsConstraint": bool(item.get("IsConstraint", False)),
            "ResourceType": item.get("ResourceType") or item.get("Type"),
            "IsBuffered": bool(item.get("IsBuffered", False)),
            "LocationID": item.get("LocationID"),
            "OwnerID": item.get("OwnerID"),
            "Category": item.get("Category"),
            "Calendar": item.get("Calendar"),
        }
    return result


def _append_downtime_bars(
    *,
    schedule: dict[str, object],
    resources: dict[str, dict[str, object]],
    rows_by_resource: dict[str, dict[str, object]],
) -> None:
    for resource_id, metadata in resources.items():
        row = rows_by_resource.get(resource_id)
        if row is None:
            continue
        calendar = _dict(metadata.get("Calendar"))
        for window in _dict_list(calendar.get("MaintenanceWindows")):
            start = window.get("Start")
            end = window.get("End")
            parsed_start = _parse_datetime(start)
            parsed_end = _parse_datetime(end)
            if parsed_start is None or parsed_end is None:
                continue
            row["Bars"].append(
                {
                    "OperationID": "MAINTENANCE",
                    "OrderID": None,
                    "Start": parsed_start.isoformat(),
                    "End": parsed_end.isoformat(),
                    "DurationMinutes": int(
                        (parsed_end - parsed_start).total_seconds() / 60
                    ),
                    "BarType": "Maintenance",
                    "BufferZone": None,
                }
            )


def _append_calendar_override_bars(
    *,
    calendar_overrides: list[dict[str, object]],
    resources: dict[str, dict[str, object]],
    rows_by_resource: dict[str, dict[str, object]],
) -> None:
    for override in calendar_overrides:
        if override.get("Status") != "Active":
            continue
        if override.get("OverrideType") != "ExclusionOrMaintenance":
            continue
        parsed_start = _parse_datetime(override.get("EffectiveStartAt"))
        parsed_end = _parse_datetime(override.get("EffectiveEndAt"))
        if parsed_start is None or parsed_end is None:
            continue
        for resource_id in _override_resource_ids(override, resources):
            row = rows_by_resource.get(resource_id)
            if row is None:
                continue
            row["Bars"].append(
                {
                    "OperationID": override.get("OverrideID") or "CALENDAR-OVERRIDE",
                    "OrderID": None,
                    "Start": parsed_start.isoformat(),
                    "End": parsed_end.isoformat(),
                    "DurationMinutes": int(
                        (parsed_end - parsed_start).total_seconds() / 60
                    ),
                    "BarType": "Maintenance",
                    "BufferZone": None,
                }
            )


def _override_resource_ids(
    override: dict[str, object],
    resources: dict[str, dict[str, object]],
) -> list[str]:
    resource_id = override.get("ResourceID")
    if resource_id:
        return [str(resource_id)] if str(resource_id) in resources else []
    calendar_id = override.get("CalendarID")
    return [
        item_resource_id
        for item_resource_id, metadata in resources.items()
        if _dict(metadata.get("Calendar")).get("CalendarID") == calendar_id
    ]
    reference_tz = None
    for row in rows_by_resource.values():
        for bar in _dict_list(row.get("Bars")):
            parsed = _parse_datetime(bar.get("Start"))
            if parsed is not None:
                reference_tz = parsed.tzinfo
                break
        if reference_tz is not None:
            break
    for load_row in _dict_list(schedule.get("LoadGraphRows")):
        resource_id = str(load_row.get("ResourceID"))
        row = rows_by_resource.get(resource_id)
        if row is None:
            continue
        for cell in _dict_list(load_row.get("Cells")):
            if int(cell.get("CapacityMinutes", 0)) > 0:
                continue
            try:
                bucket_date = date.fromisoformat(str(cell.get("Date")))
            except ValueError:
                continue
            start = datetime.combine(bucket_date, time.min, tzinfo=reference_tz)
            row["Bars"].append(
                {
                    "OperationID": "UNAVAILABLE",
                    "OrderID": None,
                    "Start": start.isoformat(),
                    "End": (start + timedelta(days=1)).isoformat(),
                    "DurationMinutes": 1440,
                    "BarType": "Unavailable",
                    "BufferZone": None,
                }
            )


def _schedule(planning_run: dict[str, object]) -> dict[str, object]:
    return _dict(planning_run.get("Schedule"))


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _distinct(
    resources: dict[str, dict[str, object]], key: str
) -> list[object]:
    return sorted(
        {item[key] for item in resources.values() if item.get(key) is not None},
        key=str,
    )


def _scenario_score(kpis: dict[str, object]) -> tuple[float, ...]:
    return (
        float(kpis.get("LateOrderCount", 0)),
        float(kpis.get("TotalOverloadMinutes", 0)),
        float(kpis.get("RedBufferCount", 0)),
        float(kpis.get("MaxLoadPercent", 0)),
    )


def _decision_codes(
    delta: dict[str, object], candidate_recommended: bool
) -> list[str]:
    codes = []
    if float(delta["TotalOverloadMinutes"]) < 0:
        codes.append("CANDIDATE_REDUCES_OVERLOAD")
    if float(delta["LateOrderCount"]) < 0:
        codes.append("CANDIDATE_REDUCES_LATE_ORDERS")
    if float(delta["RedBufferCount"]) < 0:
        codes.append("CANDIDATE_REDUCES_RED_BUFFERS")
    if not codes:
        codes.append(
            "CANDIDATE_BETTER_SCORE"
            if candidate_recommended
            else "BASELINE_BETTER_SCORE"
        )
    return codes
