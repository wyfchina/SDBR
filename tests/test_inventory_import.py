from sdbr.inventory_import import InventoryBufferImportRow, import_inventory_buffers_from_rows


def test_import_inventory_buffers_from_rows_maps_and_sorts_buffer_policies():
    rows = [
        InventoryBufferImportRow(
            item_id="WIP-KIT",
            location_id="LINE-SUPERMARKET",
            on_hand_qty=160,
            red_zone_qty=40,
            yellow_zone_qty=90,
            green_zone_qty=160,
        ),
        InventoryBufferImportRow(
            item_id="RM-STEEL",
            location_id="SUPPLIER-DECOUPLING",
            on_hand_qty=35,
            red_zone_qty=50,
            yellow_zone_qty=120,
            green_zone_qty=200,
        ),
    ]

    buffers = import_inventory_buffers_from_rows(rows)

    assert [buffer.item_id for buffer in buffers] == ["RM-STEEL", "WIP-KIT"]
    assert buffers[0].location_id == "SUPPLIER-DECOUPLING"
    assert buffers[0].on_hand_qty == 35
    assert buffers[0].red_zone_qty == 50
