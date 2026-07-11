from datetime import datetime, timezone

import pytest

from sdbr.ccr_shadow_scheduler import _validate_shadow_request


UTC = timezone.utc


class TestCcrShadowInputContract:
    """BE-SDBR-008, BE-SDBR-010: validate MTO CCR shadow inputs."""

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"order_id": " "}, "order_id"),
            ({"quantity": True}, "quantity"),
            ({"quantity": float("inf")}, "quantity"),
            ({"requested_due_at": datetime(2026, 7, 20, 8)}, "timezone-aware"),
            ({"evaluated_at": datetime(2026, 7, 11, 8)}, "timezone-aware"),
            ({"downstream_protection_minutes": -1}, "non-negative"),
            ({"protection_threshold_percent": 0.0}, "threshold"),
            ({"protection_threshold_percent": 100.1}, "threshold"),
        ],
    )
    def test_rejects_invalid_public_inputs(self, overrides, message):
        values = {
            "order_id": "SO-1:10",
            "quantity": 1.0,
            "requested_due_at": datetime(2026, 7, 20, 18, tzinfo=UTC),
            "evaluated_at": datetime(2026, 7, 11, 8, tzinfo=UTC),
            "downstream_protection_minutes": 60,
            "protection_threshold_percent": 80.0,
        }
        values.update(overrides)
        with pytest.raises(ValueError, match=message):
            _validate_shadow_request(**values)
