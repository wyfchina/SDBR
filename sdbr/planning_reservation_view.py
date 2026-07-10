"""Pure read projections for shared planning reservations."""

from datetime import datetime
from math import isfinite
from numbers import Real


ACTIVE_PLANNING_STATUSES = frozenset({
    "ActivePlanReservation",
    "LinkedToFormalOrder",
    "HeldForPlanningError",
})


def reservation_load_by_bucket(
    reservations: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    """Group active shared CCR reservations by resource and calendar day."""
    buckets: dict[tuple[str, str], dict[str, object]] = {}
    for reservation in reservations:
        if not _is_active_planning_status(reservation):
            continue
        reserved_minutes = _finite_non_negative(
            reservation.get("ReservedMinutes"), "ReservedMinutes"
        )
        window_start_at = _parse_window_start_at(reservation.get("WindowStartAt"))
        key = (str(reservation.get("ResourceID")), window_start_at.date().isoformat())
        bucket = buckets.setdefault(
            key,
            {
                "MtoReservationMinutes": 0,
                "MtaReservationMinutes": 0,
                "ReservationLoadMinutes": 0,
            },
        )
        if _demand_class(reservation) == "MTA":
            bucket["MtaReservationMinutes"] += reserved_minutes
        else:
            bucket["MtoReservationMinutes"] += reserved_minutes
        bucket["ReservationLoadMinutes"] += reserved_minutes
    return buckets


def planning_allocated_qty_for_other_demands(
    *,
    allocations: list[dict[str, object]],
    item_id: str,
    location_id: str,
    current_demand_commitment_id: str,
) -> float:
    """Return active plan allocations for a material other than this demand."""
    allocated_qty = 0
    for allocation in allocations:
        if not _is_active_planning_status(allocation):
            continue
        if str(allocation.get("ItemID")) != item_id:
            continue
        if str(allocation.get("LocationID")) != location_id:
            continue
        if str(allocation.get("DemandCommitmentID")) == current_demand_commitment_id:
            continue
        allocated_qty += _finite_non_negative(
            allocation.get("AllocatedQty"), "AllocatedQty"
        )
    return allocated_qty


def uncommitted_supply_qty(
    *,
    qualified_supply_qty: Real,
    authority_allocated_qty: Real,
    allocations: list[dict[str, object]],
    item_id: str,
    location_id: str,
    current_demand_commitment_id: str,
) -> float:
    """Return supply after authority and other active planning allocations."""
    qualified_supply = _finite_non_negative(
        qualified_supply_qty, "qualified_supply_qty"
    )
    authority_allocated = _finite_non_negative(
        authority_allocated_qty, "authority_allocated_qty"
    )
    planning_allocated = planning_allocated_qty_for_other_demands(
        allocations=allocations,
        item_id=item_id,
        location_id=location_id,
        current_demand_commitment_id=current_demand_commitment_id,
    )
    return max(qualified_supply - authority_allocated - planning_allocated, 0)


def _is_active_planning_status(record: dict[str, object]) -> bool:
    return record.get("Status") in ACTIVE_PLANNING_STATUSES


def _parse_window_start_at(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("WindowStartAt must be an ISO datetime string.")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("WindowStartAt must be an ISO datetime string.") from error


def _finite_non_negative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite non-negative number.")
    try:
        normalized_value = float(value)
    except OverflowError as error:
        raise ValueError(f"{field} must be a finite non-negative number.") from error
    if not isfinite(normalized_value) or normalized_value < 0:
        raise ValueError(f"{field} must be a finite non-negative number.")
    return normalized_value


def _demand_class(record: dict[str, object]) -> str:
    value = str(record.get("DemandClass") or record.get("DemandType") or "MTO")
    return "MTA" if value.upper() in {"MTA", "MTS", "STOCKREPLENISHMENT"} else "MTO"
