from datetime import date, datetime, time, timezone

from sdbr.planner_workbench import (
    MaintenanceWindow,
    Operation,
    Resource,
    Shift,
    Routing,
    SchedulingOrder,
    WorkCalendar,
    build_planner_workbench,
    calculate_suggested_release_date,
    calculate_working_capacity_minutes,
    create_scheduling_backend,
    export_simio_operation_rows,
    evaluate_release_decision,
)


def test_workbench_flags_drum_resource_overload_by_day():
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
                duration_minutes=300,
                sequence=1,
            )
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
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        ),
    ]

    workbench = build_planner_workbench(
        orders=orders,
        resources=[resource],
        routings=[routing],
    )

    bucket = workbench.load_buckets[0]
    assert bucket.resource_id == "WC-DRUM"
    assert bucket.bucket_date == date(2026, 6, 16)
    assert bucket.required_minutes == 600
    assert bucket.capacity_minutes == 480
    assert bucket.overload_minutes == 120
    assert bucket.is_constraint is True
    assert workbench.overloaded_constraints == ["WC-DRUM"]


def test_suggested_release_date_uses_routing_time_and_time_buffer():
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=480,
                sequence=1,
            ),
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=240,
                sequence=2,
            ),
        ],
    )
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )

    release_date = calculate_suggested_release_date(
        order=order,
        routing=routing,
        time_buffer_minutes=720,
    )

    assert release_date == datetime(2026, 6, 19, 8, tzinfo=timezone.utc)


def test_scheduling_backends_expose_ortools_gurobi_and_simio_interfaces():
    assert create_scheduling_backend("ortools").backend_id == "ortools"
    assert create_scheduling_backend("gurobi").backend_id == "gurobi"
    assert create_scheduling_backend("simio").backend_id == "simio"

    simio = create_scheduling_backend("simio")
    assert simio.export_format == "operation_rows"


def test_workbench_includes_order_release_recommendations():
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
                duration_minutes=480,
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

    workbench = build_planner_workbench(
        orders=[order],
        resources=[resource],
        routings=[routing],
        time_buffer_minutes=720,
    )

    recommendation = workbench.release_recommendations[0]
    assert recommendation.order_id == "WO-1"
    assert recommendation.suggested_release_date == datetime(
        2026,
        6,
        19,
        12,
        tzinfo=timezone.utc,
    )


def test_release_decision_blocks_before_suggested_release_date():
    decision = evaluate_release_decision(
        order_id="WO-1",
        requested_release_at=datetime(2026, 6, 19, 8, tzinfo=timezone.utc),
        suggested_release_at=datetime(2026, 6, 19, 12, tzinfo=timezone.utc),
    )

    assert decision.allowed is False
    assert decision.status == "ReleaseBlocked"
    assert decision.message == "Hold release until rope date."
    assert decision.minutes_early == 240


def test_release_decision_allows_on_or_after_suggested_release_date():
    decision = evaluate_release_decision(
        order_id="WO-1",
        requested_release_at=datetime(2026, 6, 19, 12, tzinfo=timezone.utc),
        suggested_release_at=datetime(2026, 6, 19, 12, tzinfo=timezone.utc),
    )

    assert decision.allowed is True
    assert decision.status == "ReleaseAllowed"
    assert decision.minutes_early == 0


def test_workbench_groups_load_graph_rows_by_resource_and_date():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={
                date(2026, 6, 16): 480,
                date(2026, 6, 17): 480,
            },
        ),
        Resource(
            resource_id="WC-ASM",
            name="Assembly",
            is_constraint=False,
            daily_capacity_minutes={
                date(2026, 6, 16): 480,
                date(2026, 6, 17): 480,
            },
        ),
    ]
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=300,
                sequence=1,
            ),
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=120,
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
            quantity=2,
            due_date=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 17),
        ),
    ]

    workbench = build_planner_workbench(
        orders=orders,
        resources=resources,
        routings=[routing],
    )

    drum_row = workbench.load_graph_rows[0]
    assert drum_row.resource_id == "WC-DRUM"
    assert drum_row.resource_name == "Constraint Cutter"
    assert drum_row.is_constraint is True
    assert [cell.bucket_date for cell in drum_row.cells] == [
        date(2026, 6, 16),
        date(2026, 6, 17),
    ]
    assert [cell.required_minutes for cell in drum_row.cells] == [300, 600]
    assert [cell.load_percent for cell in drum_row.cells] == [62.5, 125.0]


