from datetime import date, datetime, time, timezone

from sdbr.master_data_validation import MaterialRequirement, validate_master_data
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.planner_workbench import (
    MaintenanceWindow,
    Operation,
    Resource,
    Routing,
    SchedulingOrder,
    Shift,
    WorkCalendar,
)


def test_master_data_validation_flags_duplicate_resources_and_missing_constraint():
    resources = [
        Resource(
            resource_id="WC-ASM",
            name="Assembly Cell A",
            is_constraint=False,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
        Resource(
            resource_id="WC-ASM",
            name="Assembly Cell B",
            is_constraint=False,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            operations=[
                Operation(
                    operation_id="ASM",
                    resource_id="WC-ASM",
                    duration_minutes=60,
                    sequence=1,
                )
            ],
        )
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        )
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=[],
        calendar_timezone=None,
    )

    assert result.is_valid is False
    assert {
        issue.code: issue.message
        for issue in result.issues
    } == {
        "DUPLICATE_RESOURCE_ID": "Resource WC-ASM is defined more than once.",
        "NO_CONSTRAINT_RESOURCE": "At least one resource must be marked as the drum constraint.",
    }


def test_master_data_validation_flags_order_operation_and_inventory_buffer_quality_issues():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        )
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    duration_minutes=0,
                    sequence=1,
                )
            ],
        )
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=0,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        ),
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 17),
        ),
    ]
    inventory_buffers = [
        InventoryBufferPolicy(
            item_id="RM-STEEL",
            location_id="SUPPLIER-DECOUPLING",
            on_hand_qty=10,
            red_zone_qty=120,
            yellow_zone_qty=80,
            green_zone_qty=200,
        )
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=inventory_buffers,
        calendar_timezone=None,
    )

    assert result.is_valid is False
    assert {
        issue.code: issue.message
        for issue in result.issues
    } == {
        "NON_POSITIVE_OPERATION_DURATION": "Operation CUT must have a positive duration.",
        "DUPLICATE_ORDER_ID": "Order WO-1 is defined more than once.",
        "NON_POSITIVE_ORDER_QUANTITY": "Order WO-1 must have a positive quantity.",
        "INVALID_INVENTORY_BUFFER_ZONES": (
            "Inventory buffer RM-STEEL at SUPPLIER-DECOUPLING must satisfy "
            "0 <= red <= yellow <= green."
        ),
    }


def test_master_data_validation_flags_material_requirement_quality_issues():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        )
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    duration_minutes=60,
                    sequence=1,
                )
            ],
        )
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        )
    ]
    inventory_buffers = [
        InventoryBufferPolicy(
            item_id="RM-STEEL",
            location_id="SUPPLIER-DECOUPLING",
            on_hand_qty=80,
            red_zone_qty=50,
            yellow_zone_qty=120,
            green_zone_qty=200,
        )
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=inventory_buffers,
        material_requirements=[
            MaterialRequirement(
                order_id="WO-MISSING",
                item_id="RM-STEEL",
                location_id="SUPPLIER-DECOUPLING",
                required_qty=10,
            ),
            MaterialRequirement(
                order_id="WO-1",
                item_id="RM-MISSING",
                location_id="SUPPLIER-DECOUPLING",
                required_qty=10,
            ),
            MaterialRequirement(
                order_id="WO-1",
                item_id="RM-STEEL",
                location_id="SUPPLIER-DECOUPLING",
                required_qty=0,
            ),
        ],
        calendar_timezone=None,
    )

    assert result.is_valid is False
    assert {
        issue.code: issue.message
        for issue in result.issues
    } == {
        "UNKNOWN_MATERIAL_REQUIREMENT_ORDER": (
            "Material requirement for RM-STEEL references missing order WO-MISSING."
        ),
        "UNKNOWN_MATERIAL_REQUIREMENT_BUFFER": (
            "Material requirement for RM-MISSING at SUPPLIER-DECOUPLING "
            "does not match an inventory buffer."
        ),
        "NON_POSITIVE_MATERIAL_REQUIREMENT_QTY": (
            "Material requirement for RM-STEEL on order WO-1 must have a positive quantity."
        ),
    }
    assert result.summary["MaterialRequirementCount"] == 3


