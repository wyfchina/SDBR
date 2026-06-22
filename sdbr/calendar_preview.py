from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta, tzinfo as TzInfo

from sdbr.base_calendar import apply_base_calendar_assignments
from sdbr.calendar_overrides import apply_calendar_overrides
from sdbr.planner_workbench import Resource
from sdbr.scheduling_solver import build_capacity_buckets_from_resources


CONFLICT_PRIORITY = [
    "Maintenance",
    "Holiday",
    "TemporaryShiftOverride",
    "Overtime",
    "BaseShift",
]


def calendar_preview_required_elements() -> list[dict[str, object]]:
    return [
        {
            "ElementID": "RESOURCE_CALENDAR_ASSIGNMENT",
            "Element": "资源日历分配",
            "CpSatNeedReason": "CP-SAT 需要知道每个资源使用哪个日历生成能力桶。",
            "MissingImpactDomain": "资源可能回退到日能力总量，最终排程与现场班次不一致。",
        },
        {
            "ElementID": "BASE_SHIFT",
            "Element": "基础班次开始/结束",
            "CpSatNeedReason": "基础班次决定资源在一天内哪些时间可以加工。",
            "MissingImpactDomain": "工序可能被排到非工作时间，或可用产能被低估。",
        },
        {
            "ElementID": "WORKING_WEEKDAY",
            "Element": "工作日规则",
            "CpSatNeedReason": "工作日规则决定日历是否在某天生效。",
            "MissingImpactDomain": "周末或非工作日可能被错误排产。",
        },
        {
            "ElementID": "HOLIDAY",
            "Element": "节假日",
            "CpSatNeedReason": "节假日按当前规则会扣除当天所有基础班次、加班和临时覆盖。",
            "MissingImpactDomain": "计划可能排到停工日；若节假日强制加班未定义，也可能低估产能。",
        },
        {
            "ElementID": "MAINTENANCE",
            "Element": "维护/停机窗口",
            "CpSatNeedReason": "维护窗口优先级最高，会切掉所有低优先级可用窗口。",
            "MissingImpactDomain": "工序可能排到设备维护期间，现场不可执行。",
        },
        {
            "ElementID": "OVERTIME",
            "Element": "加班窗口",
            "CpSatNeedReason": "加班窗口增加额外能力桶，用于处理短期产能增加。",
            "MissingImpactDomain": "紧急订单可能被误判为不可行或延后。",
        },
        {
            "ElementID": "TEMPORARY_SHIFT_OVERRIDE",
            "Element": "临时班次覆盖",
            "CpSatNeedReason": "临时覆盖体现计划员短期调整，当前按新增可用窗口处理。",
            "MissingImpactDomain": "重排结果无法反映临时排班变化。",
        },
        {
            "ElementID": "CONFLICT_PRIORITY",
            "Element": "冲突优先级",
            "CpSatNeedReason": "多条日历规则重叠时，必须唯一确定最终可用窗口。",
            "MissingImpactDomain": "同一时间可能被同时解释为可用和不可用。",
        },
        {
            "ElementID": "TIMEZONE",
            "Element": "时区",
            "CpSatNeedReason": "日期、班次和交期必须落在同一时区语义下计算。",
            "MissingImpactDomain": "跨天、跨班次和节假日判断可能偏移。",
        },
        {
            "ElementID": "CROSS_SHIFT_PROCESSING_RULE",
            "Element": "跨班次加工规则",
            "CpSatNeedReason": "长工序是否允许跨窗口加工会改变可行性。",
            "MissingImpactDomain": "长工序可能被错误判断为可行或不可行；当前 CP-SAT 要求工序完整落入一个能力桶。",
        },
    ]


