from datetime import date, datetime, timezone

from sdbr.planner_view import (
    InventoryBufferPolicy,
    build_inventory_buffer_board,
    build_planner_workbench_view,
    planner_workbench_view_to_dict,
)
from sdbr.planner_workbench import Operation, Resource, Routing, SchedulingOrder


def test_planner_workbench_view_combines_load_graph_gantt_and_solver_status():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 480},
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=120,
                sequence=1,
            )
        ],
    )
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )

    view = build_planner_workbench_view(
        problem_id="P-VIEW",
        orders=[order],
        resources=[resource],
        routings=[routing],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        generated_at=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
    )

    assert view.solver_backend_id == "baseline-finite"
    assert view.solver_status == "Feasible"
    assert view.order_count == 1
    assert view.constraint_overload_count == 0
    assert view.load_graph_rows[0].resource_id == "WC-DRUM"
    assert view.gantt_rows[0].resource_id == "WC-DRUM"
    assert view.gantt_rows[0].bars[0].operation_id == "WO-1:CUT"

    payload = planner_workbench_view_to_dict(view)

    assert payload["GeneratedAt"] == "2026-06-15T12:00:00+00:00"
    assert payload["SolverBackendID"] == "baseline-finite"
    assert payload["SolverStatus"] == "Feasible"
    assert payload["OrderCount"] == 1
    assert payload["LoadGraphRows"][0]["Cells"][0]["Date"] == "2026-06-16"
    assert payload["GanttRows"][0]["Bars"][0]["Start"] == "2026-06-16T08:00:00+00:00"
    assert payload["GanttRows"][0]["Bars"][0]["DurationMinutes"] == 120
    assert payload["ReleaseRecommendations"] == [
        {
            "OrderID": "WO-1",
            "SuggestedReleaseDate": "2026-06-20T06:00:00+00:00",
        }
    ]


def test_planner_workbench_view_payload_includes_buffer_board_zones():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 480},
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=120,
                sequence=1,
            )
        ],
    )
    orders = [
        SchedulingOrder(
            order_id="WO-GREEN",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 19),
        ),
        SchedulingOrder(
            order_id="WO-YELLOW",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 17),
        ),
        SchedulingOrder(
            order_id="WO-RED",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 17, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 15),
        ),
    ]

    view = build_planner_workbench_view(
        problem_id="P-BUFFER",
        orders=orders,
        resources=[resource],
        routings=[routing],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        generated_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    payload = planner_workbench_view_to_dict(view)

    assert payload["BufferBoard"] == [
        {
            "OrderID": "WO-RED",
            "Zone": "Red",
            "SuggestedReleaseDate": "2026-06-17T06:00:00+00:00",
            "TargetStartDate": "2026-06-15",
        },
        {
            "OrderID": "WO-YELLOW",
            "Zone": "Yellow",
            "SuggestedReleaseDate": "2026-06-16T08:00:00+00:00",
            "TargetStartDate": "2026-06-17",
        },
        {
            "OrderID": "WO-GREEN",
            "Zone": "Green",
            "SuggestedReleaseDate": "2026-06-20T06:00:00+00:00",
            "TargetStartDate": "2026-06-19",
        },
    ]
    assert payload["BufferSummary"] == {
        "RedCount": 1,
        "YellowCount": 1,
        "GreenCount": 1,
        "HasCriticalAlert": True,
        "HighestSeverity": "Red",
    }
    assert payload["ExecutionPriorityQueue"] == [
        {
            "Rank": 1,
            "OrderID": "WO-RED",
            "Zone": "Red",
            "PriorityReason": "Red buffer penetration",
            "RecommendedAction": "Expedite to constraint",
            "SuggestedReleaseDate": "2026-06-17T06:00:00+00:00",
        },
        {
            "Rank": 2,
            "OrderID": "WO-YELLOW",
            "Zone": "Yellow",
            "PriorityReason": "Inside release window",
            "RecommendedAction": "Release now",
            "SuggestedReleaseDate": "2026-06-16T08:00:00+00:00",
        },
        {
            "Rank": 3,
            "OrderID": "WO-GREEN",
            "Zone": "Green",
            "PriorityReason": "Not ready for release",
            "RecommendedAction": "Hold release",
            "SuggestedReleaseDate": "2026-06-20T06:00:00+00:00",
        },
    ]


def test_planner_workbench_view_reports_cp_sat_schedule_with_gantt():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 480},
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=120,
                sequence=1,
            )
        ],
    )
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )

    view = build_planner_workbench_view(
        problem_id="P-VIEW",
        orders=[order],
        resources=[resource],
        routings=[routing],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        solver_backend_id="ortools",
    )

    assert view.solver_backend_id == "ortools"
    assert view.solver_status in {"Optimal", "Feasible"}
    assert view.solver_message == "OR-Tools CP-SAT finite-capacity schedule generated."
    assert view.load_graph_rows[0].resource_id == "WC-DRUM"
    assert view.gantt_rows


