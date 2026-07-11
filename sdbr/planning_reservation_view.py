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
    for reservation in _deduplicated_ledger_rows(
        reservations, "CapacityReservationID"
    ):
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
            bucket["MtaReservationMinutes"] = _checked_finite_sum(
                bucket["MtaReservationMinutes"],
                reserved_minutes,
                "MtaReservationMinutes",
            )
        else:
            bucket["MtoReservationMinutes"] = _checked_finite_sum(
                bucket["MtoReservationMinutes"],
                reserved_minutes,
                "MtoReservationMinutes",
            )
        bucket["ReservationLoadMinutes"] = _checked_finite_sum(
            bucket["ReservationLoadMinutes"],
            reserved_minutes,
            "ReservationLoadMinutes",
        )
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
    for allocation in _deduplicated_ledger_rows(
        allocations, "MaterialAllocationID"
    ):
        if not _is_active_planning_status(allocation):
            continue
        if str(allocation.get("ItemID")) != item_id:
            continue
        if str(allocation.get("LocationID")) != location_id:
            continue
        if str(allocation.get("DemandCommitmentID")) == current_demand_commitment_id:
            continue
        allocated_qty = _checked_finite_sum(
            allocated_qty,
            _finite_non_negative(allocation.get("AllocatedQty"), "AllocatedQty"),
            "AllocatedQty",
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


def _deduplicated_ledger_rows(
    records: list[dict[str, object]], record_id_field: str
) -> tuple[dict[str, object], ...]:
    """Return one canonical ledger row per required identifier."""
    records_by_id: dict[str, tuple[tuple[tuple[str, object], ...], dict[str, object]]] = {}
    for record in records:
        record_id = _required_ledger_id(record.get(record_id_field), record_id_field)
        canonical_content = tuple(sorted(record.items()))
        existing = records_by_id.get(record_id)
        if existing is None:
            records_by_id[record_id] = (canonical_content, record)
        elif existing[0] != canonical_content:
            raise ValueError(
                f"{record_id_field} has duplicate rows with different content."
            )
    return tuple(record for _, record in records_by_id.values())


def _required_ledger_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required.")
    return value


def _parse_window_start_at(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("WindowStartAt must be an ISO datetime string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("WindowStartAt must be an ISO datetime string.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("WindowStartAt must be timezone-aware.")
    return parsed


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


def _checked_finite_sum(
    left: int | float,
    right: int | float,
    field: str,
) -> int | float:
    try:
        total = left + right
        is_total_finite = isfinite(float(total))
    except OverflowError as error:
        raise ValueError(f"{field} aggregate overflow.") from error
    if not is_total_finite:
        raise ValueError(f"{field} aggregate overflow.")
    return total


def _demand_class(record: dict[str, object]) -> str:
    value = record.get("DemandClass")
    if not isinstance(value, str) or value.upper() not in {"MTO", "MTA"}:
        raise ValueError("DemandClass must be MTO or MTA.")
    return value.upper()
