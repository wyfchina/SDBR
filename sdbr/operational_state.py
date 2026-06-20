from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_candidates import MaterialAvailability, WipLimit


@dataclass(frozen=True, slots=True)
class OperationalStateSnapshot:
    snapshot_id: str
    captured_at: datetime
    inventory_buffers: list[InventoryBufferPolicy]
    material_availability: list[MaterialAvailability]
    wip_limits: list[WipLimit]


@dataclass(frozen=True, slots=True)
class OperationalStateFreshness:
    status: Literal["Fresh", "Stale", "Future"]
    age_minutes: float
    max_age_minutes: int
    acceptable: bool


def create_operational_state_snapshot(
    *,
    snapshot_id: str,
    captured_at: datetime,
    inventory_buffers: list[InventoryBufferPolicy],
    material_availability: list[MaterialAvailability],
    wip_limits: list[WipLimit],
) -> OperationalStateSnapshot:
    normalized_id = snapshot_id.strip()
    if not normalized_id:
        raise ValueError("Operational state snapshot ID is required.")
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("Operational state snapshot time must be timezone-aware.")

    buffer_keys = [(item.item_id, item.location_id) for item in inventory_buffers]
    if len(buffer_keys) != len(set(buffer_keys)):
        raise ValueError("Operational state snapshot contains duplicate inventory buffers.")
    availability_keys = [
        (item.item_id, item.location_id)
        for item in material_availability
    ]
    if len(availability_keys) != len(set(availability_keys)):
        raise ValueError("Operational state snapshot contains duplicate material availability.")
    scope_ids = [item.scope_id for item in wip_limits]
    if len(scope_ids) != len(set(scope_ids)):
        raise ValueError("Operational state snapshot contains duplicate WIP scopes.")

    return OperationalStateSnapshot(
        snapshot_id=normalized_id,
        captured_at=captured_at,
        inventory_buffers=sorted(
            inventory_buffers,
            key=lambda item: (item.item_id, item.location_id),
        ),
        material_availability=sorted(
            material_availability,
            key=lambda item: (item.item_id, item.location_id),
        ),
        wip_limits=sorted(wip_limits, key=lambda item: item.scope_id),
    )


def evaluate_operational_state_freshness(
    *,
    snapshot: OperationalStateSnapshot,
    evaluated_at: datetime,
    max_age_minutes: int,
) -> OperationalStateFreshness:
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("Operational state evaluation time must be timezone-aware.")
    if max_age_minutes <= 0:
        raise ValueError("Operational state maximum age must be positive.")

    age_minutes = (evaluated_at - snapshot.captured_at).total_seconds() / 60
    if age_minutes < 0:
        status: Literal["Fresh", "Stale", "Future"] = "Future"
    elif age_minutes > max_age_minutes:
        status = "Stale"
    else:
        status = "Fresh"
    return OperationalStateFreshness(
        status=status,
        age_minutes=age_minutes,
        max_age_minutes=max_age_minutes,
        acceptable=status == "Fresh",
    )
