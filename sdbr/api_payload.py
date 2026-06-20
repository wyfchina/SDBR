from __future__ import annotations

from datetime import date, datetime, timezone

from sdbr.planner_view import build_planner_workbench_view, planner_workbench_view_to_dict
from sdbr.planner_workbench import Operation, Resource, Routing, SchedulingOrder


def get_planner_workbench_demo_payload(
    generated_at: datetime | None = None,
    solver_backend_id: str = "baseline-finite",
) -> dict[str, object]:
    generated_at = generated_at or datetime.now(timezone.utc)
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
        Resource(
            resource_id="WC-ASM",
            name="Assembly",
            is_constraint=False,
            daily_capacity_minutes={date(2026, 6, 16): 480},
        ),
    ]
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=180,
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
            order_id="WO-DEMO-1",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        ),
        SchedulingOrder(
            order_id="WO-DEMO-2",
            product_id="FG-A",
            quantity=1,
            due_date=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
            target_start_date=date(2026, 6, 16),
        ),
    ]
    view = build_planner_workbench_view(
        problem_id="DEMO-WORKBENCH",
        orders=orders,
        resources=resources,
        routings=[routing],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        generated_at=generated_at,
        solver_backend_id=solver_backend_id,
    )
    return {
        "Endpoint": "/planner/workbench/demo",
        "StatusCode": 200,
        "Data": planner_workbench_view_to_dict(view),
    }
