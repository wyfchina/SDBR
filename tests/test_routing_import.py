from sdbr.routing_import import RoutingImportRow, import_routings_from_operation_rows


def test_import_routings_from_operation_rows_groups_and_sorts_operations():
    rows = [
        RoutingImportRow(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operation_id="ASM",
            resource_id="WC-ASM",
            duration_minutes=80,
            sequence=2,
        ),
        RoutingImportRow(
            product_id="FG-A",
            routing_id="ALT-LASER",
            is_primary=False,
            operation_id="LASER",
            resource_id="WC-LASER",
            duration_minutes=100,
            sequence=1,
        ),
        RoutingImportRow(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operation_id="CUT",
            resource_id="WC-DRUM",
            alternate_resource_ids=["WC-LASER"],
            duration_minutes=120,
            sequence=1,
        ),
    ]

    routings = import_routings_from_operation_rows(rows)

    assert [routing.routing_id for routing in routings] == ["ALT-LASER", "PRIMARY"]
    primary = routings[1]
    assert primary.product_id == "FG-A"
    assert primary.is_primary is True
    assert [operation.operation_id for operation in primary.operations] == ["CUT", "ASM"]
    assert primary.operations[0].resource_id == "WC-DRUM"
    assert primary.operations[0].alternate_resource_ids == ["WC-LASER"]


def test_import_routings_from_operation_rows_preserves_inconsistent_primary_flags_for_validation():
    rows = [
        RoutingImportRow(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operation_id="CUT",
            resource_id="WC-DRUM",
            duration_minutes=120,
            sequence=1,
        ),
        RoutingImportRow(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=False,
            operation_id="ASM",
            resource_id="WC-ASM",
            duration_minutes=80,
            sequence=2,
        ),
    ]

    routings = import_routings_from_operation_rows(rows)

    assert len(routings) == 2
    assert {routing.is_primary for routing in routings} == {True, False}
