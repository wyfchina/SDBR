"""Acceptance evidence for BE-SDBR-007, BE-SDBR-008, and BE-SDBR-009."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from sdbr.planning_commitments import (
    BUSINESS_CONTENT_FIELDS,
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


def _capacity_request(
    *,
    reservation_line_id: str = "CAP-LINE-1",
    order_id: str = "WO-1",
    operation_id: str = "WO-1:CCR",
    reserved_minutes: float = 120,
    latest_allowed_completion_at: object = "2026-07-20T16:00:00+00:00",
) -> dict[str, object]:
    return {
        "ReservationLineID": reservation_line_id,
        "OrderID": order_id,
        "OperationID": operation_id,
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "WindowEndAt": "2026-07-20T16:00:00+00:00",
        "ReservedMinutes": reserved_minutes,
        "LatestAllowedCompletionAt": latest_allowed_completion_at,
    }


def test_prepare_and_apply_confirmation_writes_batch_capacity_material_and_event():
    write_set = _prepare(
        capacity_requests=[_capacity_request()],
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
    assert collections[4][0]["PayloadFingerprint"] == write_set.payload_fingerprint
    assert collections[4][0]["Result"] == {
        "DemandCommitmentID": write_set.demand_commitment["DemandCommitmentID"],
        "ReservationBatchID": write_set.batch["ReservationBatchID"],
        "CapacityReservationIDs": list(write_set.batch["CapacityReservationIDs"]),
        "MaterialAllocationIDs": list(write_set.batch["MaterialAllocationIDs"]),
    }
    assert write_set.idempotency_key in collections[5]


def test_duplicate_confirmation_does_not_create_second_batch():
    write_set = _prepare()
    collections = ({}, {}, {}, {}, [], set())

    _apply(write_set, collections)
    _apply(write_set, collections)

    assert len(collections[1]) == 1
    assert len(collections[4]) == 1


def test_prepare_rejects_drifted_candidate_demand_identity():
    demand = _demand()
    demand["BusinessKey"] = "forged-business-key"

    with pytest.raises(ReservationConflict, match="identity"):
        _prepare(demand_commitment=demand)


def test_idempotent_replay_requires_canonical_persisted_demand_domain():
    write_set = _prepare()
    collections = ({}, {}, {}, {}, [], set())
    _apply(write_set, collections)
    demand_id = str(write_set.demand_commitment["DemandCommitmentID"])
    persisted = collections[0][demand_id]
    persisted["DemandSourceType"] = "Forecast"
    business_content = {
        field: persisted[field] for field in BUSINESS_CONTENT_FIELDS
    }
    encoded = json.dumps(
        business_content,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    persisted["ContentFingerprint"] = f"sha256:{sha256(encoded).hexdigest()}"
    before = deepcopy(collections)

    with pytest.raises(ReservationConflict) as error:
        _apply(write_set, collections)

    assert error.value.status == "PlanningReservationLegacyMigrationRequired"
    assert collections == before


def test_idempotent_replay_requires_every_persisted_result_child():
    write_set = _prepare(
        capacity_requests=[_capacity_request()],
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 20,
        }],
    )
    collections = ({}, {}, {}, {}, [], set())
    _apply(write_set, collections)
    capacity_id = str(write_set.capacity_reservations[0]["CapacityReservationID"])
    collections[2].pop(capacity_id)
    before = deepcopy(collections)

    with pytest.raises(ReservationConflict) as error:
        _apply(write_set, collections)

    assert error.value.status == "PlanningReservationLegacyMigrationRequired"
    assert collections == before


@pytest.mark.parametrize(
    ("collection_index", "record_id_field", "immutable_field"),
    [
        (2, "CapacityReservationID", "ResourceID"),
        (3, "MaterialAllocationID", "ItemID"),
    ],
)
def test_idempotent_replay_rejects_immutable_persisted_child_drift(
    collection_index: int,
    record_id_field: str,
    immutable_field: str,
):
    write_set = _prepare(
        capacity_requests=[_capacity_request()],
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 20,
        }],
    )
    collections = ({}, {}, {}, {}, [], set())
    _apply(write_set, collections)
    candidate_rows = (
        write_set.capacity_reservations
        if collection_index == 2
        else write_set.material_allocations
    )
    record_id = str(candidate_rows[0][record_id_field])
    collections[collection_index][record_id][immutable_field] = "DRIFTED"
    before = deepcopy(collections)

    with pytest.raises(ReservationConflict, match="immutable"):
        _apply(write_set, collections)

    assert collections == before


def test_idempotent_replay_allows_documented_lifecycle_changes():
    write_set = _prepare(
        capacity_requests=[_capacity_request()],
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 20,
            "MaterialSnapshotID": "OPS-1",
        }],
    )
    collections = ({}, {}, {}, {}, [], set())
    _apply(write_set, collections)
    demand = collections[0][str(write_set.demand_commitment["DemandCommitmentID"])]
    batch = collections[1][str(write_set.batch["ReservationBatchID"])]
    capacity = collections[2][
        str(write_set.capacity_reservations[0]["CapacityReservationID"])
    ]
    material = collections[3][
        str(write_set.material_allocations[0]["MaterialAllocationID"])
    ]
    demand.update({"Status": "LinkedToFormalOrder", "RecordVersion": 2})
    for record in (batch, capacity):
        record.update(
            {
                "Status": "ConvertedToScheduledOccupancy",
                "RecordVersion": 2,
                "PlanningRunID": "RUN-1",
                "LastTransitionAt": "2026-07-20T12:00:00+00:00",
                "EventType": "PlanningRunCompleted",
            }
        )
    material.update(
        {
            "Status": "Externalized",
            "RecordVersion": 2,
            "ExternalAllocationRef": "ERP-ALLOC-1",
            "MaterialSnapshotID": "OPS-AUTHORITY-2",
        }
    )

    _apply(write_set, collections)

    assert len(collections[1]) == 1
    assert len(collections[4]) == 1


@pytest.mark.parametrize(
    "lifecycle_status",
    ["ActivePlanReservation", "HeldForPlanningError"],
)
def test_true_pre_fix_replay_fails_closed_with_structured_migration_requirement(
    lifecycle_status: str,
):
    write_set = _prepare(capacity_requests=[_capacity_request()])
    demand_id = str(write_set.demand_commitment["DemandCommitmentID"])
    old_batch_id = "PRB-f1f16bdff93d72c8c0a9"
    old_capacity_id = "CCR-f36148473b60a289b70b"
    old_event = {
        "EventID": "PRE-e893d23228887c0cad8d",
        "EventType": "PlanningReservationActivated",
        "DemandCommitmentID": demand_id,
        "ReservationBatchID": old_batch_id,
        "OccurredAt": "2026-07-10T08:00:00+00:00",
        "ActorID": "planner-1",
        "IdempotencyKey": write_set.idempotency_key,
        "TraceID": "TRACE-REC-1",
    }
    collections = (
        {demand_id: dict(write_set.demand_commitment)},
        {
            old_batch_id: {
                "ReservationBatchID": old_batch_id,
                "DemandCommitmentID": demand_id,
                "DemandClass": "MTA",
                "Status": lifecycle_status,
                "ConfirmationID": "CONFIRM-1",
                "ConfirmedBy": "planner-1",
                "ConfirmedAt": "2026-07-10T08:00:00+00:00",
                "CapacityReservationIDs": [old_capacity_id],
                "MaterialAllocationIDs": [],
            }
        },
        {
            old_capacity_id: {
                "CapacityReservationID": old_capacity_id,
                "ReservationBatchID": old_batch_id,
                "DemandCommitmentID": demand_id,
                "DemandClass": "MTA",
                "Status": lifecycle_status,
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "WindowEndAt": "2026-07-20T16:00:00+00:00",
                "ReservedMinutes": 120,
                "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
            }
        },
        {},
        [old_event],
        {write_set.idempotency_key},
    )
    before = deepcopy(collections)

    with pytest.raises(ReservationConflict) as error:
        _apply(write_set, collections)

    assert error.value.status == "PlanningReservationLegacyMigrationRequired"
    assert "migration" in str(error.value).lower()
    assert collections == before


def test_idempotency_key_reuse_with_changed_payload_is_rejected_without_mutation():
    original = _prepare(capacity_requests=[_capacity_request(reserved_minutes=120)])
    changed = _prepare(capacity_requests=[_capacity_request(reserved_minutes=121)])
    collections = ({}, {}, {}, {}, [], set())
    _apply(original, collections)
    before = (
        dict(collections[0]),
        dict(collections[1]),
        dict(collections[2]),
        dict(collections[3]),
        list(collections[4]),
        set(collections[5]),
    )

    with pytest.raises(ReservationConflict, match="idempotency key"):
        _apply(changed, collections)

    assert collections == before


def test_demand_cannot_have_two_non_terminal_reservation_batches():
    first = _prepare(confirmation_id="CONFIRM-1")
    competing = _prepare(confirmation_id="CONFIRM-2")
    collections = ({}, {}, {}, {}, [], set())
    _apply(first, collections)
    before = (
        dict(collections[0]),
        dict(collections[1]),
        dict(collections[2]),
        dict(collections[3]),
        list(collections[4]),
        set(collections[5]),
    )

    with pytest.raises(ReservationConflict, match="non-terminal reservation batch"):
        _apply(competing, collections)

    assert collections == before


def test_converted_demand_allows_only_exact_idempotent_replay_not_new_confirmation():
    first = _prepare(
        confirmation_id="CONFIRM-1",
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 10,
        }],
    )
    competing = _prepare(
        confirmation_id="CONFIRM-2",
        material_requests=[{
            "RequirementLineID": "REQ-2",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 10,
        }],
    )
    collections = ({}, {}, {}, {}, [], set())
    _apply(first, collections)
    first_batch_id = str(first.batch["ReservationBatchID"])
    collections[1][first_batch_id].update(
        {
            "Status": "ConvertedToScheduledOccupancy",
            "RecordVersion": 2,
            "PlanningRunID": "RUN-CONVERTED",
            "LastTransitionAt": "2026-07-20T12:00:00+00:00",
            "EventType": "PlanningRunCompleted",
        }
    )

    _apply(first, collections)
    before_competing = deepcopy(collections)

    with pytest.raises(ReservationConflict, match="already has a reservation batch"):
        _apply(competing, collections)

    assert collections == before_competing
    assert len(collections[3]) == 1


def test_stable_child_ids_and_payload_fingerprint_do_not_depend_on_request_order():
    capacity_a = _capacity_request(
        reservation_line_id="CAP-A", operation_id="WO-1:CCR-A"
    )
    capacity_b = _capacity_request(
        reservation_line_id="CAP-B", operation_id="WO-1:CCR-B"
    )
    material_a = {
        "RequirementLineID": "REQ-A",
        "ItemID": "RM-1",
        "LocationID": "MAIN",
        "AllocatedQty": 10,
    }
    material_b = {
        "RequirementLineID": "REQ-B",
        "ItemID": "RM-2",
        "LocationID": "MAIN",
        "AllocatedQty": 20,
    }

    first = _prepare(
        capacity_requests=[capacity_a, capacity_b],
        material_requests=[material_a, material_b],
    )
    reordered = _prepare(
        capacity_requests=[capacity_b, capacity_a],
        material_requests=[material_b, material_a],
    )

    assert first.capacity_reservations == reordered.capacity_reservations
    assert first.material_allocations == reordered.material_allocations
    assert first.payload_fingerprint == reordered.payload_fingerprint


@pytest.mark.parametrize("line_kind", ["capacity_identity", "capacity_correlation", "material"])
def test_prepare_rejects_duplicate_semantic_reservation_lines(line_kind: str):
    if line_kind == "capacity_identity":
        capacity_requests = [
            _capacity_request(),
            _capacity_request(operation_id="WO-1:CCR-2"),
        ]
        material_requests = []
    elif line_kind == "capacity_correlation":
        capacity_requests = [
            _capacity_request(reservation_line_id="CAP-A"),
            _capacity_request(reservation_line_id="CAP-B"),
        ]
        material_requests = []
    else:
        capacity_requests = []
        material_requests = [
            {
                "RequirementLineID": "REQ-1",
                "ItemID": "RM-1",
                "LocationID": "MAIN",
                "AllocatedQty": 10,
            },
            {
                "RequirementLineID": "REQ-1",
                "ItemID": "RM-2",
                "LocationID": "MAIN",
                "AllocatedQty": 20,
            },
        ]

    with pytest.raises(ReservationConflict, match="duplicate semantic"):
        _prepare(
            capacity_requests=capacity_requests,
            material_requests=material_requests,
        )


def test_invalid_capacity_request_builds_no_partial_write_set():
    with pytest.raises(ReservationConflict, match="positive reserved minutes"):
        _prepare(
            capacity_requests=[{
                "ReservationLineID": "CAP-LINE-1",
                "OrderID": "WO-1",
                "OperationID": "WO-1:CCR",
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "WindowEndAt": "2026-07-20T16:00:00+00:00",
                "ReservedMinutes": 0,
            }]
        )


@pytest.mark.parametrize(
    ("window_start", "window_end", "message"),
    [
        ("not-a-datetime", "2026-07-20T16:00:00+00:00", "ISO datetime"),
        ("2026-07-20T08:00:00", "2026-07-20T16:00:00+00:00", "timezone-aware"),
        (
            "2026-07-20T08:00:00+00:00",
            "2026-07-20T08:00:00+00:00",
            "after start",
        ),
        (
            "2026-07-20T16:00:00+00:00",
            "2026-07-20T08:00:00+00:00",
            "after start",
        ),
    ],
)
def test_prepare_rejects_invalid_capacity_windows(
    window_start: str, window_end: str, message: str
):
    with pytest.raises(ReservationConflict, match=message):
        _prepare(
            capacity_requests=[{
                "ResourceID": "CCR-1",
                "WindowStartAt": window_start,
                "WindowEndAt": window_end,
                "ReservedMinutes": 120,
            }]
        )


@pytest.mark.parametrize(
    ("latest_allowed_completion_at", "message"),
    [
        (None, "LatestAllowedCompletionAt is required"),
        ("2026-07-20T12:00:00", "timezone-aware"),
        ("2026-07-20T07:59:00+00:00", "inside the reservation window"),
        ("2026-07-20T16:01:00+00:00", "inside the reservation window"),
    ],
)
def test_prepare_requires_aware_latest_completion_inside_capacity_window(
    latest_allowed_completion_at: object,
    message: str,
):
    request = _capacity_request(
        latest_allowed_completion_at=latest_allowed_completion_at
    )
    if latest_allowed_completion_at is None:
        request.pop("LatestAllowedCompletionAt")

    with pytest.raises(ReservationConflict, match=message):
        _prepare(capacity_requests=[request])


def test_prepare_deep_copies_request_rows_before_validation_records_are_returned():
    capacity_request = {
        "ReservationLineID": "CAP-LINE-1",
        "OrderID": "WO-1",
        "OperationID": "WO-1:CCR",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "WindowEndAt": "2026-07-20T16:00:00+00:00",
        "ReservedMinutes": 120,
        "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
        "RequestContext": {"priority": "original"},
    }
    material_request = {
        "RequirementLineID": "REQ-1",
        "ItemID": "RM-1",
        "LocationID": "MAIN",
        "AllocatedQty": 20,
        "RequestContext": {"priority": "original"},
    }
    write_set = _prepare(
        capacity_requests=[capacity_request], material_requests=[material_request]
    )

    capacity_request["RequestContext"]["priority"] = "changed"
    material_request["RequestContext"]["priority"] = "changed"

    assert write_set.capacity_reservations[0]["RequestContext"] == {
        "priority": "original"
    }
    assert write_set.material_allocations[0]["RequestContext"] == {
        "priority": "original"
    }


def test_apply_deep_copies_write_set_records_into_stored_collections():
    write_set = _prepare(
        capacity_requests=[{
            **_capacity_request(),
            "RequestContext": {"priority": "original"},
        }]
    )
    collections = ({}, {}, {}, {}, [], set())
    _apply(write_set, collections)

    write_set.batch["CapacityReservationIDs"].append("CALLER-INSERTED")
    write_set.capacity_reservations[0]["RequestContext"]["priority"] = "changed"

    assert "CALLER-INSERTED" not in collections[1][
        str(write_set.batch["ReservationBatchID"])
    ]["CapacityReservationIDs"]
    assert next(iter(collections[2].values()))["RequestContext"] == {
        "priority": "original"
    }


@pytest.mark.parametrize("target", ["capacity", "material", "event"])
def test_duplicate_ids_inside_write_set_are_rejected_without_mutation(target: str):
    write_set = _prepare(
        capacity_requests=[_capacity_request()],
        material_requests=[{
            "RequirementLineID": "REQ-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "AllocatedQty": 20,
        }],
    )
    if target == "capacity":
        duplicate = {**write_set.capacity_reservations[0], "Status": "Cancelled"}
        write_set = replace(
            write_set,
            capacity_reservations=(*write_set.capacity_reservations, duplicate),
        )
    elif target == "material":
        duplicate = {**write_set.material_allocations[0], "Status": "Cancelled"}
        write_set = replace(
            write_set,
            material_allocations=(*write_set.material_allocations, duplicate),
        )
    else:
        duplicate = {**write_set.events[0], "ActorID": "planner-2"}
        write_set = replace(write_set, events=(*write_set.events, duplicate))

    collections = ({}, {}, {}, {}, [], set())

    with pytest.raises(ReservationConflict, match="different content"):
        _apply(write_set, collections)

    assert collections == ({}, {}, {}, {}, [], set())


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
            "ReservationLineID": "CAP-LINE-1",
            "OrderID": "WO-1",
            "OperationID": "WO-1:CCR",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "WindowEndAt": "2026-07-20T16:00:00+00:00",
            "ReservedMinutes": 120,
            "LatestAllowedCompletionAt": "2026-07-20T16:00:00+00:00",
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
