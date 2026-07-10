"""Acceptance evidence for BE-SDBR-007, BE-SDBR-008, and BE-SDBR-009."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from sdbr.planning_commitments import (
    DemandCommitmentConflict,
    create_demand_commitment,
)
from sdbr.planning_reservations import (
    ReservationConflict,
    apply_reservation_write_set,
    prepare_reservation_confirmation,
)


def _demand(*, version: str = "1") -> dict[str, object]:
    return create_demand_commitment(
        demand_source_type="MTAReplenishment",
        source_system="SDBR",
        source_object_type="ReplenishmentRecommendation",
        source_object_id="REC-1",
        source_object_version=version,
        demand_line_id="1",
        item_or_product_id="FG-1",
        location_id="MAIN",
        quantity=10,
        uom="EA",
        required_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
        demand_class="MTA",
        trace_id="TRACE-REC-1",
    )


def _prepare(**overrides: object):
    arguments: dict[str, object] = {
        "demand_commitment": _demand(),
        "existing_commitments": {},
        "confirmation_id": "CONFIRM-1",
        "confirmed_by": "planner-1",
        "confirmed_at": datetime(2026, 7, 10, 8, tzinfo=timezone.utc),
        "capacity_requests": [],
        "material_requests": [],
    }
    arguments.update(overrides)
    return prepare_reservation_confirmation(**arguments)  # type: ignore[arg-type]


def _apply(write_set: object, collections: tuple[dict, dict, dict, dict, list, set]):
    apply_reservation_write_set(
        write_set=write_set,  # type: ignore[arg-type]
        commitments=collections[0],
        batches=collections[1],
        capacity_reservations=collections[2],
        material_allocations=collections[3],
        events=collections[4],
        processed_event_keys=collections[5],
    )


def test_prepare_and_apply_confirmation_writes_batch_capacity_material_and_event():
    write_set = _prepare(
        capacity_requests=[{
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "WindowEndAt": "2026-07-20T16:00:00+00:00",
            "ReservedMinutes": 120,
            "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
        }],
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "Uom": "EA",
            "AllocatedQty": 20,
            "SupplySourceType": "OnHand",
            "MaterialSnapshotID": "OPS-1",
        }],
    )
    collections = ({}, {}, {}, {}, [], set())

    _apply(write_set, collections)

    assert len(collections[0]) == len(collections[1]) == 1
    assert len(collections[2]) == len(collections[3]) == 1
    assert collections[4][0]["EventType"] == "PlanningReservationActivated"
    assert write_set.idempotency_key in collections[5]


def test_duplicate_confirmation_does_not_create_second_batch():
    write_set = _prepare()
    collections = ({}, {}, {}, {}, [], set())

    _apply(write_set, collections)
    _apply(write_set, collections)

    assert len(collections[1]) == 1
    assert len(collections[4]) == 1


def test_invalid_capacity_request_builds_no_partial_write_set():
    with pytest.raises(ReservationConflict, match="positive reserved minutes"):
        _prepare(
            capacity_requests=[{
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "WindowEndAt": "2026-07-20T16:00:00+00:00",
                "ReservedMinutes": 0,
            }]
        )


def test_request_control_fields_cannot_override_generated_reservation_values():
    demand = _demand()
    write_set = _prepare(
        demand_commitment=demand,
        capacity_requests=[{
            "CapacityReservationID": "CALLER-CAPACITY-ID",
            "ReservationBatchID": "CALLER-BATCH-ID",
            "DemandCommitmentID": "CALLER-DEMAND-ID",
            "DemandClass": "CALLER-CLASS",
            "Status": "CallerStatus",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "WindowEndAt": "2026-07-20T16:00:00+00:00",
            "ReservedMinutes": 120,
        }],
        material_requests=[{
            "MaterialAllocationID": "CALLER-MATERIAL-ID",
            "ReservationBatchID": "CALLER-BATCH-ID",
            "DemandCommitmentID": "CALLER-DEMAND-ID",
            "DemandClass": "CALLER-CLASS",
            "Status": "CallerStatus",
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 20,
        }],
    )

    capacity = write_set.capacity_reservations[0]
    material = write_set.material_allocations[0]
    assert capacity["CapacityReservationID"] != "CALLER-CAPACITY-ID"
    assert material["MaterialAllocationID"] != "CALLER-MATERIAL-ID"
    for record in (capacity, material):
        assert record["ReservationBatchID"] == write_set.batch["ReservationBatchID"]
        assert record["DemandCommitmentID"] == demand["DemandCommitmentID"]
        assert record["DemandClass"] == demand["DemandClass"]
        assert record["Status"] == "ActivePlanReservation"


def test_prepare_rejects_active_predecessor_through_commitment_guard():
    predecessor = {**_demand(version="1"), "Status": "Active"}

    with pytest.raises(DemandCommitmentConflict, match="active predecessor"):
        _prepare(
            demand_commitment=_demand(version="2"),
            existing_commitments={str(predecessor["DemandCommitmentID"]): predecessor},
        )


def test_write_set_is_immutable():
    write_set = _prepare()

    with pytest.raises(FrozenInstanceError):
        write_set.idempotency_key = "different"  # type: ignore[misc]


def test_conflicting_target_preflight_leaves_all_collections_unchanged():
    write_set = _prepare()
    conflicting_batch = {**write_set.batch, "Status": "Cancelled"}
    collections = ({}, {str(write_set.batch["ReservationBatchID"]): conflicting_batch}, {}, {}, [], set())
    before = ({}, dict(collections[1]), {}, {}, [], set())

    with pytest.raises(ReservationConflict, match="different content"):
        _apply(write_set, collections)

    assert collections == before
