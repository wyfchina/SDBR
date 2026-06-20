from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sdbr.planner_workbench import Resource


@dataclass(frozen=True, slots=True)
class ResourceCapacityImportRow:
    resource_id: str
    name: str
    is_constraint: bool
    capacity_date: date
    capacity_minutes: int


def import_resources_from_capacity_rows(rows: list[ResourceCapacityImportRow]) -> list[Resource]:
    grouped: dict[tuple[str, str, bool], dict[date, int]] = {}
    for row in rows:
        grouped.setdefault(
            (row.resource_id, row.name, row.is_constraint),
            {},
        )[row.capacity_date] = row.capacity_minutes

    return [
        Resource(
            resource_id=resource_id,
            name=name,
            is_constraint=is_constraint,
            daily_capacity_minutes=dict(sorted(capacity_by_date.items())),
        )
        for (resource_id, name, is_constraint), capacity_by_date in sorted(grouped.items())
    ]
