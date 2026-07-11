"""Acceptance evidence for BE-SDBR-006 stable demand commitment identity."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from sdbr.planning_commitments import (
    BUSINESS_CONTENT_FIELDS,
    DemandCommitmentConflict,
    DemandCommitmentMigrationRequired,
    assert_no_active_predecessor,
    create_demand_commitment,
    register_demand_commitment,
)


def _commitment(
    *,
    demand_source_type: str = "MTOCustomerOrder",
    source_system: str = "MockERP",
    source_object_type: str = "CustomerOrder",
    version: str = "1",
    quantity: float = 10,
    required_at: datetime | None = None,
    trace_id: str = "TRACE-SO-100-10",
) -> dict[str, object]:
    return create_demand_commitment(
        demand_source_type=demand_source_type,
        source_system=source_system,
        source_object_type=source_object_type,
        source_object_id="SO-100",
        source_object_version=version,
        demand_line_id="10",
        item_or_product_id="FG-1",
        location_id="MAIN",
        quantity=quantity,
        uom="EA",
        required_at=required_at
        or datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
        demand_class="MTO",
        trace_id=trace_id,
    )


def test_register_same_business_key_and_content_is_idempotent():
    candidate = _commitment()
    status, first = register_demand_commitment({}, candidate)
    status_again, duplicate = register_demand_commitment(
        {str(first["DemandCommitmentID"]): first}, candidate
    )
    assert status == "Created"
    assert status_again == "Duplicate"
    assert duplicate == first


def test_same_business_key_and_version_with_changed_content_is_conflict():
    existing = _commitment(quantity=10)
    with pytest.raises(DemandCommitmentConflict, match="same business key"):
        register_demand_commitment(
            {str(existing["DemandCommitmentID"]): existing},
            _commitment(quantity=12),
        )


def test_new_version_cannot_activate_while_predecessor_is_active():
    active = {**_commitment(version="1"), "Status": "Active"}
    with pytest.raises(DemandCommitmentConflict, match="active predecessor"):
        assert_no_active_predecessor(
            {str(active["DemandCommitmentID"]): active},
            _commitment(version="2"),
        )


@pytest.mark.parametrize(
    "demand_source_type",
    [
        "MTOCustomerOrder",
        "MTAReplenishment",
        "DependentDemand",
        "ExternalFormalOrder",
        "Adjustment",
    ],
)
def test_create_demand_commitment_accepts_each_allowed_source_type(
    demand_source_type: str,
):
    commitment = _commitment(demand_source_type=demand_source_type)

    assert commitment["DemandSourceType"] == demand_source_type


def test_create_demand_commitment_rejects_unsupported_source_type():
    with pytest.raises(ValueError, match="Unsupported demand source type"):
        _commitment(demand_source_type="Forecast")


def test_create_demand_commitment_identity_and_fingerprint_are_deterministic():
    first = _commitment()
    second = _commitment()

    assert first["DemandCommitmentID"] == second["DemandCommitmentID"]
    assert first["BusinessKey"] == second["BusinessKey"]
    assert first["LogicalDemandKey"] == second["LogicalDemandKey"]
    assert first["ContentFingerprint"] == second["ContentFingerprint"]


def test_business_fingerprint_normalizes_equivalent_required_at_offsets_to_utc():
    utc_commitment = _commitment(
        required_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc)
    )
    offset_commitment = _commitment(
        required_at=datetime(
            2026,
            7,
            20,
            16,
            tzinfo=timezone(timedelta(hours=8)),
        )
    )

    assert utc_commitment["RequiredAt"] == "2026-07-20T08:00:00+00:00"
    assert offset_commitment["RequiredAt"] == "2026-07-20T08:00:00+00:00"
    assert offset_commitment["ContentFingerprint"] == utc_commitment[
        "ContentFingerprint"
    ]


def test_trace_id_change_is_idempotent_business_replay_metadata():
    existing = _commitment(trace_id="TRACE-ATTEMPT-1")
    replay = _commitment(trace_id="TRACE-ATTEMPT-2")

    status, registered = register_demand_commitment(
        {str(existing["DemandCommitmentID"]): existing}, replay
    )

    assert replay["ContentFingerprint"] == existing["ContentFingerprint"]
    assert status == "Duplicate"
    assert registered == existing


@pytest.mark.parametrize("forged_record", ["existing", "candidate"])
def test_register_recomputes_persisted_and_candidate_fingerprints(
    forged_record: str,
):
    existing = _commitment()
    candidate = _commitment()
    target = existing if forged_record == "existing" else candidate
    target["ContentFingerprint"] = "sha256:forged"

    with pytest.raises(DemandCommitmentConflict) as error:
        register_demand_commitment(
            {str(existing["DemandCommitmentID"]): existing}, candidate
        )

    expected_status = (
        "DemandCommitmentMigrationRequired"
        if forged_record == "existing"
        else "DemandCommitmentConflict"
    )
    assert error.value.status == expected_status


def test_register_does_not_treat_two_malformed_business_records_as_equal():
    existing = _commitment()
    candidate = _commitment()
    existing.pop("RequiredAt")
    candidate.pop("RequiredAt")

    with pytest.raises(DemandCommitmentConflict) as error:
        register_demand_commitment(
            {str(existing["DemandCommitmentID"]): existing}, candidate
        )

    assert error.value.status == "DemandCommitmentMigrationRequired"


@pytest.mark.parametrize(
    "field",
    ["BusinessKey", "LogicalDemandKey", "DemandCommitmentID"],
)
@pytest.mark.parametrize("record_kind", ["stored", "candidate"])
def test_register_rejects_drifted_derived_demand_identity(
    field: str,
    record_kind: str,
):
    existing = _commitment()
    candidate = _commitment()
    target = existing if record_kind == "stored" else candidate
    target[field] = f"forged-{field}"
    commitments = (
        {str(_commitment()["DemandCommitmentID"]): existing}
        if record_kind == "stored"
        else {}
    )

    with pytest.raises(DemandCommitmentConflict) as error:
        register_demand_commitment(commitments, candidate)

    expected_type = (
        DemandCommitmentMigrationRequired
        if record_kind == "stored"
        else DemandCommitmentConflict
    )
    assert type(error.value) is expected_type


def _legacy_business_fingerprint(record: dict[str, object]) -> str:
    content = {field: record[field] for field in BUSINESS_CONTENT_FIELDS}
    encoded = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("DemandSourceType", "Forecast"), ("Quantity", 0.0)],
)
@pytest.mark.parametrize("record_kind", ["stored", "candidate"])
def test_register_rejects_self_consistent_invalid_domain_content(
    field: str,
    invalid_value: object,
    record_kind: str,
):
    invalid = _commitment()
    invalid[field] = invalid_value
    invalid["ContentFingerprint"] = _legacy_business_fingerprint(invalid)
    candidate = deepcopy(invalid)
    commitments = (
        {str(invalid["DemandCommitmentID"]): invalid}
        if record_kind == "stored"
        else {}
    )

    with pytest.raises(DemandCommitmentConflict) as error:
        register_demand_commitment(commitments, candidate)

    expected_type = (
        DemandCommitmentMigrationRequired
        if record_kind == "stored"
        else DemandCommitmentConflict
    )
    assert type(error.value) is expected_type


def test_register_rejects_duplicate_matching_business_key_ledger():
    existing = _commitment()
    duplicate = deepcopy(existing)

    with pytest.raises(
        DemandCommitmentMigrationRequired,
        match="multiple persisted demand commitments",
    ):
        register_demand_commitment(
            {
                str(existing["DemandCommitmentID"]): existing,
                "duplicate-ledger-row": duplicate,
            },
            _commitment(),
        )


def test_predecessor_check_rejects_drifted_stored_logical_identity():
    predecessor = {**_commitment(version="1"), "Status": "Active"}
    predecessor["LogicalDemandKey"] = "forged-logical-demand"

    with pytest.raises(DemandCommitmentMigrationRequired):
        assert_no_active_predecessor(
            {str(predecessor["DemandCommitmentID"]): predecessor},
            _commitment(version="2"),
        )


def test_create_demand_commitment_delimited_source_identifiers_remain_distinct():
    first = _commitment(source_system="ERP|A", source_object_type="Order")
    second = _commitment(source_system="ERP", source_object_type="A|Order")

    assert first["BusinessKey"] != second["BusinessKey"]
    assert first["LogicalDemandKey"] != second["LogicalDemandKey"]
    assert first["DemandCommitmentID"] != second["DemandCommitmentID"]


def test_create_demand_commitment_rejects_naive_required_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        _commitment(required_at=datetime(2026, 7, 20, 8))


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -1,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
    ],
)
def test_create_demand_commitment_rejects_non_positive_or_non_finite_quantities(
    quantity: float,
):
    with pytest.raises(ValueError, match="finite, strictly positive real number"):
        _commitment(quantity=quantity)


@pytest.mark.parametrize(
    "status",
    ["Active", "LinkedToFormalOrder", "HeldForPlanningError"],
)
def test_new_version_cannot_activate_while_predecessor_has_active_status(status: str):
    active = {**_commitment(version="1"), "Status": status}

    with pytest.raises(DemandCommitmentConflict, match="active predecessor"):
        assert_no_active_predecessor(
            {str(active["DemandCommitmentID"]): active},
            _commitment(version="2"),
        )


def test_new_version_can_activate_while_predecessor_is_not_active():
    inactive = {**_commitment(version="1"), "Status": "Cancelled"}

    assert_no_active_predecessor(
        {str(inactive["DemandCommitmentID"]): inactive},
        _commitment(version="2"),
    )
