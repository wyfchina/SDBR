from datetime import datetime, timedelta, timezone

import pytest

from sdbr.ccr_shadow_scheduler import (
    _build_window_states,
    _commit_candidate,
    _extract_route_operations,
    _reservation_request,
    _validate_shadow_request,
    _window_metrics,
)
from sdbr.planner_workbench import Operation, Resource, Routing
from sdbr.planning_commitments import create_demand_commitment
from sdbr.planning_reservations import prepare_reservation_confirmation
from sdbr.scheduling_solver import CapacityBucket, SetupTransition


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

    def test_repeated_visits_share_only_their_exact_resource_window(self):
        state = self._state()
        _commit_candidate(
            state,
            minutes=300,
            latest_allowed_completion_at=state["WindowEnd"],
        )
        second = _window_metrics(
            state,
            usable_start=state["WindowStart"],
            deadline=state["WindowEnd"],
            candidate_minutes=200,
        )
        assert second["AggregateRemainingMinutes"] == 180
        assert second["Fits"] is False

    def test_end_equal_deadline_is_accepted_by_phase0(self):
        operation = {
            "OperationID": "SO-1:10:CUT",
            "ResourceID": "CCR-1",
            "DurationMinutes": 60,
        }
        state = self._state()
        request = _reservation_request(
            order_id="SO-1:10",
            operation=operation,
            state=state,
            operation_deadline=state["WindowEnd"],
        )
        demand = create_demand_commitment(
            demand_source_type="MTOCustomerOrder",
            source_system="MockERP",
            source_object_type="CustomerOrder",
            source_object_id="SO-1",
            source_object_version="1",
            demand_line_id="10",
            item_or_product_id="FG-1",
            location_id="MAIN",
            quantity=1.0,
            uom="EA",
            required_at=state["WindowEnd"],
            demand_class="MTO",
            trace_id="TRACE-1",
        )
        write_set = prepare_reservation_confirmation(
            demand_commitment=demand,
            existing_commitments={},
            confirmation_id="DEC-1",
            confirmed_by="planner-1",
            confirmed_at=datetime(2026, 7, 11, 8, tzinfo=UTC),
            capacity_requests=[request],
            material_requests=[],
        )
        assert request["LatestAllowedCompletionAt"] == request["WindowEndAt"]
        assert len(write_set.capacity_reservations) == 1

    @staticmethod
    def _window_evidence():
        start = datetime(2026, 7, 20, 8, tzinfo=UTC)
        end = datetime(2026, 7, 20, 16, tzinfo=UTC)
        later_end = datetime(2026, 7, 20, 20, tzinfo=UTC)
        resources = [
            Resource("CCR-A", "CCR A", True, {}),
            Resource("CCR-B", "CCR B", True, {}, capacity_units=2),
        ]
        buckets = [
            CapacityBucket("CCR-A", start, end, 480),
            CapacityBucket("CCR-B", start, end, 480),
            CapacityBucket("CCR-B", end, later_end, 240),
        ]
        bars = [
            {
                "OrderID": "SO-OLD",
                "OperationID": "CUT-1",
                "BarType": "Processing",
                "Start": (start + timedelta(hours=1)).isoformat(),
                "End": (start + timedelta(hours=2)).isoformat(),
            },
            {
                "OrderID": "SO-LATER",
                "OperationID": "CUT-2",
                "BarType": "Processing",
                "Start": (end + timedelta(hours=1)).isoformat(),
                "End": (end + timedelta(hours=2)).isoformat(),
            },
        ]
        reservations = [
            {
                "CapacityReservationID": "RES-EXACT",
                "Status": "ActivePlanReservation",
                "ResourceID": "CCR-B",
                "WindowStartAt": start.isoformat(),
                "WindowEndAt": end.isoformat(),
                "LatestAllowedCompletionAt": end.isoformat(),
                "ReservedMinutes": 30,
            },
            {
                "CapacityReservationID": "RES-LATER",
                "Status": "LinkedToFormalOrder",
                "ResourceID": "CCR-B",
                "WindowStartAt": end.isoformat(),
                "WindowEndAt": later_end.isoformat(),
                "LatestAllowedCompletionAt": later_end.isoformat(),
                "ReservedMinutes": 40,
            },
            {
                "CapacityReservationID": "RES-INACTIVE",
                "Status": "Released",
                "ResourceID": "CCR-B",
                "ReservedMinutes": 999,
            },
        ]
        return start, end, later_end, resources, buckets, bars, reservations

    def test_build_window_states_scopes_evidence_to_exact_active_window(self):
        start, end, later_end, resources, buckets, bars, reservations = (
            self._window_evidence()
        )
        states = _build_window_states(
            resources=resources,
            capacity_buckets=buckets,
            ccr_resource_ids={"CCR-A", "CCR-B"},
            gantt_rows=[
                {"ResourceID": "CCR-B", "Bars": bars},
                {"ResourceID": "UNRELATED", "Bars": "malformed"},
            ],
            active_capacity_reservations=reservations,
        )

        assert states[("CCR-A", start, end)]["ScheduledFullMinutes"] == 0
        assert states[("CCR-B", start, end)]["ScheduledFullMinutes"] == 60
        assert states[("CCR-B", start, end)]["ExistingReservationMinutes"] == 30
        assert states[("CCR-B", end, later_end)]["ScheduledFullMinutes"] == 60
        assert states[("CCR-B", end, later_end)]["ExistingReservationMinutes"] == 40

    def test_build_window_states_rejects_malformed_matching_row(self):
        start, end, _, resources, buckets, _, _ = self._window_evidence()
        malformed = {
            "CapacityReservationID": "RES-BAD",
            "Status": "ActivePlanReservation",
            "ResourceID": "CCR-B",
            "WindowStartAt": start.isoformat(),
            "WindowEndAt": end.isoformat(),
            "LatestAllowedCompletionAt": start.isoformat(),
            "ReservedMinutes": 10,
        }
        with pytest.raises(ValueError, match="malformed or duplicated"):
            _build_window_states(
                resources=resources,
                capacity_buckets=buckets,
                ccr_resource_ids={"CCR-A", "CCR-B"},
                gantt_rows=[],
                active_capacity_reservations=[malformed],
            )

    @pytest.mark.parametrize("duplicate_kind", ["bucket", "bar", "reservation"])
    def test_build_window_states_rejects_duplicate_evidence(self, duplicate_kind):
        _, _, _, resources, buckets, bars, reservations = self._window_evidence()
        gantt_rows = [{"ResourceID": "CCR-B", "Bars": bars}]
        if duplicate_kind == "bucket":
            buckets.append(buckets[1])
        elif duplicate_kind == "bar":
            bars.append(dict(bars[0]))
        else:
            duplicate = dict(reservations[1])
            duplicate["CapacityReservationID"] = "RES-EXACT"
            reservations.append(duplicate)

        with pytest.raises(ValueError, match="malformed or duplicated"):
            _build_window_states(
                resources=resources,
                capacity_buckets=buckets,
                ccr_resource_ids={"CCR-A", "CCR-B"},
                gantt_rows=gantt_rows,
                active_capacity_reservations=reservations,
            )
