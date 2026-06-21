from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo as TzInfo

from sdbr.gantt_view import GanttRow, build_gantt_rows
from sdbr.planner_workbench import (
    AlternateRouteSuggestion,
    LoadGraphRow,
    ReleaseRecommendation,
    Resource,
    Routing,
    SchedulingOrder,
    build_planner_workbench,
)
from sdbr.release_policy import effective_rope_buffer_minutes
from sdbr.scheduling_solver import (
    BaselineFiniteScheduler,
    FixedOperationAssignment,
    SchedulingObjective,
    SolverDiagnostic,
    SetupTransition,
    build_capacity_buckets_from_resources,
    build_resource_inputs,
    build_scheduling_problem,
)
from sdbr.scheduling_solver import create_solver_engine


@dataclass(frozen=True, slots=True)
class PlannerWorkbenchView:
    generated_at: datetime | None
    solver_backend_id: str
    solver_status: str
    solver_message: str
    solver_diagnostics: list[SolverDiagnostic]
    order_count: int
    constraint_overload_count: int
    load_graph_rows: list[LoadGraphRow]
    gantt_rows: list[GanttRow]
    release_recommendations: list[ReleaseRecommendation]
    buffer_board: list[BufferBoardItem]
    buffer_summary: BufferSummary
    execution_priority_queue: list[ExecutionPriorityItem]
    alternate_route_suggestions: list[AlternateRouteSuggestion]
    bottleneck_candidates: list[BottleneckCandidate]
    capacity_buffer_board: list[CapacityBufferItem]
    inventory_buffer_board: list[InventoryBufferItem]


@dataclass(frozen=True, slots=True)
class BufferBoardItem:
    order_id: str
    zone: str
    suggested_release_date: datetime
    target_start_date: date


@dataclass(frozen=True, slots=True)
class BufferSummary:
    red_count: int
    yellow_count: int
    green_count: int
    has_critical_alert: bool
    highest_severity: str


@dataclass(frozen=True, slots=True)
class ExecutionPriorityItem:
    rank: int
    order_id: str
    zone: str
    priority_reason: str
    recommended_action: str
    suggested_release_date: datetime


@dataclass(frozen=True, slots=True)
class BottleneckCandidate:
    resource_id: str
    resource_name: str
    overloaded_bucket_count: int
    max_load_percent: float
    total_overload_minutes: int
    recommendation: str


@dataclass(frozen=True, slots=True)
class CapacityBufferItem:
    resource_id: str
    resource_name: str
    capacity_minutes: int
    required_minutes: int
    sprint_capacity_minutes: int
    overload_minutes: int
    load_percent: float
    status: str
    recommendation: str


@dataclass(frozen=True, slots=True)
class InventoryBufferPolicy:
    item_id: str
    location_id: str
    on_hand_qty: float
    red_zone_qty: float
    yellow_zone_qty: float
    green_zone_qty: float


@dataclass(frozen=True, slots=True)
class InventoryBufferItem:
    item_id: str
    location_id: str
    on_hand_qty: float
    red_zone_qty: float
    yellow_zone_qty: float
    green_zone_qty: float
    zone: str
    penetration_percent: float
    recommended_action: str


