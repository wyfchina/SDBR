from sdbr.schedule_output import (
    scheduled_order_rows_from_schedule,
    scheduled_work_order_rows_from_schedule,
)


def test_flattens_gantt_rows_into_scheduled_work_order_operations():
    schedule = {
        "GanttRows": [
            {
                "ResourceID": "WC-B",
                "Bars": [
                    {
                        "OrderID": "WO-2",
                        "OperationID": "ASM",
                        "Start": "2026-06-16T09:00:00+00:00",
                        "End": "2026-06-16T10:00:00+00:00",
                        "DurationMinutes": 60,
                    }
                ],
            },
            {
                "ResourceID": "WC-A",
                "Bars": [
                    {
                        "OrderID": "WO-1",
                        "OperationID": "CUT",
                        "Start": "2026-06-16T08:00:00+00:00",
                        "End": "2026-06-16T09:00:00+00:00",
                        "DurationMinutes": 60,
                    },
                    {
                        "OrderID": "WO-3",
                        "OperationID": "CUT",
                        "Start": "2026-06-16T09:00:00+00:00",
                        "End": "2026-06-16T09:30:00+00:00",
                        "DurationMinutes": 30,
                    },
                ],
            },
        ]
    }

    rows = scheduled_work_order_rows_from_schedule(schedule)

    assert rows == [
        {
            "OrderID": "WO-1",
            "OperationID": "CUT",
            "ResourceID": "WC-A",
            "Start": "2026-06-16T08:00:00+00:00",
            "End": "2026-06-16T09:00:00+00:00",
            "DurationMinutes": 60,
        },
        {
            "OrderID": "WO-3",
            "OperationID": "CUT",
            "ResourceID": "WC-A",
            "Start": "2026-06-16T09:00:00+00:00",
            "End": "2026-06-16T09:30:00+00:00",
            "DurationMinutes": 30,
        },
        {
            "OrderID": "WO-2",
            "OperationID": "ASM",
            "ResourceID": "WC-B",
            "Start": "2026-06-16T09:00:00+00:00",
            "End": "2026-06-16T10:00:00+00:00",
            "DurationMinutes": 60,
        },
    ]


def test_aggregates_scheduled_operations_into_order_rows():
    schedule = {
        "GanttRows": [
            {
                "ResourceID": "WC-ASM",
                "Bars": [
                    {
                        "OrderID": "WO-1",
                        "OperationID": "WO-1:ASM",
                        "Start": "2026-06-16T10:00:00+00:00",
                        "End": "2026-06-16T11:20:00+00:00",
                        "DurationMinutes": 80,
                    }
                ],
            },
            {
                "ResourceID": "WC-DRUM",
                "Bars": [
                    {
                        "OrderID": "WO-2",
                        "OperationID": "WO-2:CUT",
                        "Start": "2026-06-16T08:30:00+00:00",
                        "End": "2026-06-16T09:00:00+00:00",
                        "DurationMinutes": 30,
                    },
                    {
                        "OrderID": "WO-1",
                        "OperationID": "WO-1:CUT",
                        "Start": "2026-06-16T08:00:00+00:00",
                        "End": "2026-06-16T10:00:00+00:00",
                        "DurationMinutes": 120,
                    },
                ],
            },
        ]
    }

    rows = scheduled_order_rows_from_schedule(schedule)

    assert rows == [
        {
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T11:20:00+00:00",
            "FirstOperationID": "WO-1:CUT",
            "FirstResourceID": "WC-DRUM",
            "LastOperationID": "WO-1:ASM",
            "LastResourceID": "WC-ASM",
            "OperationCount": 2,
            "TotalDurationMinutes": 200,
            "ResourceIDs": ["WC-DRUM", "WC-ASM"],
        },
        {
            "OrderID": "WO-2",
            "ScheduledStart": "2026-06-16T08:30:00+00:00",
            "ScheduledEnd": "2026-06-16T09:00:00+00:00",
            "FirstOperationID": "WO-2:CUT",
            "FirstResourceID": "WC-DRUM",
            "LastOperationID": "WO-2:CUT",
            "LastResourceID": "WC-DRUM",
            "OperationCount": 1,
            "TotalDurationMinutes": 30,
            "ResourceIDs": ["WC-DRUM"],
        },
    ]
