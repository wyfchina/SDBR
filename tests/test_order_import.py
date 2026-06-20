from datetime import date, datetime, timezone

from sdbr.order_import import OrderImportRow, import_orders_from_rows


def test_import_orders_from_rows_maps_and_sorts_scheduling_orders():
    rows = [
        OrderImportRow(
            order_id="WO-2",
            product_id="FG-B",
            quantity=2,
            due_date=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 17),
        ),
        OrderImportRow(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        ),
    ]

    orders = import_orders_from_rows(rows)

    assert [order.order_id for order in orders] == ["WO-1", "WO-2"]
    assert orders[0].product_id == "FG-A"
    assert orders[0].quantity == 1
    assert orders[0].due_date == datetime(2026, 6, 20, 8, tzinfo=timezone.utc)
    assert orders[0].target_start_date == date(2026, 6, 16)
