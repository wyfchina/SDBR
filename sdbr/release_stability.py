from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReleaseStabilityPolicy:
    tolerance_minutes: int = 30
    replan_threshold_minutes: int = 120
    consecutive_blocked_threshold: int = 3
    replan_cooldown_minutes: int = 60

    def __post_init__(self) -> None:
        if self.tolerance_minutes < 0:
            raise ValueError("tolerance_minutes must be non-negative")
        if self.replan_threshold_minutes < self.tolerance_minutes:
            raise ValueError(
                "replan_threshold_minutes must be at least tolerance_minutes"
            )
        if self.consecutive_blocked_threshold < 1:
            raise ValueError("consecutive_blocked_threshold must be at least 1")
        if self.replan_cooldown_minutes < 0:
            raise ValueError("replan_cooldown_minutes must be non-negative")


@dataclass(frozen=True, slots=True)
class ReleaseStabilityInput:
    order_id: str
    planned_release_at: datetime
    evaluated_release_at: datetime
    gate_allowed: bool
    consecutive_blocked_count: int = 0
    last_replan_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.consecutive_blocked_count < 0:
            raise ValueError("consecutive_blocked_count must be non-negative")


@dataclass(frozen=True, slots=True)
class ReleaseStabilityResult:
    order_id: str
    deviation_minutes: int
    absolute_deviation_minutes: int
    timing_status: str
    severity: str
    action: str
    replan_required: bool
    reason_code: str


def evaluate_release_stability(
    release_input: ReleaseStabilityInput,
    policy: ReleaseStabilityPolicy | None = None,
) -> ReleaseStabilityResult:
    active_policy = policy or ReleaseStabilityPolicy()
    datetimes = [
        release_input.planned_release_at,
        release_input.evaluated_release_at,
    ]
    if release_input.last_replan_at is not None:
        datetimes.append(release_input.last_replan_at)
    awareness = {_is_timezone_aware(value) for value in datetimes}
    if len(awareness) > 1:
        raise ValueError(
            "release stability datetimes must use consistent timezone awareness"
        )
    deviation_minutes = int(
        (
            release_input.evaluated_release_at
            - release_input.planned_release_at
        ).total_seconds()
        / 60
    )
    absolute_deviation = abs(deviation_minutes)
    if deviation_minutes < 0:
        timing_status = "Early"
    elif deviation_minutes > 0:
        timing_status = "Late"
    else:
        timing_status = "OnTime"

    threshold_triggered = (
        absolute_deviation >= active_policy.replan_threshold_minutes
    )
    repeated_blocking = (
        not release_input.gate_allowed
        and release_input.consecutive_blocked_count
        >= active_policy.consecutive_blocked_threshold
    )
    if threshold_triggered or repeated_blocking:
        cooldown_active = False
        if release_input.last_replan_at is not None:
            elapsed_since_replan = int(
                (
                    release_input.evaluated_release_at
                    - release_input.last_replan_at
                ).total_seconds()
                / 60
            )
            cooldown_active = (
                elapsed_since_replan < active_policy.replan_cooldown_minutes
            )
        if cooldown_active:
            return ReleaseStabilityResult(
                order_id=release_input.order_id,
                deviation_minutes=deviation_minutes,
                absolute_deviation_minutes=absolute_deviation,
                timing_status=timing_status,
                severity="Warning",
                action="Review",
                replan_required=False,
                reason_code="ReplanCooldownActive",
            )
        return ReleaseStabilityResult(
            order_id=release_input.order_id,
            deviation_minutes=deviation_minutes,
            absolute_deviation_minutes=absolute_deviation,
            timing_status=timing_status,
            severity="Critical",
            action="Replan",
            replan_required=True,
            reason_code=(
                "DeviationAtReplanThreshold"
                if threshold_triggered
                else "ConsecutiveGateBlocks"
            ),
        )

    inside_tolerance = absolute_deviation <= active_policy.tolerance_minutes
    return ReleaseStabilityResult(
        order_id=release_input.order_id,
        deviation_minutes=deviation_minutes,
        absolute_deviation_minutes=absolute_deviation,
        timing_status=timing_status,
        severity="Normal" if inside_tolerance else "Warning",
        action="Monitor" if inside_tolerance else "Review",
        replan_required=False,
        reason_code=(
            "WithinTolerance" if inside_tolerance else "DeviationAboveTolerance"
        ),
    )


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
