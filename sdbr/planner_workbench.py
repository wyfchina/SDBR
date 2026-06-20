from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo as TzInfo


@dataclass(frozen=True, slots=True)
class Resource:
    resource_id: str
    name: str
    is_constraint: bool
    daily_capacity_minutes: dict[date, int]
    calendar: WorkCalendar | None = None
    capacity_units: int = 1
    efficiency_percent: int = 100
    resource_type: str | None = None
    is_buffered: bool = False
    owner_id: str | None = None
    category: str | None = None


@dataclass(frozen=True, slots=True)
class Shift:
    name: str
    start: time
    end: time


@dataclass(frozen=True, slots=True)
class MaintenanceWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class WorkCalendar:
    calendar_id: str
    working_weekdays: set[int]
    shifts: list[Shift]
    maintenance_windows: list[MaintenanceWindow]
    holidays: set[date] | None = None


@dataclass(frozen=True, slots=True)
class Operation:
    operation_id: str
    resource_id: str
    duration_minutes: int
    sequence: int
    alternate_resource_ids: list[str] | None = None
    setup_family: str | None = None
    earliest_start_at: datetime | None = None
    latest_end_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Routing:
    product_id: str
    operations: list[Operation]
    routing_id: str = "PRIMARY"
    is_primary: bool = True


@dataclass(frozen=True, slots=True)
class SchedulingOrder:
    order_id: str
    product_id: str
    quantity: float
    due_date: datetime
    target_start_date: date


@dataclass(frozen=True, slots=True)
class LoadBucket:
    resource_id: str
    bucket_date: date
    required_minutes: int
    capacity_minutes: int
    overload_minutes: int
    is_constraint: bool
    capacity_mode: str


@dataclass(frozen=True, slots=True)
class ReleaseRecommendation:
    order_id: str
    suggested_release_date: datetime


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    order_id: str
    allowed: bool
    status: str
    message: str
    requested_release_at: datetime
    suggested_release_at: datetime
    minutes_early: int


@dataclass(frozen=True, slots=True)
class LoadGraphCell:
    bucket_date: date
    required_minutes: int
    capacity_minutes: int
    overload_minutes: int
    load_percent: float


@dataclass(frozen=True, slots=True)
class LoadGraphRow:
    resource_id: str
    resource_name: str
    is_constraint: bool
    cells: list[LoadGraphCell]


@dataclass(frozen=True, slots=True)
class AlternateRouteSuggestion:
    order_id: str
    current_routing_id: str
    alternate_routing_id: str
    relief_resource_id: str
    relief_minutes: int
    added_resource_id: str
    added_minutes: int


@dataclass(frozen=True, slots=True)
class PlannerWorkbench:
    load_buckets: list[LoadBucket]
    overloaded_constraints: list[str]
    release_recommendations: list[ReleaseRecommendation]
    load_graph_rows: list[LoadGraphRow]
    alternate_route_suggestions: list[AlternateRouteSuggestion]


@dataclass(frozen=True, slots=True)
class SchedulingBackend:
    backend_id: str
    export_format: str | None = None


