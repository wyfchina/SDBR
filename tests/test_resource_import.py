from datetime import date

from sdbr.resource_import import ResourceCapacityImportRow, import_resources_from_capacity_rows


def test_import_resources_from_capacity_rows_groups_daily_capacity_by_resource():
    rows = [
        ResourceCapacityImportRow(
            resource_id="WC-ASM",
            name="Assembly Cell",
            is_constraint=False,
            capacity_date=date(2026, 6, 17),
            capacity_minutes=960,
        ),
        ResourceCapacityImportRow(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            capacity_date=date(2026, 6, 16),
            capacity_minutes=480,
        ),
        ResourceCapacityImportRow(
            resource_id="WC-ASM",
            name="Assembly Cell",
            is_constraint=False,
            capacity_date=date(2026, 6, 16),
            capacity_minutes=960,
        ),
    ]

    resources = import_resources_from_capacity_rows(rows)

    assert [resource.resource_id for resource in resources] == ["WC-ASM", "WC-DRUM"]
    assert resources[0].daily_capacity_minutes == {
        date(2026, 6, 16): 960,
        date(2026, 6, 17): 960,
    }
    assert resources[1].is_constraint is True