def test_planner_workbench_view_payload_includes_alternate_route_suggestions():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
        Resource(
            resource_id="WC-LASER",
            name="Laser Cell",
            is_constraint=False,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
    ]
    primary = Routing(
        product_id="FG-A",
        routing_id="PRIMARY",
        is_primary=True,
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=500,
                sequence=1,
            )
        ],
    )
    alternate = Routing(
        product_id="FG-A",
        routing_id="ALT-LASER",
        is_primary=False,
        operations=[
            Operation(
                operation_id="LASER",
                resource_id="WC-LASER",
                duration_minutes=420,
                sequence=1,
            )
        ],
    )
    order = SchedulingOrder(
        order_id="WO-ALT",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )

    view = build_planner_workbench_view(
        problem_id="P-ALT",
        orders=[order],
        resources=resources,
        routings=[primary, alternate],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    payload = planner_workbench_view_to_dict(view)

    assert payload["AlternateRouteSuggestions"] == [
        {
            "OrderID": "WO-ALT",
            "CurrentRoutingID": "PRIMARY",
            "AlternateRoutingID": "ALT-LASER",
            "ReliefResourceID": "WC-DRUM",
            "ReliefMinutes": 500,
            "AddedResourceID": "WC-LASER",
            "AddedMinutes": 420,
        }
    ]


def test_planner_workbench_view_flags_sustained_non_constraint_overload_as_bottleneck_candidate():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={
                date(2026, 6, 16): 60,
                date(2026, 6, 17): 60,
            },
        ),
        Resource(
            resource_id="WC-PAINT",
            name="Paint Booth",
            is_constraint=False,
            daily_capacity_minutes={
                date(2026, 6, 16): 100,
                date(2026, 6, 17): 100,
            },
        ),
    ]
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=70,
                sequence=1,
            ),
            Operation(
                operation_id="PAINT",
                resource_id="WC-PAINT",
                duration_minutes=150,
                sequence=2,
            ),
        ],
    )
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
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 17),
        ),
    ]

    view = build_planner_workbench_view(
        problem_id="P-BOTTLENECK",
        orders=orders,
        resources=resources,
        routings=[routing],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    payload = planner_workbench_view_to_dict(view)

    assert payload["BottleneckCandidates"] == [
        {
            "ResourceID": "WC-PAINT",
            "ResourceName": "Paint Booth",
            "OverloadedBucketCount": 2,
            "MaxLoadPercent": 150.0,
            "TotalOverloadMinutes": 100,
            "Recommendation": "Review as new constraint candidate",
        }
    ]


def test_planner_workbench_view_payload_includes_capacity_buffer_board_for_non_constraints():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
        Resource(
            resource_id="WC-ASM",
            name="Assembly Cell",
            is_constraint=False,
            daily_capacity_minutes={date(2026, 6, 16): 300},
        ),
        Resource(
            resource_id="WC-PACK",
            name="Packing Cell",
            is_constraint=False,
            daily_capacity_minutes={date(2026, 6, 16): 80},
        ),
    ]
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=60,
                sequence=1,
            ),
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=120,
                sequence=2,
            ),
            Operation(
                operation_id="PACK",
                resource_id="WC-PACK",
                duration_minutes=100,
                sequence=3,
            ),
        ],
    )
    order = SchedulingOrder(
        order_id="WO-CAP",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )

    view = build_planner_workbench_view(
        problem_id="P-CAPACITY-BUFFER",
        orders=[order],
        resources=resources,
        routings=[routing],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    payload = planner_workbench_view_to_dict(view)

    assert payload["CapacityBufferBoard"] == [
        {
            "ResourceID": "WC-PACK",
            "ResourceName": "Packing Cell",
            "CapacityMinutes": 80,
            "RequiredMinutes": 100,
            "SprintCapacityMinutes": 0,
            "OverloadMinutes": 20,
            "LoadPercent": 125.0,
            "Status": "Overloaded",
            "Recommendation": "Reclassify or offload work",
        },
        {
            "ResourceID": "WC-ASM",
            "ResourceName": "Assembly Cell",
            "CapacityMinutes": 300,
            "RequiredMinutes": 120,
            "SprintCapacityMinutes": 180,
            "OverloadMinutes": 0,
            "LoadPercent": 40.0,
            "Status": "Healthy",
            "Recommendation": "Protect sprint capacity",
        },
    ]


def test_inventory_buffer_board_assigns_zones_and_replenishment_actions():
    board = build_inventory_buffer_board(
        [
            InventoryBufferPolicy(
                item_id="RM-STEEL",
                location_id="SUPPLIER-DECOUPLING",
                on_hand_qty=35,
                red_zone_qty=50,
                yellow_zone_qty=120,
                green_zone_qty=200,
            ),
            InventoryBufferPolicy(
                item_id="WIP-KIT",
                location_id="LINE-SUPERMARKET",
                on_hand_qty=160,
                red_zone_qty=40,
                yellow_zone_qty=90,
                green_zone_qty=160,
            ),
        ]
    )

    assert board[0].item_id == "RM-STEEL"
    assert board[0].zone == "Red"
    assert board[0].penetration_percent == 70.0
    assert board[0].recommended_action == "Expedite replenishment"
    assert board[1].item_id == "WIP-KIT"
    assert board[1].zone == "Green"
    assert board[1].penetration_percent == 0.0
    assert board[1].recommended_action == "Maintain buffer"