def build_planner_workbench(
    orders: list[SchedulingOrder],
    resources: list[Resource],
    routings: list[Routing],
    time_buffer_minutes: int = 0,
    calendar_tzinfo: TzInfo | None = None,
) -> PlannerWorkbench:
    resources_by_id = {resource.resource_id: resource for resource in resources}
    routings_by_product = _primary_routings_by_product(routings)
    required_by_resource_day: dict[tuple[str, date], int] = {}

    for order in orders:
        routing = routings_by_product[order.product_id]
        for operation in routing.operations:
            key = (operation.resource_id, order.target_start_date)
            required_by_resource_day[key] = required_by_resource_day.get(key, 0) + int(
                operation.duration_minutes * order.quantity
            )

    load_buckets = []
    for (resource_id, bucket_date), required_minutes in sorted(required_by_resource_day.items()):
        resource = resources_by_id[resource_id]
        capacity_minutes = _capacity_minutes_for(resource, bucket_date, calendar_tzinfo)
        overload_minutes = max(0, required_minutes - capacity_minutes)
        load_buckets.append(
            LoadBucket(
                resource_id=resource_id,
                bucket_date=bucket_date,
                required_minutes=required_minutes,
                capacity_minutes=capacity_minutes,
                overload_minutes=overload_minutes,
                is_constraint=resource.is_constraint,
                capacity_mode="Finite" if resource.is_constraint else "Infinite",
            )
        )

    overloaded_constraints = [
        bucket.resource_id
        for bucket in load_buckets
        if bucket.is_constraint and bucket.overload_minutes > 0
    ]
    release_recommendations = [
        ReleaseRecommendation(
            order_id=order.order_id,
            suggested_release_date=calculate_suggested_release_date(
                order=order,
                routing=routings_by_product[order.product_id],
                time_buffer_minutes=time_buffer_minutes,
            ),
        )
        for order in orders
    ]
    bucket_by_resource_day = {
        (bucket.resource_id, bucket.bucket_date): bucket
        for bucket in load_buckets
    }
    bucket_dates = sorted({order.target_start_date for order in orders})
    load_graph_rows = []
    for resource in sorted(resources, key=lambda item: (not item.is_constraint, item.resource_id)):
        cells = []
        for bucket_date in bucket_dates:
            bucket = bucket_by_resource_day.get((resource.resource_id, bucket_date))
            capacity_minutes = _capacity_minutes_for(resource, bucket_date, calendar_tzinfo)
            required_minutes = bucket.required_minutes if bucket else 0
            overload_minutes = max(0, required_minutes - capacity_minutes)
            load_percent = 0.0
            if capacity_minutes > 0:
                load_percent = round((required_minutes / capacity_minutes) * 100, 2)
            cells.append(
                LoadGraphCell(
                    bucket_date=bucket_date,
                    required_minutes=required_minutes,
                    capacity_minutes=capacity_minutes,
                    overload_minutes=overload_minutes,
                    load_percent=load_percent,
                )
            )
        load_graph_rows.append(
            LoadGraphRow(
                resource_id=resource.resource_id,
                resource_name=resource.name,
                is_constraint=resource.is_constraint,
                cells=cells,
            )
        )
    alternate_route_suggestions = _alternate_route_suggestions(
        orders=orders,
        routings=routings,
        primary_routings_by_product=routings_by_product,
        overloaded_constraints=set(overloaded_constraints),
    )
    return PlannerWorkbench(
        load_buckets=load_buckets,
        overloaded_constraints=overloaded_constraints,
        release_recommendations=release_recommendations,
        load_graph_rows=load_graph_rows,
        alternate_route_suggestions=alternate_route_suggestions,
    )


def calculate_working_capacity_minutes(
    calendar: WorkCalendar,
    target_date: date,
    tzinfo: TzInfo,
) -> int:
    if calendar.holidays is not None and target_date in calendar.holidays:
        return 0
    if target_date.weekday() not in calendar.working_weekdays:
        return 0

    shift_windows = [
        (
            datetime.combine(target_date, shift.start, tzinfo=tzinfo),
            datetime.combine(target_date, shift.end, tzinfo=tzinfo),
        )
        for shift in calendar.shifts
    ]
    capacity = sum(
        int((shift_end - shift_start).total_seconds() / 60)
        for shift_start, shift_end in shift_windows
    )

    maintenance_minutes = 0
    for maintenance in calendar.maintenance_windows:
        for shift_start, shift_end in shift_windows:
            overlap_start = max(shift_start, maintenance.start)
            overlap_end = min(shift_end, maintenance.end)
            if overlap_start < overlap_end:
                maintenance_minutes += int((overlap_end - overlap_start).total_seconds() / 60)

    return max(0, capacity - maintenance_minutes)


def _capacity_minutes_for(
    resource: Resource,
    bucket_date: date,
    calendar_tzinfo: TzInfo | None,
) -> int:
    if resource.calendar is not None:
        if calendar_tzinfo is None:
            raise ValueError("calendar_tzinfo is required when resource calendars are used")
        return calculate_working_capacity_minutes(
            calendar=resource.calendar,
            target_date=bucket_date,
            tzinfo=calendar_tzinfo,
        )
    return resource.daily_capacity_minutes.get(bucket_date, 0)


def calculate_suggested_release_date(
    order: SchedulingOrder,
    routing: Routing,
    time_buffer_minutes: int,
) -> datetime:
    routing_minutes = sum(
        int(operation.duration_minutes * order.quantity)
        for operation in routing.operations
    )
    rope_minutes = routing_minutes + time_buffer_minutes
    return order.due_date - timedelta(minutes=rope_minutes)