def build_planner_workbench_view(
    problem_id: str,
    orders: list[SchedulingOrder],
    resources: list[Resource],
    routings: list[Routing],
    schedule_start_at: datetime,
    time_buffer_minutes: int = 0,
    calendar_tzinfo: TzInfo | None = None,
    solver_backend_id: str = "baseline-finite",
    generated_at: datetime | None = None,
    inventory_buffers: list[InventoryBufferPolicy] | None = None,
    solver_time_limit_seconds: float | None = None,
    fixed_assignments: list[FixedOperationAssignment] | None = None,
    setup_transitions: list[SetupTransition] | None = None,
    objective: SchedulingObjective | None = None,
    align_release_to_schedule: bool = False,
    release_policy: dict[str, object] | None = None,
) -> PlannerWorkbenchView:
    effective_time_buffer_minutes = effective_rope_buffer_minutes(
        release_policy=release_policy,
        fallback_time_buffer_minutes=time_buffer_minutes,
    )
    workbench = build_planner_workbench(
        orders=orders,
        resources=resources,
        routings=routings,
        time_buffer_minutes=effective_time_buffer_minutes,
        calendar_tzinfo=calendar_tzinfo,
    )
    problem = build_scheduling_problem(
        problem_id=problem_id,
        orders=orders,
        routings=routings,
        resource_inputs=build_resource_inputs(resources),
        capacity_buckets=build_capacity_buckets_from_resources(
            resources,
            schedule_start_at.tzinfo,
        ),
        schedule_start_at=schedule_start_at,
        time_buffer_minutes=effective_time_buffer_minutes,
        solver_time_limit_seconds=solver_time_limit_seconds,
        fixed_assignments=fixed_assignments,
        setup_transitions=setup_transitions,
        objective=objective,
    )
    if solver_backend_id == "baseline-finite":
        schedule = BaselineFiniteScheduler().solve(
            problem=problem,
            start_at=schedule_start_at,
        )
    else:
        schedule = create_solver_engine(solver_backend_id).solve(problem)
    release_recommendations = workbench.release_recommendations
    if align_release_to_schedule:
        release_recommendations = release_recommendations_aligned_to_schedule(
            fallback_recommendations=workbench.release_recommendations,
            schedule_assignments=schedule.assignments,
            time_buffer_minutes=effective_time_buffer_minutes,
        )
    buffer_board = build_buffer_board(
        orders=orders,
        release_recommendations=release_recommendations,
        generated_at=generated_at or schedule_start_at,
    )
    return PlannerWorkbenchView(
        generated_at=generated_at,
        solver_backend_id=schedule.backend_id,
        solver_status=schedule.status,
        solver_message=schedule.message,
        solver_diagnostics=schedule.diagnostics,
        order_count=len(orders),
        constraint_overload_count=len(workbench.overloaded_constraints),
        load_graph_rows=workbench.load_graph_rows,
        gantt_rows=build_gantt_rows(schedule) if schedule.assignments else [],
        release_recommendations=release_recommendations,
        buffer_board=buffer_board,
        buffer_summary=build_buffer_summary(buffer_board),
        execution_priority_queue=build_execution_priority_queue(buffer_board),
        alternate_route_suggestions=workbench.alternate_route_suggestions,
        bottleneck_candidates=build_bottleneck_candidates(workbench.load_graph_rows),
        capacity_buffer_board=build_capacity_buffer_board(workbench.load_graph_rows),
        inventory_buffer_board=build_inventory_buffer_board(inventory_buffers or []),
    )


def release_recommendations_aligned_to_schedule(
    *,
    fallback_recommendations: list[ReleaseRecommendation],
    schedule_assignments: list[object],
    time_buffer_minutes: int,
) -> list[ReleaseRecommendation]:
    first_start_by_order: dict[str, datetime] = {}
    for assignment in schedule_assignments:
        order_id = str(getattr(assignment, "order_id", ""))
        start = getattr(assignment, "start", None)
        if not order_id or not isinstance(start, datetime):
            continue
        current = first_start_by_order.get(order_id)
        if current is None or start < current:
            first_start_by_order[order_id] = start
    if not first_start_by_order:
        return fallback_recommendations
    aligned = []
    for recommendation in fallback_recommendations:
        scheduled_start = first_start_by_order.get(recommendation.order_id)
        if scheduled_start is None:
            aligned.append(recommendation)
            continue
        aligned.append(
            ReleaseRecommendation(
                order_id=recommendation.order_id,
                suggested_release_date=scheduled_start
                - timedelta(minutes=time_buffer_minutes),
            )
        )
    return aligned


