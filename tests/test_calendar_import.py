from datetime import date, datetime, time

from sdbr.calendar_import import (
    CalendarImportRow,
    attach_work_calendars_to_resources,
    import_work_calendars_from_rows,
)
from sdbr.planner_workbench import Resource


def test_import_work_calendars_from_rows_groups_shifts_holidays_and_maintenance():
    rows = [
        CalendarImportRow(
            resource_id="WC-DRUM",
            calendar_id="CAL-DRUM",
            working_weekdays=[0, 1, 2, 3, 4],
            shift_name="Day",
            shift_start=time(8, 0),
            shift_end=time(16, 0),
        ),
        CalendarImportRow(
            resource_id="WC-DRUM",
            calendar_id="CAL-DRUM",
            working_weekdays=[0, 1, 2, 3, 4],
            shift_name="Evening",
            shift_start=time(16, 0),
            shift_end=time(20, 0),
            holiday=date(2026, 6, 18),
            maintenance_start=datetime(2026, 6, 16, 10, 0),
            maintenance_end=datetime(2026, 6, 16, 11, 0),
        ),
    ]

    calendars_by_resource = import_work_calendars_from_rows(rows)

    calendar = calendars_by_resource["WC-DRUM"]
    assert calendar.calendar_id == "CAL-DRUM"
    assert calendar.working_weekdays == {0, 1, 2, 3, 4}
    assert [shift.name for shift in calendar.shifts] == ["Day", "Evening"]
    assert calendar.holidays == {date(2026, 6, 18)}
    assert calendar.maintenance_windows[0].start == datetime(2026, 6, 16, 10, 0)


def test_attach_work_calendars_to_resources_sets_calendar_by_resource_id():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 480},
    )
    calendar = import_work_calendars_from_rows(
        [
            CalendarImportRow(
                resource_id="WC-DRUM",
                calendar_id="CAL-DRUM",
                working_weekdays=[0, 1, 2, 3, 4],
                shift_name="Day",
                shift_start=time(8, 0),
                shift_end=time(16, 0),
            )
        ]
    )

    resources = attach_work_calendars_to_resources([resource], calendar)

    assert resources[0].calendar is not None
    assert resources[0].calendar.calendar_id == "CAL-DRUM"
