from datetime import datetime, timedelta, timezone

import pytest

from sdbr.ccr_shadow_scheduler import (
    _extract_route_operations,
    _validate_shadow_request,
    _window_metrics,
)
from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.scheduling_solver import SetupTransition


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

    def test_route_order_repeated_ccr_and_formal_duration(self):
        resource = Resource(
            "CCR-1", "CCR", True, {}, capacity_units=1,
            efficiency_percent=80,
        )
        routing = Routing(
            product_id="FG-1",
            operations=[
                Operation("CCR-B", "CCR-1", 7, 30),
                Operation("NCR", "NCR-1", 5, 20),
                Operation("CCR-A", "CCR-1", 11, 10),
            ],
        )
        non_constraint = Resource("NCR-1", "NCR", False, {})

        all_operations, ccr_operations, issues = _extract_route_operations(
            order_id="SO-1:10",
            quantity=1.5,
            routing=routing,
            resources=[resource, non_constraint],
            setup_transitions=[],
        )

        assert issues == []
        assert [row["SourceOperationID"] for row in all_operations] == [
            "CCR-A", "NCR", "CCR-B"
        ]
        assert [row["OperationID"] for row in ccr_operations] == [
            "SO-1:10:CCR-A", "SO-1:10:CCR-B"
        ]
        assert ccr_operations[0]["DurationMinutes"] == 20

    def test_to_family_setup_and_missing_route_resource_or_ccr_fail_closed(self):
        ccr = Resource("CCR-1", "CCR", True, {}, efficiency_percent=100)
        routing = Routing(
            product_id="FG-1",
            operations=[Operation("CUT", "CCR-1", 10, 10, setup_family="F2")],
        )
        transition = SetupTransition("CCR-1", "F1", "F2", 15)

        _, _, setup_issues = _extract_route_operations(
            order_id="SO-1:10",
            quantity=1.0,
            routing=routing,
            resources=[ccr],
            setup_transitions=[transition],
        )
        assert [row["Code"] for row in setup_issues] == [
            "CCR_SETUP_LOAD_REQUIRES_REVIEW"
        ]

        for broken_routing, resources, code in [
            (None, [ccr], "ROUTING_NOT_FOUND"),
            (routing, [], "RESOURCE_NOT_FOUND"),
            (
                Routing("FG-1", [Operation("PACK", "NCR-1", 10, 10)]),
                [Resource("NCR-1", "NCR", False, {})],
                "CCR_OPERATION_NOT_FOUND",
            ),
        ]:
            _, _, issues = _extract_route_operations(
                order_id="SO-1:10",
                quantity=1.0,
                routing=broken_routing,
                resources=resources,
                setup_transitions=[],
            )
            assert [row["Code"] for row in issues] == [code]


class TestCcrShadowCapacityParity:
    """BE-SDBR-008, BE-SDBR-010: mirror formal solver capacity semantics."""

    @staticmethod
    def _state(*, units=1, capacity=480, scheduled=(), reserved=0):
        return {
            "ResourceID": "CCR-1",
            "WindowStart": datetime(2026, 7, 20, 8, tzinfo=UTC),
            "WindowEnd": datetime(2026, 7, 20, 16, tzinfo=UTC),
            "CapacityMinutes": capacity,
            "CapacityUnits": units,
            "ProcessingIntervals": list(scheduled),
            "ScheduledFullMinutes": sum(
                int((end - start).total_seconds() // 60)
                for start, end in scheduled
            ),
            "ExistingReservationMinutes": reserved,
            "CandidateAssignments": [],
        }

    def test_capacity_units_never_multiply_formal_bucket_total(self):
        state = self._state(units=2, reserved=450)
        metrics = _window_metrics(
            state,
            usable_start=state["WindowStart"],
            deadline=state["WindowEnd"],
            candidate_minutes=60,
        )
        assert metrics["AggregateRemainingMinutes"] == 30
        assert metrics["Fits"] is False

    def test_deadline_truncates_temporal_but_not_aggregate_load(self):
        start = datetime(2026, 7, 20, 8, tzinfo=UTC)
        state = self._state(
            scheduled=[(start, start + timedelta(minutes=180))]
        )
        metrics = _window_metrics(
            state,
            usable_start=start,
            deadline=datetime(2026, 7, 20, 12, tzinfo=UTC),
            candidate_minutes=120,
        )
        assert metrics["UsableTemporalCapacityMinutes"] == 240
        assert metrics["TemporalRemainingMinutes"] == 60
        assert metrics["Fits"] is False

        after_deadline = self._state(
            scheduled=[
                (
                    datetime(2026, 7, 20, 13, tzinfo=UTC),
                    datetime(2026, 7, 20, 16, tzinfo=UTC),
                )
            ]
        )
        aggregate = _window_metrics(
            after_deadline,
            usable_start=start,
            deadline=datetime(2026, 7, 20, 12, tzinfo=UTC),
            candidate_minutes=360,
        )
        assert aggregate["ScheduledLoadBeforeDeadlineMinutes"] == 0
        assert aggregate["AggregateRemainingMinutes"] == 300
        assert aggregate["Fits"] is False