def build_buffer_board(
    orders: list[SchedulingOrder],
    release_recommendations: list[ReleaseRecommendation],
    generated_at: datetime,
) -> list[BufferBoardItem]:
    orders_by_id = {order.order_id: order for order in orders}
    items = [
        BufferBoardItem(
            order_id=recommendation.order_id,
            zone=_buffer_zone(
                generated_at=generated_at,
                suggested_release_date=recommendation.suggested_release_date,
                target_start_date=orders_by_id[recommendation.order_id].target_start_date,
            ),
            suggested_release_date=recommendation.suggested_release_date,
            target_start_date=orders_by_id[recommendation.order_id].target_start_date,
        )
        for recommendation in release_recommendations
    ]
    zone_rank = {"Red": 0, "Yellow": 1, "Green": 2}
    return sorted(
        items,
        key=lambda item: (
            zone_rank[item.zone],
            item.suggested_release_date,
            item.order_id,
        ),
    )


def build_buffer_summary(buffer_board: list[BufferBoardItem]) -> BufferSummary:
    red_count = sum(1 for item in buffer_board if item.zone == "Red")
    yellow_count = sum(1 for item in buffer_board if item.zone == "Yellow")
    green_count = sum(1 for item in buffer_board if item.zone == "Green")
    highest_severity = "None"
    if red_count > 0:
        highest_severity = "Red"
    elif yellow_count > 0:
        highest_severity = "Yellow"
    elif green_count > 0:
        highest_severity = "Green"
    return BufferSummary(
        red_count=red_count,
        yellow_count=yellow_count,
        green_count=green_count,
        has_critical_alert=red_count > 0,
        highest_severity=highest_severity,
    )


def build_execution_priority_queue(
    buffer_board: list[BufferBoardItem],
) -> list[ExecutionPriorityItem]:
    return [
        ExecutionPriorityItem(
            rank=index + 1,
            order_id=item.order_id,
            zone=item.zone,
            priority_reason=_priority_reason(item.zone),
            recommended_action=_recommended_action(item.zone),
            suggested_release_date=item.suggested_release_date,
        )
        for index, item in enumerate(buffer_board)
    ]


def build_bottleneck_candidates(load_graph_rows: list[LoadGraphRow]) -> list[BottleneckCandidate]:
    candidates = []
    for row in load_graph_rows:
        if row.is_constraint:
            continue
        overloaded_cells = [cell for cell in row.cells if cell.overload_minutes > 0]
        if len(overloaded_cells) < 2:
            continue
        candidates.append(
            BottleneckCandidate(
                resource_id=row.resource_id,
                resource_name=row.resource_name,
                overloaded_bucket_count=len(overloaded_cells),
                max_load_percent=max(cell.load_percent for cell in overloaded_cells),
                total_overload_minutes=sum(cell.overload_minutes for cell in overloaded_cells),
                recommendation="Review as new constraint candidate",
            )
        )
    return sorted(
        candidates,
        key=lambda item: (-item.overloaded_bucket_count, -item.total_overload_minutes, item.resource_id),
    )


def build_capacity_buffer_board(load_graph_rows: list[LoadGraphRow]) -> list[CapacityBufferItem]:
    items = []
    for row in load_graph_rows:
        if row.is_constraint:
            continue
        capacity_minutes = sum(cell.capacity_minutes for cell in row.cells)
        required_minutes = sum(cell.required_minutes for cell in row.cells)
        overload_minutes = sum(cell.overload_minutes for cell in row.cells)
        sprint_capacity_minutes = max(0, capacity_minutes - required_minutes)
        load_percent = 0.0
        if capacity_minutes > 0:
            load_percent = round(required_minutes / capacity_minutes * 100, 2)
        status = _capacity_buffer_status(
            overload_minutes=overload_minutes,
            load_percent=load_percent,
        )
        items.append(
            CapacityBufferItem(
                resource_id=row.resource_id,
                resource_name=row.resource_name,
                capacity_minutes=capacity_minutes,
                required_minutes=required_minutes,
                sprint_capacity_minutes=sprint_capacity_minutes,
                overload_minutes=overload_minutes,
                load_percent=load_percent,
                status=status,
                recommendation=_capacity_buffer_recommendation(status),
            )
        )
    return sorted(
        items,
        key=lambda item: (
            _capacity_buffer_status_rank(item.status),
            -item.overload_minutes,
            item.sprint_capacity_minutes,
            item.resource_id,
        ),
    )


