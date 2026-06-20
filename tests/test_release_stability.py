from datetime import datetime, timezone

import pytest

from sdbr.release_stability import (
    ReleaseStabilityInput,
    ReleaseStabilityPolicy,
    evaluate_release_stability,
)


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 19, hour, minute, tzinfo=timezone.utc)


def test_release_deviation_inside_tolerance_is_monitored():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=_utc(8),
            evaluated_release_at=_utc(8, 20),
            gate_allowed=True,
        )
    )

    assert result.deviation_minutes == 20
    assert result.absolute_deviation_minutes == 20
    assert result.timing_status == "Late"
    assert result.severity == "Normal"
    assert result.action == "Monitor"
    assert result.replan_required is False
    assert result.reason_code == "WithinTolerance"


def test_release_deviation_above_tolerance_requires_review():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=_utc(8),
            evaluated_release_at=_utc(9),
            gate_allowed=True,
        )
    )

    assert result.deviation_minutes == 60
    assert result.timing_status == "Late"
    assert result.severity == "Warning"
    assert result.action == "Review"
    assert result.replan_required is False
    assert result.reason_code == "DeviationAboveTolerance"


def test_large_release_delay_triggers_replan():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=_utc(8),
            evaluated_release_at=_utc(10),
            gate_allowed=True,
        )
    )

    assert result.severity == "Critical"
    assert result.action == "Replan"
    assert result.replan_required is True
    assert result.reason_code == "DeviationAtReplanThreshold"


def test_repeated_gate_blocks_trigger_replan_inside_deviation_tolerance():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=_utc(8),
            evaluated_release_at=_utc(8, 20),
            gate_allowed=False,
            consecutive_blocked_count=3,
        )
    )

    assert result.action == "Replan"
    assert result.replan_required is True
    assert result.reason_code == "ConsecutiveGateBlocks"


def test_replan_cooldown_suppresses_another_replan():
    result = evaluate_release_stability(
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=_utc(8),
            evaluated_release_at=_utc(10),
            gate_allowed=True,
            last_replan_at=_utc(9, 30),
        )
    )

    assert result.severity == "Warning"
    assert result.action == "Review"
    assert result.replan_required is False
    assert result.reason_code == "ReplanCooldownActive"


@pytest.mark.parametrize(
    ("policy_kwargs", "message"),
    [
        ({"tolerance_minutes": -1}, "tolerance_minutes must be non-negative"),
        (
            {"tolerance_minutes": 60, "replan_threshold_minutes": 30},
            "replan_threshold_minutes must be at least tolerance_minutes",
        ),
        (
            {"consecutive_blocked_threshold": 0},
            "consecutive_blocked_threshold must be at least 1",
        ),
        (
            {"replan_cooldown_minutes": -1},
            "replan_cooldown_minutes must be non-negative",
        ),
    ],
)
def test_release_stability_policy_rejects_invalid_thresholds(
    policy_kwargs: dict[str, int],
    message: str,
):
    with pytest.raises(ValueError, match=message):
        ReleaseStabilityPolicy(**policy_kwargs)


def test_release_stability_input_rejects_negative_blocked_count():
    with pytest.raises(
        ValueError,
        match="consecutive_blocked_count must be non-negative",
    ):
        ReleaseStabilityInput(
            order_id="WO-1",
            planned_release_at=_utc(8),
            evaluated_release_at=_utc(8),
            gate_allowed=False,
            consecutive_blocked_count=-1,
        )


def test_release_stability_rejects_mixed_timezone_awareness():
    release_input = ReleaseStabilityInput(
        order_id="WO-1",
        planned_release_at=datetime(2026, 6, 19, 8),
        evaluated_release_at=_utc(8),
        gate_allowed=True,
    )

    with pytest.raises(
        ValueError,
        match="release stability datetimes must use consistent timezone awareness",
    ):
        evaluate_release_stability(release_input)
