from __future__ import annotations

from dataclasses import dataclass

from sdbr.planner_workbench import Operation, Routing


@dataclass(frozen=True, slots=True)
class RoutingImportRow:
    product_id: str
    routing_id: str
    is_primary: bool
    operation_id: str
    resource_id: str
    duration_minutes: int
    sequence: int
    alternate_resource_ids: list[str] | None = None


def import_routings_from_operation_rows(rows: list[RoutingImportRow]) -> list[Routing]:
    grouped: dict[tuple[str, str, bool], list[Operation]] = {}
    for row in rows:
        grouped.setdefault(
            (row.product_id, row.routing_id, row.is_primary),
            [],
        ).append(
            Operation(
                operation_id=row.operation_id,
                resource_id=row.resource_id,
                duration_minutes=row.duration_minutes,
                sequence=row.sequence,
                alternate_resource_ids=row.alternate_resource_ids or [],
            )
        )

    return [
        Routing(
            product_id=product_id,
            routing_id=routing_id,
            is_primary=is_primary,
            operations=sorted(operations, key=lambda operation: operation.sequence),
        )
        for (product_id, routing_id, is_primary), operations in sorted(grouped.items())
    ]