def build_inventory_buffer_board(
    policies: list[InventoryBufferPolicy],
) -> list[InventoryBufferItem]:
    return sorted(
        [
            InventoryBufferItem(
                item_id=policy.item_id,
                location_id=policy.location_id,
                on_hand_qty=float(policy.on_hand_qty),
                red_zone_qty=float(policy.red_zone_qty),
                yellow_zone_qty=float(policy.yellow_zone_qty),
                green_zone_qty=float(policy.green_zone_qty),
                zone=_inventory_zone(policy),
                penetration_percent=_inventory_penetration_percent(policy),
                recommended_action=_inventory_recommended_action(_inventory_zone(policy)),
            )
            for policy in policies
        ],
        key=lambda item: (_inventory_zone_rank(item.zone), item.item_id, item.location_id),
    )


def _priority_reason(zone: str) -> str:
    if zone == "Red":
        return "Red buffer penetration"
    if zone == "Yellow":
        return "Inside release window"
    return "Not ready for release"


def _recommended_action(zone: str) -> str:
    if zone == "Red":
        return "Expedite to constraint"
    if zone == "Yellow":
        return "Release now"
    return "Hold release"


def _inventory_zone(policy: InventoryBufferPolicy) -> str:
    if policy.on_hand_qty <= policy.red_zone_qty:
        return "Red"
    if policy.on_hand_qty <= policy.yellow_zone_qty:
        return "Yellow"
    return "Green"


def _inventory_penetration_percent(policy: InventoryBufferPolicy) -> float:
    if policy.on_hand_qty > policy.yellow_zone_qty:
        return 0.0
    if policy.red_zone_qty <= 0:
        return 100.0
    return round(max(0.0, policy.on_hand_qty / policy.red_zone_qty * 100), 2)


def _inventory_recommended_action(zone: str) -> str:
    if zone == "Red":
        return "Expedite replenishment"
    if zone == "Yellow":
        return "Release replenishment order"
    return "Maintain buffer"


def _inventory_zone_rank(zone: str) -> int:
    return {"Red": 0, "Yellow": 1, "Green": 2}.get(zone, 3)


def _capacity_buffer_status(
    overload_minutes: int,
    load_percent: float,
) -> str:
    if overload_minutes > 0:
        return "Overloaded"
    if load_percent >= 85:
        return "Watch"
    return "Healthy"


def _capacity_buffer_recommendation(status: str) -> str:
    if status == "Overloaded":
        return "Reclassify or offload work"
    if status == "Watch":
        return "Reserve sprint capacity"
    return "Protect sprint capacity"


def _capacity_buffer_status_rank(status: str) -> int:
    return {"Overloaded": 0, "Watch": 1, "Healthy": 2}.get(status, 3)


def _buffer_zone(
    generated_at: datetime,
    suggested_release_date: datetime,
    target_start_date: date,
) -> str:
    target_start_at = datetime.combine(
        target_start_date,
        time.min,
        tzinfo=generated_at.tzinfo,
    )
    if generated_at >= target_start_at:
        return "Red"
    if generated_at >= suggested_release_date:
        return "Yellow"
    return "Green"