def build_calendar_preview(
    *,
    resources: list[Resource],
    base_calendars: list[dict[str, object]],
    resource_calendar_assignments: list[dict[str, object]],
    calendar_overrides: list[dict[str, object]],
    start_date: date,
    end_date: date,
    tzinfo: TzInfo,
    resource_id: str | None = None,
) -> dict[str, object]:
    selected_resources = [
        resource for resource in resources if resource_id in {None, resource.resource_id}
    ]
    selected_resources = [
        _restrict_resource_capacity_dates(
            resource=resource,
            start_date=start_date,
            end_date=end_date,
        )
        for resource in selected_resources
    ]
    base_application = apply_base_calendar_assignments(
        resources=selected_resources,
        calendars=base_calendars,
        assignments=resource_calendar_assignments,
    )
    override_application = apply_calendar_overrides(
        resources=base_application.resources,
        overrides=calendar_overrides,
    )
    buckets = build_capacity_buckets_from_resources(
        override_application.resources,
        tzinfo=tzinfo,
    )
    return {
        "PreviewMode": "CalendarPreviewV1",
        "CalendarScope": "ResourceOnly",
        "StartDate": start_date.isoformat(),
        "EndDate": end_date.isoformat(),
        "Timezone": str(tzinfo),
        "ConflictPriority": CONFLICT_PRIORITY,
        "RequiredElements": calendar_preview_required_elements(),
        "Summary": {
            "ResourceCount": len(selected_resources),
            "BaseCalendarCount": len(base_calendars),
            "ActiveBaseCalendarCount": sum(
                1 for item in base_calendars if item.get("Status") == "Active"
            ),
            "ActiveAssignmentCount": sum(
                1
                for item in resource_calendar_assignments
                if item.get("Status") == "Active"
            ),
            "ActiveOverrideCount": sum(
                1 for item in calendar_overrides if item.get("Status") == "Active"
            ),
            "FinalWindowCount": len(buckets),
            "MissingDailyCapacityDateCount": sum(
                len(_missing_capacity_dates(resource, start_date, end_date))
                for resource in selected_resources
            ),
        },
        "Resources": [
            _resource_preview(
                resource=resource,
                final_resources=override_application.resources,
                buckets=buckets,
                start_date=start_date,
                end_date=end_date,
                base_calendars=base_calendars,
                assignments=resource_calendar_assignments,
                overrides=calendar_overrides,
            )
            for resource in selected_resources
        ],
        "Diagnostics": [
            _diagnostic_to_dict(item)
            for item in [*base_application.diagnostics, *override_application.diagnostics]
        ],
    }


def _resource_preview(
    *,
    resource: Resource,
    final_resources: list[Resource],
    buckets: list[object],
    start_date: date,
    end_date: date,
    base_calendars: list[dict[str, object]],
    assignments: list[dict[str, object]],
    overrides: list[dict[str, object]],
) -> dict[str, object]:
    final_resource = next(
        item for item in final_resources if item.resource_id == resource.resource_id
    )
    active_assignment = next(
        (
            item
            for item in assignments
            if item.get("Status") == "Active"
            and item.get("ResourceID") == resource.resource_id
        ),
        None,
    )
    calendar_id = (
        str(active_assignment.get("CalendarID"))
        if active_assignment is not None and active_assignment.get("CalendarID")
        else (
            final_resource.calendar.calendar_id
            if final_resource.calendar is not None
            else None
        )
    )
    return {
        "ResourceID": resource.resource_id,
        "ResourceName": resource.name,
        "CalendarID": calendar_id,
        "MissingDailyCapacityDates": [
            item.isoformat()
            for item in _missing_capacity_dates(resource, start_date, end_date)
        ],
        "Elements": _calendar_elements_for_resource(
            resource=final_resource,
            calendar_id=calendar_id,
            base_calendars=base_calendars,
            assignments=assignments,
            overrides=overrides,
        ),
        "FinalCapacityWindows": [
            {
                "ResourceID": bucket.resource_id,
                "Start": bucket.bucket_start.isoformat(),
                "End": bucket.bucket_end.isoformat(),
                "CapacityMinutes": bucket.capacity_minutes,
            }
            for bucket in buckets
            if bucket.resource_id == resource.resource_id
        ],
    }


