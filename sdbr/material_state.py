from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sdbr.release_candidates import MaterialAvailability, WipLimit


@dataclass(frozen=True, slots=True)
class MaterialAvailabilityImportRow:
    item_id: str
    location_id: str
    allocated_qty: float = 0.0
    inbound_qty: float = 0.0
    inbound_available_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WipLimitImportRow:
    scope_id: str
    current_wip_count: int
    max_wip_count: int
    order_wip_increment: int = 1


def import_material_availability_from_rows(
    rows: list[MaterialAvailabilityImportRow],
) -> list[MaterialAvailability]:
    for row in rows:
        if row.allocated_qty < 0:
            raise ValueError(
                f"Material availability {row.item_id} at {row.location_id} has negative allocated quantity."
            )
        if row.inbound_qty < 0:
            raise ValueError(
                f"Material availability {row.item_id} at {row.location_id} has negative inbound quantity."
            )
    return [
        MaterialAvailability(
            item_id=row.item_id,
            location_id=row.location_id,
            allocated_qty=row.allocated_qty,
            inbound_qty=row.inbound_qty,
            inbound_available_at=row.inbound_available_at,
        )
        for row in sorted(rows, key=lambda item: (item.item_id, item.location_id))
    ]


def import_wip_limits_from_rows(rows: list[WipLimitImportRow]) -> list[WipLimit]:
    for row in rows:
        if row.current_wip_count < 0:
            raise ValueError(f"WIP limit {row.scope_id} has negative current WIP.")
        if row.max_wip_count < 0:
            raise ValueError(f"WIP limit {row.scope_id} has negative maximum WIP.")
        if row.order_wip_increment <= 0:
            raise ValueError(f"WIP limit {row.scope_id} must have positive order WIP increment.")
        if row.current_wip_count > row.max_wip_count:
            raise ValueError(f"WIP limit {row.scope_id} has current WIP above maximum WIP.")
    return [
        WipLimit(
            scope_id=row.scope_id,
            current_wip_count=row.current_wip_count,
            max_wip_count=row.max_wip_count,
            order_wip_increment=row.order_wip_increment,
        )
        for row in sorted(rows, key=lambda item: item.scope_id)
    ]
