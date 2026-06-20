from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sdbr.planner_workbench import MaintenanceWindow, Resource, Shift, WorkCalendar


@dataclass(frozen=True, slots=True)
class CalendarImportRow:
    resource_id: str
    calendar_id: str
    working_weekdays: list[int]
    shift_name: str | None = None
    shift_start: time | None = None
    shift_end: time | None = None
    holiday: date | None = None
    maintenance_start: datetime | None = None
    maintenance_end: datetime | None = None


def import_work_calendars_from_rows(rows: list[CalendarImportRow]) -> dict[str, WorkCalendar]:
    grouped: dict[
        tuple[str, str],
        dict[str, object],
    ] = {}
    for row in rows:
        bucket = grouped.setdefault(
            (row.resource_id, row.calendar_id),
            {
                "weekdays": set(),
                "shifts": set(),
                "holidays": set(),
                "maintenance_windows": set(),
            },
        )
        bucket["weekdays"].update(row.working_weekdays)
        if row.shift_name is not None and row.shift_start is not None and row.shift_end is not None:
            bucket["shifts"].add((row.shift_name, row.shift_start, row.shift_end))
        if row.holiday is not None:
            bucket["holidays"].add(row.holiday)
        if row.maintenance_start is not None and row.maintenance_end is not None:
            bucket["maintenance_windows"].add((row.maintenance_start, row.maintenance_end))

    calendars_by_resource: dict[str, WorkCalendar] = {}
    for (resource_id, calendar_id), bucket in sorted(grouped.items()):
        calendars_by_resource[resource_id] = WorkCalendar(
            calendar_id=calendar_id,
            working_weekdays=set(sorted(bucket["weekdays"])),
            shifts=[
                Shift(name=name, start=start, end=end)
                for name, start, end in sorted(bucket["shifts"])
            ],
            maintenance_windows=[
                MaintenanceWindow(start=start, end=end)
                for start, end in sorted(bucket["maintenance_windows"])
            ],
            holidays=set(sorted(bucket["holidays"])),
        )
    return calendars_by_resource


def attach_work_calendars_to_resources(
    resources: list[Resource],
    calendars_by_resource: dict[str, WorkCalendar],
) -> list[Resource]:
    return [
        Resource(
            resource_id=resource.resource_id,
            name=resource.name,
            is_constraint=resource.is_constraint,
            daily_capacity_minutes=resource.daily_capacity_minutes,
            calendar=calendars_by_resource.get(resource.resource_id, resource.calendar),
        )
        for resource in resources
    ]
