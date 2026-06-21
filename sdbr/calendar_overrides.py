from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from sdbr.planner_workbench import (
    ExtraCapacityWindow,
    MaintenanceWindow,
    Resource,
    WorkCalendar,
)
from sdbr.scheduling_solver import SolverDiagnostic


@dataclass(frozen=True, slots=True)
class CalendarOverrideApplication:
    resources: list[Resource]
    diagnostics: list[SolverDiagnostic]
    applied_overrides: list[dict[str, object]]


def apply_calendar_overrides(
    *,
    resources: list[Resource],
    overrides: list[dict[str, object]],
) -> CalendarOverrideApplication:
    active_overrides = [
        override for override in overrides if override.get("Status") == "Active"
    ]
    resources_by_id = {resource.resource_id: resource for resource in resources}
    diagnostics: list[SolverDiagnostic] = []
    applied: list[dict[str, object]] = []

    for override in active_overrides:
        override_id = str(override.get("OverrideID"))
        override_type = str(override.get("OverrideType"))
        start = _parse_datetime(override.get("EffectiveStartAt"))
        end = _parse_datetime(override.get("EffectiveEndAt"))
        if start is None or end is None or end <= start:
            diagnostics.append(
                SolverDiagnostic(
                    severity="Warning",
                    code="CALENDAR_OVERRIDE_NOT_APPLIED",
                    message="Calendar override has an invalid effective window.",
                    entity_id=override_id,
                )
            )
            continue
        matched_ids = _matched_resource_ids(resources_by_id.values(), override)
        if not matched_ids:
            diagnostics.append(
                SolverDiagnostic(
                    severity="Information",
                    code="CALENDAR_OVERRIDE_NOT_APPLIED",
                    message="Calendar override did not match any resource or calendar.",
                    entity_id=override_id,
                )
            )
            continue
        for resource_id in matched_ids:
            resource = resources_by_id[resource_id]
            if override_type == "ExclusionOrMaintenance":
                if resource.calendar is None:
                    diagnostics.append(
                        SolverDiagnostic(
                            severity="Warning",
                            code="CALENDAR_OVERRIDE_NOT_APPLIED",
                            message="Maintenance override requires a resource calendar.",
                            entity_id=override_id,
                        )
                    )
                    continue
                resource = replace(
                    resource,
                    calendar=_calendar_with_maintenance(
                        resource.calendar,
                        MaintenanceWindow(start=start, end=end),
                    ),
                )
            elif override_type in {"Overtime", "TemporaryShiftOverride"}:
                resource = replace(
                    resource,
                    extra_capacity_windows=[
                        *resource.extra_capacity_windows,
                        ExtraCapacityWindow(
                            start=start,
                            end=end,
                            capacity_minutes=_capacity_minutes(override, start, end),
                            source_id=override_id,
                        ),
                    ],
                )
            else:
                diagnostics.append(
                    SolverDiagnostic(
                        severity="Warning",
                        code="CALENDAR_OVERRIDE_NOT_APPLIED",
                        message=f"Unsupported calendar override type {override_type}.",
                        entity_id=override_id,
                    )
                )
                continue
            resources_by_id[resource_id] = resource
            applied.append(
                {
                    "OverrideID": override_id,
                    "ResourceID": resource_id,
                    "OverrideType": override_type,
                    "EffectiveStartAt": start.isoformat(),
                    "EffectiveEndAt": end.isoformat(),
                }
            )

    if applied:
        diagnostics.append(
            SolverDiagnostic(
                severity="Information",
                code="CALENDAR_OVERRIDES_APPLIED",
                message=f"{len(applied)} calendar override application(s) were applied.",
            )
        )
    return CalendarOverrideApplication(
        resources=[resources_by_id[resource.resource_id] for resource in resources],
        diagnostics=diagnostics,
        applied_overrides=applied,
    )


def calendar_override_driver_status(
    *,
    override: dict[str, object],
    resources: list[Resource],
    applied_override_ids: set[str] | None = None,
) -> str:
    if applied_override_ids and str(override.get("OverrideID")) in applied_override_ids:
        return "AppliedInRun"
    if override.get("Status") != "Active":
        return "NotApplied"
    return "Eligible" if _matched_resource_ids(resources, override) else "NotApplied"


def _matched_resource_ids(
    resources: list[Resource] | object,
    override: dict[str, object],
) -> list[str]:
    resource_list = list(resources) if not isinstance(resources, list) else resources
    requested_resource_id = override.get("ResourceID")
    calendar_id = override.get("CalendarID")
    if requested_resource_id:
        return [
            resource.resource_id
            for resource in resource_list
            if resource.resource_id == requested_resource_id
        ]
    return [
        resource.resource_id
        for resource in resource_list
        if resource.calendar is not None and resource.calendar.calendar_id == calendar_id
    ]


def _calendar_with_maintenance(
    calendar: WorkCalendar,
    window: MaintenanceWindow,
) -> WorkCalendar:
    return replace(
        calendar,
        maintenance_windows=[*calendar.maintenance_windows, window],
    )


def _capacity_minutes(
    override: dict[str, object],
    start: datetime,
    end: datetime,
) -> int:
    configured = int(override.get("CapacityDeltaMinutes") or 0)
    if configured > 0:
        return configured
    return int((end - start).total_seconds() / 60)


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None
