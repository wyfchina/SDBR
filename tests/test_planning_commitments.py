from datetime import datetime, timezone

import pytest

from sdbr.planning_commitments import (
    DemandCommitmentConflict,
    assert_no_active_predecessor,
    create_demand_commitment,
    register_demand_commitment,
)


def _commitment(*, version: str = "1", quantity: float = 10) -> dict[str, object]:
    return create_demand_commitment(
        demand_source_type="MTOCustomerOrder",
        source_system="MockERP",
        source_object_type="CustomerOrder",
        source_object_id="SO-100",
        source_object_version=version,
        demand_line_id="10",
        item_or_product_id="FG-1",
        location_id="MAIN",
        quantity=quantity,
        uom="EA",
        required_at=datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
        demand_class="MTO",
        trace_id="TRACE-SO-100-10",
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
