from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import ceil, floor, isfinite
from numbers import Real

from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.planning_reservation_view import ACTIVE_PLANNING_STATUSES
from sdbr.scheduling_solver import CapacityBucket, SetupTransition
from sdbr.sdbr_market_control import classify_ccr_load


SHADOW_ALGORITHM = {
    "Mode": "CCRFirstShadowScheduleV1",
    "Version": 1,
    "CapacitySemantics": "FormalBucketAggregateDeadlineTruncatedV1",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Shadow schedule datetimes must be timezone-aware.")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _utc(value).isoformat()


def _positive_real(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"Shadow schedule {field} must be finite and positive.")
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(f"Shadow schedule {field} must be finite and positive.")
    return normalized


def _validate_shadow_request(
    *,
    order_id: str,
    quantity: object,
    requested_due_at: datetime,
    evaluated_at: datetime,
    downstream_protection_minutes: int,
    protection_threshold_percent: float,
) -> None:
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("Shadow schedule order_id must be non-empty.")
    _positive_real(quantity, "quantity")
    _utc(requested_due_at)
    _utc(evaluated_at)
    if (
        isinstance(downstream_protection_minutes, bool)
        or not isinstance(downstream_protection_minutes, int)
        or downstream_protection_minutes < 0
    ):
        raise ValueError("Shadow schedule protection must be non-negative.")
    threshold = _positive_real(
        protection_threshold_percent,
        "protection threshold",
    )
    if threshold > 100:
        raise ValueError("Shadow schedule threshold must be in (0, 100].")


def _issue(code: str, *entity_ids: str) -> dict[str, object]:
    return {"Code": code, "EntityIDs": list(entity_ids)}