def _calendar_elements_for_resource(
    *,
    resource: Resource,
    calendar_id: str | None,
    base_calendars: list[dict[str, object]],
    assignments: list[dict[str, object]],
    overrides: list[dict[str, object]],
) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    active_assignment = next(
        (
            item
            for item in assignments
            if item.get("Status") == "Active"
            and item.get("ResourceID") == resource.resource_id
        ),
        None,
    )
    if active_assignment is not None:
        elements.append(
            {
                "ElementType": "ResourceCalendarAssignment",
                "SourceID": active_assignment.get("AssignmentID"),
                "Status": active_assignment.get("Status"),
                "CalendarID": active_assignment.get("CalendarID"),
                "Applied": True,
            }
        )
    calendar_payload = next(
        (
            item
            for item in base_calendars
            if str(item.get("CalendarID")) == str(calendar_id)
        ),
        None,
    )
    if calendar_payload is not None:
        for shift in _dict_list(calendar_payload.get("Shifts")):
            elements.append(
                {
                    "ElementType": "BaseShift",
                    "SourceID": calendar_payload.get("CalendarID"),
                    "Status": calendar_payload.get("Status"),
                    "ShiftName": shift.get("Name"),
                    "Start": shift.get("Start"),
                    "End": shift.get("End"),
                    "Applied": calendar_payload.get("Status") == "Active",
                }
            )
        for holiday in _list(calendar_payload.get("Holidays")):
            elements.append(
                {
                    "ElementType": "Holiday",
                    "SourceID": calendar_payload.get("CalendarID"),
                    "Date": str(holiday),
                    "Applied": calendar_payload.get("Status") == "Active",
                }
            )
        for window in _dict_list(calendar_payload.get("MaintenanceWindows")):
            elements.append(
                {
                    "ElementType": "Maintenance",
                    "SourceID": calendar_payload.get("CalendarID"),
                    "Start": window.get("Start"),
                    "End": window.get("End"),
                    "Applied": calendar_payload.get("Status") == "Active",
                }
            )
    for override in overrides:
        if override.get("Status") != "Active":
            continue
        if not _override_matches_resource(
            resource_id=resource.resource_id,
            calendar_id=calendar_id,
            override=override,
        ):
            continue
        elements.append(
            {
                "ElementType": override.get("OverrideType"),
                "SourceID": override.get("OverrideID"),
                "Status": override.get("Status"),
                "Start": override.get("EffectiveStartAt"),
                "End": override.get("EffectiveEndAt"),
                "CapacityDeltaMinutes": override.get("CapacityDeltaMinutes"),
                "Reason": override.get("Reason"),
                "Applied": True,
            }
        )
    if resource.calendar is not None:
        for window in resource.extra_capacity_windows:
            elements.append(
                {
                    "ElementType": "ExtraCapacityWindow",
                    "SourceID": window.source_id,
                    "Start": window.start.isoformat(),
                    "End": window.end.isoformat(),
                    "CapacityMinutes": window.capacity_minutes,
                    "Applied": True,
                }
            )
    return elements


def _restrict_resource_capacity_dates(
    *,
    resource: Resource,
    start_date: date,
    end_date: date,
) -> Resource:
    allowed_dates = set(_date_range(start_date, end_date))
    return replace(
        resource,
        daily_capacity_minutes={
            bucket_date: minutes
            for bucket_date, minutes in resource.daily_capacity_minutes.items()
            if bucket_date in allowed_dates
        },
    )


def _missing_capacity_dates(
    resource: Resource,
    start_date: date,
    end_date: date,
) -> list[date]:
    return [
        bucket_date
        for bucket_date in _date_range(start_date, end_date)
        if bucket_date not in resource.daily_capacity_minutes
    ]


def _date_range(start_date: date, end_date: date) -> list[date]:
    days = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(days + 1)]


def _override_matches_resource(
    *,
    resource_id: str,
    calendar_id: str | None,
    override: dict[str, object],
) -> bool:
    if override.get("ResourceID"):
        return str(override.get("ResourceID")) == resource_id
    return calendar_id is not None and str(override.get("CalendarID")) == str(calendar_id)


def _diagnostic_to_dict(diagnostic: object) -> dict[str, object]:
    return {
        "Severity": getattr(diagnostic, "severity", None),
        "Code": getattr(diagnostic, "code", None),
        "Message": getattr(diagnostic, "message", None),
        "EntityID": getattr(diagnostic, "entity_id", None),
    }


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []
