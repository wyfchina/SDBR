from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time

from sdbr.planner_workbench import MaintenanceWindow, Resource, Shift, WorkCalendar
from sdbr.scheduling_solver import SolverDiagnostic


@dataclass(frozen=True, slots=True)
class BaseCalendarApplication:
    resources: list[Resource]
    diagnostics: list[SolverDiagnostic]
    applied_assignments: list[dict[str, object]]


def apply_base_calendar_assignments(
    *,
    resources: list[Resource],
    calendars: list[dict[str, object]],
    assignments: list[dict[str, object]],
) -> BaseCalendarApplication:
    active_calendars = {
        str(calendar.get("CalendarID")): calendar
        for calendar in calendars
        if calendar.get("Status") == "Active"
    }
    active_assignments = [
        assignment
        for assignment in assignments
        if assignment.get("Status") == "Active"
    ]
    resources_by_id = {resource.resource_id: resource for resource in resources}
    diagnostics: list[SolverDiagnostic] = []
    applied: list[dict[str, object]] = []

    for assignment in active_assignments:
        assignment_id = str(assignment.get("AssignmentID"))
        resource_id = str(assignment.get("ResourceID"))
        calendar_id = str(assignment.get("CalendarID"))
        resource = resources_by_id.get(resource_id)
        if resource is None:
            diagnostics.append(
                SolverDiagnostic(
                    severity="Information",
                    code="BASE_CALENDAR_ASSIGNMENT_NOT_APPLIED",
                    message="Base calendar assignment did not match a resource.",
                    entity_id=assignment_id,
                )
            )
            continue
        calendar_payload = active_calendars.get(calendar_id)
        if calendar_payload is None:
            diagnostics.append(
                SolverDiagnostic(
                    severity="Warning",
                    code="BASE_CALENDAR_ASSIGNMENT_NOT_APPLIED",
                    message="Base calendar assignment references a missing or inactive calendar.",
                    entity_id=assignment_id,
                )
            )
            continue
        calendar = work_calendar_from_payload(calendar_payload)
        resources_by_id[resource_id] = replace(resource, calendar=calendar)
        applied.append(
            {
                "AssignmentID": assignment_id,
                "ResourceID": resource_id,
                "CalendarID": calendar.calendar_id,
            }
        )

    if applied:
        diagnostics.append(
            SolverDiagnostic(
                severity="Information",
                code="BASE_CALENDARS_APPLIED",
                message=f"{len(applied)} base calendar assignment(s) were applied.",
            )
        )

    return BaseCalendarApplication(
        resources=[resources_by_id[resource.resource_id] for resource in resources],
        diagnostics=diagnostics,
        applied_assignments=applied,
    )


def work_calendar_from_payload(payload: dict[str, object]) -> WorkCalendar:
    return WorkCalendar(
        calendar_id=str(payload["CalendarID"]),
        working_weekdays={int(item) for item in _list(payload.get("WorkingWeekdays"))},
        shifts=[
            Shift(
                name=str(item.get("Name")),
                start=_parse_time(item.get("Start")),
                end=_parse_time(item.get("End")),
            )
            for item in _dict_list(payload.get("Shifts"))
        ],
        maintenance_windows=[
            MaintenanceWindow(
                start=_parse_datetime(item.get("Start")),
                end=_parse_datetime(item.get("End")),
            )
            for item in _dict_list(payload.get("MaintenanceWindows"))
        ],
        holidays={_parse_date(item) for item in _list(payload.get("Holidays"))},
    )


def base_calendar_driver_status(
    *,
    calendar: dict[str, object],
    assignments: list[dict[str, object]],
    applied_calendar_ids: set[str] | None = None,
) -> str:
    calendar_id = str(calendar.get("CalendarID"))
    if applied_calendar_ids and calendar_id in applied_calendar_ids:
        return "AppliedInRun"
    if calendar.get("Status") != "Active":
        return "NotApplied"
    return (
        "Eligible"
        if any(
            assignment.get("Status") == "Active"
            and str(assignment.get("CalendarID")) == calendar_id
            for assignment in assignments
        )
        else "NotAssigned"
    )


def resource_calendar_assignment_driver_status(
    *,
    assignment: dict[str, object],
    resources: list[Resource],
    calendars: list[dict[str, object]],
    applied_assignment_ids: set[str] | None = None,
) -> str:
    assignment_id = str(assignment.get("AssignmentID"))
    if applied_assignment_ids and assignment_id in applied_assignment_ids:
        return "AppliedInRun"
    if assignment.get("Status") != "Active":
        return "NotApplied"
    resource_ids = {resource.resource_id for resource in resources}
    active_calendar_ids = {
        str(calendar.get("CalendarID"))
        for calendar in calendars
        if calendar.get("Status") == "Active"
    }
    if str(assignment.get("ResourceID")) not in resource_ids:
        return "NotApplied"
    if str(assignment.get("CalendarID")) not in active_calendar_ids:
        return "NotApplied"
    return "Eligible"


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _parse_time(value: object) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value))


def _parse_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