def planner_workbench_view_to_dict(view: PlannerWorkbenchView) -> dict[str, object]:
    return {
        "GeneratedAt": view.generated_at.isoformat() if view.generated_at else None,
        "SolverBackendID": view.solver_backend_id,
        "SolverStatus": view.solver_status,
        "SolverMessage": view.solver_message,
        "SolverDiagnostics": [
            {
                "Severity": diagnostic.severity,
                "Code": diagnostic.code,
                "Message": diagnostic.message,
                "EntityID": diagnostic.entity_id,
            }
            for diagnostic in (view.solver_diagnostics or [])
        ],
        "OrderCount": view.order_count,
        "ConstraintOverloadCount": view.constraint_overload_count,
        "LoadGraphRows": [
            {
                "ResourceID": row.resource_id,
                "ResourceName": row.resource_name,
                "IsConstraint": row.is_constraint,
                "Cells": [
                    {
                        "Date": cell.bucket_date.isoformat(),
                        "RequiredMinutes": cell.required_minutes,
                        "CapacityMinutes": cell.capacity_minutes,
                        "OverloadMinutes": cell.overload_minutes,
                        "LoadPercent": cell.load_percent,
                    }
                    for cell in row.cells
                ],
            }
            for row in view.load_graph_rows
        ],
        "GanttRows": [
            {
                "ResourceID": row.resource_id,
                "Bars": [
                    {
                        "OperationID": bar.operation_id,
                        "OrderID": bar.order_id,
                        "Start": bar.start.isoformat(),
                        "End": bar.end.isoformat(),
                        "DurationMinutes": bar.duration_minutes,
                    }
                    for bar in row.bars
                ],
            }
            for row in view.gantt_rows
        ],
        "ReleaseRecommendations": [
            {
                "OrderID": item.order_id,
                "SuggestedReleaseDate": item.suggested_release_date.isoformat(),
            }
            for item in view.release_recommendations
        ],
        "BufferBoard": [
            {
                "OrderID": item.order_id,
                "Zone": item.zone,
                "SuggestedReleaseDate": item.suggested_release_date.isoformat(),
                "TargetStartDate": item.target_start_date.isoformat(),
            }
            for item in view.buffer_board
        ],
        "BufferSummary": {
            "RedCount": view.buffer_summary.red_count,
            "YellowCount": view.buffer_summary.yellow_count,
            "GreenCount": view.buffer_summary.green_count,
            "HasCriticalAlert": view.buffer_summary.has_critical_alert,
            "HighestSeverity": view.buffer_summary.highest_severity,
        },
        "ExecutionPriorityQueue": [
            {
                "Rank": item.rank,
                "OrderID": item.order_id,
                "Zone": item.zone,
                "PriorityReason": item.priority_reason,
                "RecommendedAction": item.recommended_action,
                "SuggestedReleaseDate": item.suggested_release_date.isoformat(),
            }
            for item in view.execution_priority_queue
        ],
        "AlternateRouteSuggestions": [
            {
                "OrderID": item.order_id,
                "CurrentRoutingID": item.current_routing_id,
                "AlternateRoutingID": item.alternate_routing_id,
                "ReliefResourceID": item.relief_resource_id,
                "ReliefMinutes": item.relief_minutes,
                "AddedResourceID": item.added_resource_id,
                "AddedMinutes": item.added_minutes,
            }
            for item in view.alternate_route_suggestions
        ],
        "BottleneckCandidates": [
            {
                "ResourceID": item.resource_id,
                "ResourceName": item.resource_name,
                "OverloadedBucketCount": item.overloaded_bucket_count,
                "MaxLoadPercent": item.max_load_percent,
                "TotalOverloadMinutes": item.total_overload_minutes,
                "Recommendation": item.recommendation,
            }
            for item in view.bottleneck_candidates
        ],
        "CapacityBufferBoard": [
            {
                "ResourceID": item.resource_id,
                "ResourceName": item.resource_name,
                "CapacityMinutes": item.capacity_minutes,
                "RequiredMinutes": item.required_minutes,
                "SprintCapacityMinutes": item.sprint_capacity_minutes,
                "OverloadMinutes": item.overload_minutes,
                "LoadPercent": item.load_percent,
                "Status": item.status,
                "Recommendation": item.recommendation,
            }
            for item in view.capacity_buffer_board
        ],
        "InventoryBufferBoard": [
            {
                "ItemID": item.item_id,
                "LocationID": item.location_id,
                "OnHandQty": item.on_hand_qty,
                "RedZoneQty": item.red_zone_qty,
                "YellowZoneQty": item.yellow_zone_qty,
                "GreenZoneQty": item.green_zone_qty,
                "Zone": item.zone,
                "PenetrationPercent": item.penetration_percent,
                "RecommendedAction": item.recommended_action,
            }
            for item in view.inventory_buffer_board
        ],
    }
