from datetime import datetime, timezone

from sdbr.gantt_view import build_gantt_rows
from sdbr.scheduling_solver import OperationAssignment, SchedulingResult


def test_gantt_rows_group_assignments_by_resource():
    result = SchedulingResult(
        backend_id="baseline-finite",
        status="Feasible",
        message="ok",
        assignments=[
            OperationAssignment(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
                end=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            ),
            OperationAssignment(
                operation_id="WO-2:ASM",
                order_id="WO-2",
                resource_id="WC-ASM",
                start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
                end=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
            ),
        ],
    )

    rows = build_gantt_rows(result)

    assert [row.resource_id for row in rows] == ["WC-ASM", "WC-DRUM"]
    assert rows[0].bars[0].operation_id == "WO-2:ASM"
    assert rows[0].bars[0].order_id == "WO-2"
    assert rows[0].bars[0].start == datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    assert rows[0].bars[0].end == datetime(2026, 6, 16, 9, tzinfo=timezone.utc)
    assert rows[0].bars[0].duration_minutes == 60


def test_gantt_bars_are_sorted_by_start_time_within_resource():
    result = SchedulingResult(
        backend_id="baseline-finite",
        status="Feasible",
        message="ok",
        assignments=[
            OperationAssignment(
                operation_id="OP-LATE",
                order_id="WO-2",
                resource_id="WC-DRUM",
                start=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
                end=datetime(2026, 6, 16, 11, tzinfo=timezone.utc),
            ),
            OperationAssignment(
                operation_id="OP-EARLY",
                order_id="WO-1",
                resource_id="WC-DRUM",
                start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
                end=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
            ),
        ],
    )

    rows = build_gantt_rows(result)

    assert [bar.operation_id for bar in rows[0].bars] == ["OP-EARLY", "OP-LATE"]