def test_master_data_validation_flags_resource_calendar_and_capacity_quality_issues():
    calendar = WorkCalendar(
        calendar_id="CAL-BAD",
        working_weekdays={0, 7},
        shifts=[Shift(name="Bad", start=time(16, 0), end=time(8, 0))],
        maintenance_windows=[
            MaintenanceWindow(
                start=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
                end=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
            )
        ],
    )
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): -10},
            calendar=calendar,
        )
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    duration_minutes=60,
                    sequence=1,
                )
            ],
        )
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        )
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=[],
        calendar_timezone="UTC",
    )

    assert result.is_valid is False
    assert {
        issue.code: issue.message
        for issue in result.issues
    } == {
        "NEGATIVE_RESOURCE_CAPACITY": (
            "Resource WC-DRUM has negative capacity on 2026-06-16."
        ),
        "INVALID_CALENDAR_WEEKDAY": "Calendar CAL-BAD has invalid weekday 7.",
        "INVALID_SHIFT_WINDOW": (
            "Shift Bad in calendar CAL-BAD must end after it starts."
        ),
        "INVALID_MAINTENANCE_WINDOW": (
            "Maintenance window in calendar CAL-BAD must end after it starts."
        ),
    }


def test_master_data_validation_flags_routing_identity_and_primary_route_issues():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        )
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    duration_minutes=60,
                    sequence=1,
                )
            ],
        ),
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operations=[
                Operation(
                    operation_id="CUT-ALT",
                    resource_id="WC-DRUM",
                    duration_minutes=50,
                    sequence=1,
                )
            ],
        ),
        Routing(
            product_id="FG-B",
            routing_id="ALT",
            is_primary=False,
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    duration_minutes=60,
                    sequence=1,
                )
            ],
        ),
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        ),
        SchedulingOrder(
            order_id="WO-2",
            product_id="FG-B",
            quantity=1,
            due_date=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 17),
        ),
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=[],
        calendar_timezone=None,
    )

    assert result.is_valid is False
    assert {
        issue.code: issue.message
        for issue in result.issues
    } == {
        "DUPLICATE_ROUTING_ID": (
            "Routing PRIMARY for product FG-A is defined more than once."
        ),
        "DUPLICATE_PRIMARY_ROUTING": (
            "Product FG-A has more than one primary routing."
        ),
        "MISSING_PRIMARY_ROUTING": "Product FG-B must have exactly one primary routing.",
    }


def test_master_data_validation_flags_operation_sequence_quality_issues():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        )
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    duration_minutes=60,
                    sequence=1,
                ),
                Operation(
                    operation_id="TRIM",
                    resource_id="WC-DRUM",
                    duration_minutes=30,
                    sequence=1,
                ),
                Operation(
                    operation_id="PACK",
                    resource_id="WC-DRUM",
                    duration_minutes=20,
                    sequence=0,
                ),
            ],
        )
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        )
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=[],
        calendar_timezone=None,
    )

    assert result.is_valid is False
    assert {
        issue.code: issue.message
        for issue in result.issues
    } == {
        "DUPLICATE_OPERATION_SEQUENCE": (
            "Routing PRIMARY for product FG-A uses sequence 1 more than once."
        ),
        "NON_POSITIVE_OPERATION_SEQUENCE": "Operation PACK must have a positive sequence.",
    }


def test_master_data_validation_flags_unknown_alternate_operation_resource():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        )
    ]
    routings = [
        Routing(
            product_id="FG-A",
            routing_id="PRIMARY",
            is_primary=True,
            operations=[
                Operation(
                    operation_id="CUT",
                    resource_id="WC-DRUM",
                    alternate_resource_ids=["WC-MISSING"],
                    duration_minutes=60,
                    sequence=1,
                )
            ],
        )
    ]
    orders = [
        SchedulingOrder(
            order_id="WO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        )
    ]

    result = validate_master_data(
        resources=resources,
        routings=routings,
        orders=orders,
        inventory_buffers=[],
        calendar_timezone=None,
    )

    assert result.is_valid is False
    assert {
        "Severity": result.issues[0].severity,
        "Code": result.issues[0].code,
        "Message": result.issues[0].message,
        "Field": result.issues[0].field,
    } == {
        "Severity": "Error",
        "Code": "UNKNOWN_OPERATION_ALTERNATE_RESOURCE",
        "Message": "Operation CUT references missing alternate resource WC-MISSING.",
        "Field": "Routings.FG-A.PRIMARY.Operations.CUT.AlternateResourceIDs",
    }