def evaluate_release_decision(
    order_id: str,
    requested_release_at: datetime,
    suggested_release_at: datetime,
) -> ReleaseDecision:
    minutes_early = max(0, int((suggested_release_at - requested_release_at).total_seconds() / 60))
    if minutes_early > 0:
        return ReleaseDecision(
            order_id=order_id,
            allowed=False,
            status="ReleaseBlocked",
            message="Hold release until rope date.",
            requested_release_at=requested_release_at,
            suggested_release_at=suggested_release_at,
            minutes_early=minutes_early,
        )
    return ReleaseDecision(
        order_id=order_id,
        allowed=True,
        status="ReleaseAllowed",
        message="Release is inside rope window.",
        requested_release_at=requested_release_at,
        suggested_release_at=suggested_release_at,
        minutes_early=0,
    )


def create_scheduling_backend(backend_id: str) -> SchedulingBackend:
    normalized = backend_id.lower()
    if normalized == "ortools":
        return SchedulingBackend(backend_id="ortools")
    if normalized == "gurobi":
        return SchedulingBackend(backend_id="gurobi")
    if normalized == "simio":
        return SchedulingBackend(
            backend_id="simio",
            export_format="operation_rows",
        )
    raise ValueError(f"Unsupported scheduling backend: {backend_id}")


def export_simio_operation_rows(
    orders: list[SchedulingOrder],
    routings: list[Routing],
) -> list[dict[str, object]]:
    routings_by_product = {routing.product_id: routing for routing in routings}
    rows = []
    for order in orders:
        routing = routings_by_product[order.product_id]
        for operation in sorted(routing.operations, key=lambda item: item.sequence):
            rows.append(
                {
                    "OrderID": order.order_id,
                    "ProductID": order.product_id,
                    "OperationID": operation.operation_id,
                    "Sequence": operation.sequence,
                    "ResourceID": operation.resource_id,
                    "DurationMinutes": int(operation.duration_minutes * order.quantity),
                    "TargetStartDate": order.target_start_date.isoformat(),
                    "DueDate": order.due_date.isoformat(),
                }
            )
    return rows


def _primary_routings_by_product(routings: list[Routing]) -> dict[str, Routing]:
    result = {}
    for routing in routings:
        if routing.is_primary or routing.product_id not in result:
            result[routing.product_id] = routing
    return result


def _alternate_route_suggestions(
    orders: list[SchedulingOrder],
    routings: list[Routing],
    primary_routings_by_product: dict[str, Routing],
    overloaded_constraints: set[str],
) -> list[AlternateRouteSuggestion]:
    alternatives_by_product: dict[str, list[Routing]] = {}
    for routing in routings:
        if not routing.is_primary:
            alternatives_by_product.setdefault(routing.product_id, []).append(routing)

    suggestions = []
    for order in orders:
        primary = primary_routings_by_product[order.product_id]
        constrained_resources = {
            operation.resource_id
            for operation in primary.operations
            if operation.resource_id in overloaded_constraints
        }
        if not constrained_resources:
            continue
        for alternate in alternatives_by_product.get(order.product_id, []):
            alternate_resources = {operation.resource_id for operation in alternate.operations}
            for resource_id in sorted(constrained_resources):
                if resource_id not in alternate_resources:
                    added_resource_id = sorted(alternate_resources)[0]
                    suggestions.append(
                        AlternateRouteSuggestion(
                            order_id=order.order_id,
                            current_routing_id=primary.routing_id,
                            alternate_routing_id=alternate.routing_id,
                            relief_resource_id=resource_id,
                            relief_minutes=_routing_minutes_for_resource(
                                routing=primary,
                                resource_id=resource_id,
                                quantity=order.quantity,
                            ),
                            added_resource_id=added_resource_id,
                            added_minutes=_routing_minutes_for_resource(
                                routing=alternate,
                                resource_id=added_resource_id,
                                quantity=order.quantity,
                            ),
                        )
                    )
    return suggestions


def _routing_minutes_for_resource(
    routing: Routing,
    resource_id: str,
    quantity: float,
) -> int:
    return sum(
        int(operation.duration_minutes * quantity)
        for operation in routing.operations
        if operation.resource_id == resource_id
    )
