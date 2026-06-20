from __future__ import annotations

from dataclasses import dataclass

from sdbr.planner_view import InventoryBufferPolicy


@dataclass(frozen=True, slots=True)
class InventoryBufferImportRow:
    item_id: str
    location_id: str
    on_hand_qty: float
    red_zone_qty: float
    yellow_zone_qty: float
    green_zone_qty: float


def import_inventory_buffers_from_rows(
    rows: list[InventoryBufferImportRow],
) -> list[InventoryBufferPolicy]:
    return [
        InventoryBufferPolicy(
            item_id=row.item_id,
            location_id=row.location_id,
            on_hand_qty=row.on_hand_qty,
            red_zone_qty=row.red_zone_qty,
            yellow_zone_qty=row.yellow_zone_qty,
            green_zone_qty=row.green_zone_qty,
        )
        for row in sorted(rows, key=lambda item: (item.item_id, item.location_id))
    ]
