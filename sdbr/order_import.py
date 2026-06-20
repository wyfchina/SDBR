from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sdbr.planner_workbench import SchedulingOrder


@dataclass(frozen=True, slots=True)
class OrderImportRow:
    order_id: str
    product_id: str
    quantity: float
    due_date: datetime
    target_start_date: date


def import_orders_from_rows(rows: list[OrderImportRow]) -> list[SchedulingOrder]:
    return [
        SchedulingOrder(
            order_id=row.order_id,
            product_id=row.product_id,
            quantity=row.quantity,
            due_date=row.due_date,
            target_start_date=row.target_start_date,
        )
        for row in sorted(rows, key=lambda item: (item.target_start_date, item.order_id))
    ]
