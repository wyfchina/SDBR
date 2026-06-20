from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sdbr.scheduling_solver import SchedulingResult


@dataclass(frozen=True, slots=True)
class GanttBar:
    operation_id: str
    order_id: str
    start: datetime
    end: datetime
    duration_minutes: int


@dataclass(frozen=True, slots=True)
class GanttRow:
    resource_id: str
    bars: list[GanttBar]


def build_gantt_rows(result: SchedulingResult) -> list[GanttRow]:
    bars_by_resource: dict[str, list[GanttBar]] = {}
    for assignment in result.assignments:
        bars_by_resource.setdefault(assignment.resource_id, []).append(
            GanttBar(
                operation_id=assignment.operation_id,
                order_id=assignment.order_id,
                start=assignment.start,
                end=assignment.end,
                duration_minutes=int((assignment.end - assignment.start).total_seconds() / 60),
            )
        )

    return [
        GanttRow(
            resource_id=resource_id,
            bars=sorted(bars, key=lambda item: (item.start, item.end, item.operation_id)),
        )
        for resource_id, bars in sorted(bars_by_resource.items())
    ]
