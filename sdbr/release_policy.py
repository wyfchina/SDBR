from __future__ import annotations

from dataclasses import dataclass

from sdbr.release_stability import ReleaseStabilityPolicy


@dataclass(frozen=True, slots=True)
class ReleasePolicySettings:
    version_id: str | None
    rope_buffer_minutes: int | None
    green_zone_ratio: float
    yellow_zone_ratio: float
    red_zone_ratio: float
    max_wip_count: int | None
    material_lookahead_minutes: int
    stability_policy: ReleaseStabilityPolicy


def release_policy_settings(
    policy: dict[str, object] | None,
) -> ReleasePolicySettings:
    ratios = _dict(policy.get("TimeBufferRatios")) if policy else {}
    stability = _dict(policy.get("StabilityPolicy")) if policy else {}
    tolerance = _int(stability.get("ToleranceMinutes"), 30)
    replan_threshold = _int(
        stability.get("ReplanThresholdMinutes"),
        max(120, tolerance),
    )
    return ReleasePolicySettings(
        version_id=(str(policy.get("VersionID")) if policy else None),
        rope_buffer_minutes=(
            _int(policy.get("RopeBufferMinutes"), 0) if policy else None
        ),
        green_zone_ratio=_float(ratios.get("Green"), 0.33),
        yellow_zone_ratio=_float(ratios.get("Yellow"), 0.34),
        red_zone_ratio=_float(ratios.get("Red"), 0.33),
        max_wip_count=(
            _int(policy.get("MaxWipCount"), 0)
            if policy and policy.get("MaxWipCount") is not None
            else None
        ),
        material_lookahead_minutes=(
            _int(
                policy.get("MaterialCheckWindowMinutes")
                if policy and policy.get("MaterialCheckWindowMinutes") is not None
                else policy.get("MaterialLookaheadMinutes"),
                0,
            )
            if policy
            else 0
        ),
        stability_policy=ReleaseStabilityPolicy(
            tolerance_minutes=tolerance,
            replan_threshold_minutes=replan_threshold,
            consecutive_blocked_threshold=_int(
                stability.get("ConsecutiveBlockedThreshold"),
                3,
            ),
            replan_cooldown_minutes=_int(
                stability.get("ReplanCooldownMinutes"),
                60,
            ),
        ),
    )


def release_policy_evidence(
    policy: dict[str, object] | None,
) -> dict[str, object]:
    settings = release_policy_settings(policy)
    return {
        "VersionID": settings.version_id,
        "RopeBufferMinutes": settings.rope_buffer_minutes,
        "TimeBufferRatios": {
            "Green": settings.green_zone_ratio,
            "Yellow": settings.yellow_zone_ratio,
            "Red": settings.red_zone_ratio,
        },
        "MaxWipCount": settings.max_wip_count,
        "MaterialLookaheadMinutes": settings.material_lookahead_minutes,
        "MaterialCheckWindowMinutes": settings.material_lookahead_minutes,
        "StabilityPolicy": {
            "ToleranceMinutes": settings.stability_policy.tolerance_minutes,
            "ReplanThresholdMinutes": settings.stability_policy.replan_threshold_minutes,
            "ConsecutiveBlockedThreshold": settings.stability_policy.consecutive_blocked_threshold,
            "ReplanCooldownMinutes": settings.stability_policy.replan_cooldown_minutes,
        },
    }


def effective_rope_buffer_minutes(
    *,
    release_policy: dict[str, object] | None,
    fallback_time_buffer_minutes: int,
) -> int:
    settings = release_policy_settings(release_policy)
    if settings.rope_buffer_minutes is None:
        return fallback_time_buffer_minutes
    return settings.rope_buffer_minutes


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