def test_non_constraint_overload_is_visible_but_not_a_finite_capacity_violation():
    resource = Resource(
        resource_id="WC-ASM",
        name="Assembly",
        is_constraint=False,
        daily_capacity_minutes={date(2026, 6, 16): 480},
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=600,
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

    workbench = build_planner_workbench(
        orders=[order],
        resources=[resource],
        routings=[routing],
    )

    bucket = workbench.load_buckets[0]
    assert bucket.overload_minutes == 120
    assert bucket.is_constraint is False
    assert bucket.capacity_mode == "Infinite"
    assert workbench.overloaded_constraints == []


def test_simio_export_flattens_orders_and_routings_to_operation_rows():
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=300,
                sequence=1,
            ),
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=120,
                sequence=2,
            ),
        ],
    )
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=2,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )

    rows = export_simio_operation_rows(orders=[order], routings=[routing])

    assert rows == [
        {
            "OrderID": "WO-1",
            "ProductID": "FG-A",
            "OperationID": "CUT",
            "Sequence": 1,
            "ResourceID": "WC-DRUM",
            "DurationMinutes": 600,
            "TargetStartDate": "2026-06-16",
            "DueDate": "2026-06-20T08:00:00+00:00",
        },
        {
            "OrderID": "WO-1",
            "ProductID": "FG-A",
            "OperationID": "ASM",
            "Sequence": 2,
            "ResourceID": "WC-ASM",
            "DurationMinutes": 240,
            "TargetStartDate": "2026-06-16",
            "DueDate": "2026-06-20T08:00:00+00:00",
        },
    ]


def test_work_calendar_capacity_subtracts_maintenance_windows():
    calendar = WorkCalendar(
        calendar_id="CAL-2SHIFT",
        working_weekdays={0, 1, 2, 3, 4},
        shifts=[
            Shift(name="Day", start=time(8, 0), end=time(16, 0)),
            Shift(name="Evening", start=time(16, 0), end=time(20, 0)),
        ],
        maintenance_windows=[
            MaintenanceWindow(
                start=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
                end=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            )
        ],
    )

    capacity = calculate_working_capacity_minutes(
        calendar=calendar,
        target_date=date(2026, 6, 16),
        tzinfo=timezone.utc,
    )

    assert capacity == 600


def test_workbench_uses_resource_calendar_capacity_when_available():
    calendar = WorkCalendar(
        calendar_id="CAL-DAY",
        working_weekdays={0, 1, 2, 3, 4},
        shifts=[Shift(name="Day", start=time(8, 0), end=time(16, 0))],
        maintenance_windows=[],
    )
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={},
        calendar=calendar,
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=500,
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

    workbench = build_planner_workbench(
        orders=[order],
        resources=[resource],
        routings=[routing],
        calendar_tzinfo=timezone.utc,
    )

    bucket = workbench.load_buckets[0]
    assert bucket.capacity_minutes == 480
    assert bucket.overload_minutes == 20


def test_work_calendar_treats_configured_holidays_as_zero_capacity():
    calendar = WorkCalendar(
        calendar_id="CAL-HOLIDAY",
        working_weekdays={0, 1, 2, 3, 4},
        shifts=[Shift(name="Day", start=time(8, 0), end=time(16, 0))],
        maintenance_windows=[],
        holidays={date(2026, 6, 16)},
    )

    capacity = calculate_working_capacity_minutes(
        calendar=calendar,
        target_date=date(2026, 6, 16),
        tzinfo=timezone.utc,
    )

    assert capacity == 0


def test_workbench_suggests_alternate_routing_when_primary_route_overloads_constraint():
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

    workbench = build_planner_workbench(
        orders=[order],
        resources=resources,
        routings=[primary, alternate],
    )

    assert len(workbench.alternate_route_suggestions) == 1
    suggestion = workbench.alternate_route_suggestions[0]
    assert suggestion.order_id == "WO-ALT"
    assert suggestion.current_routing_id == "PRIMARY"
    assert suggestion.alternate_routing_id == "ALT-LASER"
    assert suggestion.relief_resource_id == "WC-DRUM"
    assert suggestion.relief_minutes == 500
    assert suggestion.added_resource_id == "WC-LASER"
    assert suggestion.added_minutes == 420


def test_workbench_does_not_suggest_alternate_routing_that_uses_same_overloaded_constraint():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 480},
    )
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
        routing_id="ALT-SAME-DRUM",
        is_primary=False,
        operations=[
            Operation(
                operation_id="CUT-ALT",
                resource_id="WC-DRUM",
                duration_minutes=450,
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

    workbench = build_planner_workbench(
        orders=[order],
        resources=[resource],
        routings=[primary, alternate],
    )

    assert workbench.alternate_route_suggestions == []
