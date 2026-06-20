from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, tzinfo as TzInfo
from importlib.util import find_spec
from math import ceil
from typing import Protocol

from sdbr.planner_workbench import Resource, Routing, SchedulingOrder


ACTIVE_SOLVER_BACKEND_ID = "ortools"
PAUSED_SOLVER_BACKEND_IDS = frozenset({"gurobi"})


@dataclass(frozen=True, slots=True)
class SolverAvailability:
    backend_id: str
    available: bool
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class SolverDiagnostic:
    severity: str
    code: str
    message: str
    entity_id: str | None = None


class SchedulingSolver(Protocol):
    backend_id: str

    def is_available(self) -> SolverAvailability:
        ...

    def solve(self, problem: SchedulingProblem) -> SchedulingResult:
        ...


@dataclass(frozen=True, slots=True)
class SchedulingOrderInput:
    order_id: str
    product_id: str
    quantity: float
    due_at: datetime
    protected_due_at: datetime | None = None
    release_not_before: datetime | None = None
    priority: int = 0
    demand_type: str = "MTO"


@dataclass(frozen=True, slots=True)
class ResourceInput:
    resource_id: str
    name: str
    capacity_mode: str
    is_constraint: bool
    capacity_units: int = 1
    efficiency_percent: int = 100


@dataclass(frozen=True, slots=True)
class CapacityBucket:
    resource_id: str
    bucket_start: datetime
    bucket_end: datetime
    capacity_minutes: int


@dataclass(frozen=True, slots=True)
class PrecedenceConstraint:
    before_operation_id: str
    after_operation_id: str
    min_lag_minutes: int = 0


@dataclass(frozen=True, slots=True)
class FixedOperationAssignment:
    operation_id: str
    resource_id: str
    start_at: datetime


@dataclass(frozen=True, slots=True)
class SetupTransition:
    resource_id: str
    from_family: str
    to_family: str
    setup_minutes: int


@dataclass(frozen=True, slots=True)
class SchedulingObjective:
    primary_metric: str = "minimize_total_lateness"
    tardiness_weight: float = 1.0
    makespan_weight: float = 0.001
    alternate_resource_weight: float = 0.01
    strategy_id: str = "balanced"


@dataclass(frozen=True, slots=True)
class SchedulingOptions:
    time_bucket_minutes: int = 60
    enforce_finite_capacity_on_constraints_only: bool = True
    solver_time_limit_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class OperationRequirement:
    operation_id: str
    order_id: str
    resource_id: str
    duration_minutes: int
    routing_id: str = "PRIMARY"
    alternate_resource_ids: list[str] = field(default_factory=list)
    setup_family: str | None = None
    earliest_start_at: datetime | None = None
    latest_end_at: datetime | None = None

    @property
    def eligible_resource_ids(self) -> list[str]:
        return list(dict.fromkeys([self.resource_id, *self.alternate_resource_ids]))


@dataclass(frozen=True, slots=True)
class SchedulingProblem:
    problem_id: str
    operations: list[OperationRequirement]
    schedule_start_at: datetime | None = None
    schedule_end_at: datetime | None = None
    orders: list[SchedulingOrderInput] = field(default_factory=list)
    resources: list[ResourceInput] = field(default_factory=list)
    capacity_buckets: list[CapacityBucket] = field(default_factory=list)
    precedence_constraints: list[PrecedenceConstraint] = field(default_factory=list)
    fixed_assignments: list[FixedOperationAssignment] = field(default_factory=list)
    setup_transitions: list[SetupTransition] = field(default_factory=list)
    objective: SchedulingObjective = field(default_factory=SchedulingObjective)
    options: SchedulingOptions = field(default_factory=SchedulingOptions)


@dataclass(frozen=True, slots=True)
class OperationAssignment:
    operation_id: str
    order_id: str
    resource_id: str
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class SchedulingResult:
    backend_id: str
    status: str
    message: str
    problem_id: str | None = None
    objective_value: float | None = None
    assignments: list[OperationAssignment] = field(default_factory=list)
    diagnostics: list[SolverDiagnostic] = field(default_factory=list)


class OrToolsEngine:
    backend_id = "ortools"

    def __init__(self, available: bool | None = None) -> None:
        self._available_override = available

    @property
    def available(self) -> bool:
        return self.is_available().available

    def is_available(self) -> SolverAvailability:
        available = (
            self._available_override
            if self._available_override is not None
            else find_spec("ortools") is not None
        )
        if available:
            return SolverAvailability(
                backend_id=self.backend_id,
                available=True,
                status="Available",
                message="OR-Tools backend is available.",
            )
        return SolverAvailability(
            backend_id=self.backend_id,
            available=False,
            status="Unavailable",
            message="OR-Tools backend is not installed or enabled.",
        )

    def solve(self, problem: SchedulingProblem) -> SchedulingResult:
        availability = self.is_available()
        if not availability.available:
            return SchedulingResult(
                backend_id=self.backend_id,
                status="Unavailable",
                message=availability.message,
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Warning",
                        code="ORTOOLS_UNAVAILABLE",
                        message=availability.message,
                    )
                ],
            )
        try:
            from sdbr.cp_sat_solver import solve_cp_sat

            return solve_cp_sat(problem)
        except Exception as exc:
            return SchedulingResult(
                backend_id=self.backend_id,
                status="Error",
                message=f"OR-Tools CP-SAT solve failed: {exc}",
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Error",
                        code="ORTOOLS_SOLVE_FAILED",
                        message=str(exc),
                    )
                ],
            )


class GurobiEngine:
    backend_id = "gurobi"

    def __init__(self, available: bool | None = None) -> None:
        self._available_override = available

    @property
    def available(self) -> bool:
        return self.is_available().available

    def is_available(self) -> SolverAvailability:
        if self._available_override is not None:
            available = self._available_override
        else:
            available = find_spec("gurobipy") is not None
        if available:
            return SolverAvailability(
                backend_id=self.backend_id,
                available=True,
                status="Available",
                message="Gurobi backend is available.",
            )
        return SolverAvailability(
            backend_id=self.backend_id,
            available=False,
            status="Unavailable",
            message="Gurobi backend is not installed, enabled, or licensed.",
        )

    def solve(self, problem: SchedulingProblem) -> SchedulingResult:
        availability = self.is_available()
        if not availability.available:
            return SchedulingResult(
                backend_id=self.backend_id,
                status="Unavailable",
                message=availability.message,
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Warning",
                        code="GUROBI_UNAVAILABLE",
                        message=availability.message,
                        entity_id=None,
                    )
                ],
            )
        try:
            return _solve_fixed_resource_gurobi(problem)
        except Exception as exc:
            return SchedulingResult(
                backend_id=self.backend_id,
                status="Unavailable",
                message=f"Gurobi solve failed: {exc}",
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Error",
                        code="GUROBI_SOLVE_FAILED",
                        message=str(exc),
                    )
                ],
            )


class BaselineFiniteScheduler:
    backend_id = "baseline-finite"

    def solve(
        self,
        problem: SchedulingProblem,
        start_at: datetime,
    ) -> SchedulingResult:
        next_available_by_resource: dict[str, datetime] = {}
        assignments = []
        for operation in problem.operations:
            operation_start = next_available_by_resource.get(operation.resource_id, start_at)
            operation_end = operation_start + timedelta(minutes=operation.duration_minutes)
            next_available_by_resource[operation.resource_id] = operation_end
            assignments.append(
                OperationAssignment(
                    operation_id=operation.operation_id,
                    order_id=operation.order_id,
                    resource_id=operation.resource_id,
                    start=operation_start,
                    end=operation_end,
                )
            )
        return SchedulingResult(
            backend_id=self.backend_id,
            status="Feasible",
            message="Baseline finite schedule generated without optimization.",
            problem_id=problem.problem_id,
            assignments=assignments,
        )


def _solve_fixed_resource_gurobi(problem: SchedulingProblem) -> SchedulingResult:
    import gurobipy as gp
    from gurobipy import GRB

    if problem.schedule_start_at is None:
        return SchedulingResult(
            backend_id="gurobi",
            status="Error",
            message="Gurobi scheduling requires schedule_start_at.",
            problem_id=problem.problem_id,
            diagnostics=[
                SolverDiagnostic(
                    severity="Error",
                    code="MISSING_SCHEDULE_START",
                    message="Gurobi scheduling requires schedule_start_at.",
                )
            ],
        )
    operations_by_id = {operation.operation_id: operation for operation in problem.operations}
    if len(operations_by_id) != len(problem.operations):
        return SchedulingResult(
            backend_id="gurobi",
            status="Error",
            message="Operation IDs must be unique for Gurobi scheduling.",
            problem_id=problem.problem_id,
            diagnostics=[
                SolverDiagnostic(
                    severity="Error",
                    code="DUPLICATE_OPERATION_ID",
                    message="Operation IDs must be unique for Gurobi scheduling.",
                )
            ],
        )

    horizon_minutes = _scheduling_horizon_minutes(problem)
    model = gp.Model(f"sdbr_{problem.problem_id}")
    model.Params.OutputFlag = 0
    if problem.options.solver_time_limit_seconds is not None:
        model.Params.TimeLimit = problem.options.solver_time_limit_seconds

    start = {
        operation.operation_id: model.addVar(
            lb=0,
            ub=horizon_minutes,
            vtype=GRB.CONTINUOUS,
            name=f"start[{operation.operation_id}]",
        )
        for operation in problem.operations
    }
    end = {
        operation.operation_id: model.addVar(
            lb=0,
            ub=horizon_minutes,
            vtype=GRB.CONTINUOUS,
            name=f"end[{operation.operation_id}]",
        )
        for operation in problem.operations
    }

    for operation in problem.operations:
        model.addConstr(
            end[operation.operation_id]
            == start[operation.operation_id] + operation.duration_minutes,
            name=f"duration[{operation.operation_id}]",
        )

    assign = {
        (operation.operation_id, resource_id): model.addVar(
            vtype=GRB.BINARY,
            name=f"assign[{operation.operation_id},{resource_id}]",
        )
        for operation in problem.operations
        for resource_id in operation.eligible_resource_ids
    }
    for operation in problem.operations:
        model.addConstr(
            gp.quicksum(
                assign[(operation.operation_id, resource_id)]
                for resource_id in operation.eligible_resource_ids
            )
            == 1,
            name=f"assign_one_resource[{operation.operation_id}]",
        )

    for constraint in problem.precedence_constraints:
        if (
            constraint.before_operation_id not in operations_by_id
            or constraint.after_operation_id not in operations_by_id
        ):
            continue
        model.addConstr(
            start[constraint.after_operation_id]
            >= end[constraint.before_operation_id] + constraint.min_lag_minutes,
            name=(
                f"precedence[{constraint.before_operation_id}->"
                f"{constraint.after_operation_id}]"
            ),
        )

    finite_resource_ids = _finite_resource_ids(problem)
    operations_by_resource: dict[str, list[OperationRequirement]] = {}
    for operation in problem.operations:
        for resource_id in operation.eligible_resource_ids:
            operations_by_resource.setdefault(resource_id, []).append(operation)
    for resource_id in sorted(finite_resource_ids):
        resource_operations = operations_by_resource.get(resource_id, [])
        for left_index, left in enumerate(resource_operations):
            for right in resource_operations[left_index + 1 :]:
                left_before_right = model.addVar(
                    vtype=GRB.BINARY,
                    name=f"order[{left.operation_id},{right.operation_id}]",
                )
                model.addConstr(
                    end[left.operation_id]
                    <= start[right.operation_id]
                    + horizon_minutes * (1 - left_before_right)
                    + horizon_minutes * (1 - assign[(left.operation_id, resource_id)])
                    + horizon_minutes * (1 - assign[(right.operation_id, resource_id)]),
                    name=f"no_overlap_lr[{left.operation_id},{right.operation_id}]",
                )
                model.addConstr(
                    end[right.operation_id]
                    <= start[left.operation_id]
                    + horizon_minutes * left_before_right
                    + horizon_minutes * (1 - assign[(left.operation_id, resource_id)])
                    + horizon_minutes * (1 - assign[(right.operation_id, resource_id)]),
                    name=f"no_overlap_rl[{left.operation_id},{right.operation_id}]",
                )

    capacity_buckets_by_resource: dict[str, list[CapacityBucket]] = {}
    for bucket in problem.capacity_buckets:
        capacity_buckets_by_resource.setdefault(bucket.resource_id, []).append(bucket)
    for resource_id in sorted(finite_resource_ids):
        resource_buckets = sorted(
            capacity_buckets_by_resource.get(resource_id, []),
            key=lambda bucket: (bucket.bucket_start, bucket.bucket_end),
        )
        if not resource_buckets:
            continue
        bucket_choice: dict[tuple[str, str, int], object] = {}
        for operation in operations_by_resource.get(resource_id, []):
            eligible_bucket_indexes = [
                index
                for index, bucket in enumerate(resource_buckets)
                if _capacity_bucket_can_fit_operation(
                    bucket=bucket,
                    operation=operation,
                    schedule_start_at=problem.schedule_start_at,
                )
            ]
            for index in eligible_bucket_indexes:
                bucket_choice[(operation.operation_id, resource_id, index)] = model.addVar(
                    vtype=GRB.BINARY,
                    name=f"bucket[{operation.operation_id},{resource_id},{index}]",
                )
            model.addConstr(
                gp.quicksum(
                    bucket_choice[(operation.operation_id, resource_id, index)]
                    for index in eligible_bucket_indexes
                )
                == assign[(operation.operation_id, resource_id)],
                name=f"assign_bucket[{operation.operation_id},{resource_id}]",
            )
            for index in eligible_bucket_indexes:
                bucket = resource_buckets[index]
                bucket_start, bucket_end = _capacity_bucket_offsets(
                    bucket=bucket,
                    schedule_start_at=problem.schedule_start_at,
                )
                choice = bucket_choice[(operation.operation_id, resource_id, index)]
                model.addConstr(
                    start[operation.operation_id]
                    >= bucket_start - horizon_minutes * (1 - choice),
                    name=f"bucket_start[{operation.operation_id},{index}]",
                )
                model.addConstr(
                    end[operation.operation_id]
                    <= bucket_end + horizon_minutes * (1 - choice),
                    name=f"bucket_end[{operation.operation_id},{index}]",
                )
        for index, bucket in enumerate(resource_buckets):
            model.addConstr(
                gp.quicksum(
                    operation.duration_minutes
                    * bucket_choice[(operation.operation_id, resource_id, index)]
                    for operation in operations_by_resource.get(resource_id, [])
                    if (operation.operation_id, resource_id, index) in bucket_choice
                )
                <= bucket.capacity_minutes,
                name=f"bucket_capacity[{resource_id},{index}]",
            )

    lateness_vars = []
    for order in problem.orders:
        order_operations = [
            operation
            for operation in problem.operations
            if operation.order_id == order.order_id
        ]
        if not order_operations:
            continue
        planning_due_at = order.protected_due_at or order.due_at
        due_minutes = int(
            (planning_due_at - problem.schedule_start_at).total_seconds() / 60
        )
        completion = model.addVar(
            lb=0,
            ub=horizon_minutes,
            vtype=GRB.CONTINUOUS,
            name=f"completion[{order.order_id}]",
        )
        lateness = model.addVar(
            lb=0,
            ub=horizon_minutes,
            vtype=GRB.CONTINUOUS,
            name=f"lateness[{order.order_id}]",
        )
        for operation in order_operations:
            model.addConstr(
                completion >= end[operation.operation_id],
                name=f"completion_after[{order.order_id},{operation.operation_id}]",
            )
        model.addConstr(
            lateness >= completion - due_minutes,
            name=f"lateness_due[{order.order_id}]",
        )
        lateness_vars.append(lateness)

    makespan = model.addVar(
        lb=0,
        ub=horizon_minutes,
        vtype=GRB.CONTINUOUS,
        name="makespan",
    )
    for operation in problem.operations:
        model.addConstr(
            makespan >= end[operation.operation_id],
            name=f"makespan_after[{operation.operation_id}]",
        )
    alternate_resource_uses = gp.quicksum(
        assign[(operation.operation_id, resource_id)]
        for operation in problem.operations
        for resource_id in operation.alternate_resource_ids
        if (operation.operation_id, resource_id) in assign
    )
    objective_expression = (
        gp.quicksum(lateness_vars) * problem.objective.tardiness_weight
        + makespan * problem.objective.makespan_weight
        + alternate_resource_uses * problem.objective.alternate_resource_weight
    )
    model.setObjective(objective_expression, GRB.MINIMIZE)

    model.optimize()
    time_limit_diagnostics = []
    if problem.options.solver_time_limit_seconds is not None:
        time_limit_diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="GUROBI_TIME_LIMIT_CONFIGURED",
                message=(
                    "Gurobi time limit set to "
                    f"{problem.options.solver_time_limit_seconds:g} seconds."
                ),
            )
        )
    if model.status == GRB.TIME_LIMIT and model.SolCount == 0:
        return SchedulingResult(
            backend_id="gurobi",
            status="TimeLimit",
            message="Gurobi reached the time limit without a feasible schedule.",
            problem_id=problem.problem_id,
            diagnostics=[
                *time_limit_diagnostics,
                SolverDiagnostic(
                    severity="Warning",
                    code="GUROBI_TIME_LIMIT_NO_SOLUTION",
                    message="Gurobi reached the time limit without a feasible schedule.",
                ),
            ],
        )
    if model.status not in {GRB.OPTIMAL, GRB.SUBOPTIMAL, GRB.TIME_LIMIT}:
        status = "Infeasible" if model.status == GRB.INFEASIBLE else "Error"
        return SchedulingResult(
            backend_id="gurobi",
            status=status,
            message=f"Gurobi finished with status code {model.status}.",
            problem_id=problem.problem_id,
            diagnostics=[
                *time_limit_diagnostics,
                SolverDiagnostic(
                    severity="Error",
                    code="GUROBI_NON_FEASIBLE_STATUS",
                    message=f"Gurobi finished with status code {model.status}.",
                )
            ],
        )

    result_status = "Optimal" if model.status == GRB.OPTIMAL else "Feasible"
    assignments = [
        OperationAssignment(
            operation_id=operation.operation_id,
            order_id=operation.order_id,
            resource_id=_selected_resource_id(operation, assign),
            start=problem.schedule_start_at + timedelta(minutes=round(start[operation.operation_id].X)),
            end=problem.schedule_start_at + timedelta(minutes=round(end[operation.operation_id].X)),
        )
        for operation in problem.operations
    ]
    return SchedulingResult(
        backend_id="gurobi",
        status=result_status,
        message=(
            "Gurobi reached the time limit with a feasible schedule."
            if model.status == GRB.TIME_LIMIT
            else "Gurobi fixed-resource finite capacity schedule generated."
        ),
        problem_id=problem.problem_id,
        objective_value=float(model.ObjVal) if model.SolCount > 0 else None,
        assignments=sorted(assignments, key=lambda item: (item.start, item.end, item.operation_id)),
        diagnostics=[
            *time_limit_diagnostics,
            SolverDiagnostic(
                severity="Info",
                code="GUROBI_FIXED_RESOURCE_MODEL",
                message=(
                    "Solved fixed-resource model with precedence constraints and "
                    "finite-resource no-overlap constraints."
                ),
            )
        ],
    )


def _finite_resource_ids(problem: SchedulingProblem) -> set[str]:
    if not problem.resources:
        return {operation.resource_id for operation in problem.operations}
    return {
        resource.resource_id
        for resource in problem.resources
        if resource.capacity_mode.upper() == "FINITE"
    }


def _resources_by_id(problem: SchedulingProblem) -> dict[str, ResourceInput]:
    return {resource.resource_id: resource for resource in problem.resources}


def _resource_capacity_units(problem: SchedulingProblem, resource_id: str) -> int:
    resource = _resources_by_id(problem).get(resource_id)
    return max(1, int(resource.capacity_units if resource is not None else 1))


def _effective_duration_minutes(
    problem: SchedulingProblem,
    operation: OperationRequirement,
    resource_id: str | None = None,
) -> int:
    resource = _resources_by_id(problem).get(resource_id or operation.resource_id)
    efficiency = int(resource.efficiency_percent if resource is not None else 100)
    efficiency = max(1, efficiency)
    return max(1, ceil(operation.duration_minutes * 100 / efficiency))


def _selected_resource_id(
    operation: OperationRequirement,
    assign: dict[tuple[str, str], object],
) -> str:
    for resource_id in operation.eligible_resource_ids:
        if assign[(operation.operation_id, resource_id)].X > 0.5:
            return resource_id
    return operation.resource_id


def _capacity_bucket_can_fit_operation(
    *,
    bucket: CapacityBucket,
    operation: OperationRequirement,
    schedule_start_at: datetime,
) -> bool:
    bucket_start, bucket_end = _capacity_bucket_offsets(
        bucket=bucket,
        schedule_start_at=schedule_start_at,
    )
    bucket_span_minutes = bucket_end - bucket_start
    duration_minutes = operation.duration_minutes
    return (
        bucket_end > 0
        and bucket.capacity_minutes >= duration_minutes
        and bucket_span_minutes >= duration_minutes
    )


def _capacity_bucket_offsets(
    *,
    bucket: CapacityBucket,
    schedule_start_at: datetime,
) -> tuple[int, int]:
    return (
        int((bucket.bucket_start - schedule_start_at).total_seconds() / 60),
        int((bucket.bucket_end - schedule_start_at).total_seconds() / 60),
    )


def _scheduling_horizon_minutes(problem: SchedulingProblem) -> int:
    total_duration = sum(
        max(
            _effective_duration_minutes(problem, operation, resource_id)
            for resource_id in operation.eligible_resource_ids
        )
        for operation in problem.operations
    )
    operations_by_id = {
        operation.operation_id: operation for operation in problem.operations
    }
    due_offsets = [
        int(
            (
                (order.protected_due_at or order.due_at)
                - problem.schedule_start_at
            ).total_seconds()
            / 60
        )
        for order in problem.orders
        if problem.schedule_start_at is not None
    ]
    bucket_offsets = [
        int((bucket.bucket_end - problem.schedule_start_at).total_seconds() / 60)
        for bucket in problem.capacity_buckets
        if problem.schedule_start_at is not None
    ]
    explicit_horizon = (
        int((problem.schedule_end_at - problem.schedule_start_at).total_seconds() / 60)
        if problem.schedule_start_at is not None and problem.schedule_end_at is not None
        else 0
    )
    fixed_offsets = [
        int((assignment.start_at - problem.schedule_start_at).total_seconds() / 60)
        + _effective_duration_minutes(
            problem,
            operations_by_id[assignment.operation_id],
            assignment.resource_id,
        )
        for assignment in problem.fixed_assignments
        if problem.schedule_start_at is not None
        and assignment.operation_id in operations_by_id
    ]
    window_offsets = [
        int((operation.latest_end_at - problem.schedule_start_at).total_seconds() / 60)
        for operation in problem.operations
        if problem.schedule_start_at is not None
        and operation.latest_end_at is not None
    ]
    setup_total = sum(
        max(0, transition.setup_minutes) for transition in problem.setup_transitions
    )
    return max(
        (total_duration + setup_total) * 2,
        max(due_offsets, default=0) + total_duration + setup_total,
        max(bucket_offsets, default=0) + total_duration + setup_total,
        max(fixed_offsets, default=0) + total_duration + setup_total,
        max(window_offsets, default=0) + total_duration,
        explicit_horizon,
        1,
    )


def create_solver_engine(backend_id: str):
    normalized = backend_id.lower()
    if normalized == "ortools":
        return OrToolsEngine()
    if normalized == "gurobi":
        return GurobiEngine()
    raise ValueError(f"Unsupported solver backend: {backend_id}")


def build_resource_inputs(resources: list[Resource]) -> list[ResourceInput]:
    return [
        ResourceInput(
            resource_id=resource.resource_id,
            name=resource.name,
            capacity_mode="FINITE" if resource.is_constraint else "INFINITE",
            is_constraint=resource.is_constraint,
            capacity_units=max(1, int(resource.capacity_units)),
            efficiency_percent=max(1, int(resource.efficiency_percent)),
        )
        for resource in resources
    ]


def build_capacity_buckets_from_resources(
    resources: list[Resource],
    tzinfo: TzInfo | None,
) -> list[CapacityBucket]:
    buckets: list[CapacityBucket] = []
    for resource in resources:
        if resource.calendar is not None:
            if tzinfo is None:
                raise ValueError("tzinfo is required when resource calendars are used")
            buckets.extend(_calendar_capacity_buckets_for_resource(resource, tzinfo))
            continue
        for bucket_date, capacity_minutes in sorted(resource.daily_capacity_minutes.items()):
            bucket_start = datetime.combine(bucket_date, time.min, tzinfo=tzinfo)
            bucket_end = bucket_start + timedelta(days=1)
            buckets.append(
                CapacityBucket(
                    resource_id=resource.resource_id,
                    bucket_start=bucket_start,
                    bucket_end=bucket_end,
                    capacity_minutes=capacity_minutes,
                )
            )
    return buckets


def _calendar_capacity_buckets_for_resource(
    resource: Resource,
    tzinfo: TzInfo,
) -> list[CapacityBucket]:
    if resource.calendar is None:
        return []
    buckets: list[CapacityBucket] = []
    for bucket_date in sorted(resource.daily_capacity_minutes):
        if resource.calendar.holidays is not None and bucket_date in resource.calendar.holidays:
            continue
        if bucket_date.weekday() not in resource.calendar.working_weekdays:
            continue
        for shift in resource.calendar.shifts:
            shift_start = datetime.combine(bucket_date, shift.start, tzinfo=tzinfo)
            shift_end = datetime.combine(bucket_date, shift.end, tzinfo=tzinfo)
            for segment_start, segment_end in _subtract_maintenance_windows(
                shift_start=shift_start,
                shift_end=shift_end,
                maintenance_windows=resource.calendar.maintenance_windows,
            ):
                capacity_minutes = int((segment_end - segment_start).total_seconds() / 60)
                if capacity_minutes <= 0:
                    continue
                buckets.append(
                    CapacityBucket(
                        resource_id=resource.resource_id,
                        bucket_start=segment_start,
                        bucket_end=segment_end,
                        capacity_minutes=capacity_minutes,
                    )
                )
    return sorted(buckets, key=lambda item: (item.bucket_start, item.bucket_end, item.resource_id))


def _subtract_maintenance_windows(
    *,
    shift_start: datetime,
    shift_end: datetime,
    maintenance_windows: list,
) -> list[tuple[datetime, datetime]]:
    segments = [(shift_start, shift_end)]
    for maintenance in sorted(maintenance_windows, key=lambda item: (item.start, item.end)):
        updated_segments: list[tuple[datetime, datetime]] = []
        for segment_start, segment_end in segments:
            overlap_start = max(segment_start, maintenance.start)
            overlap_end = min(segment_end, maintenance.end)
            if overlap_start >= overlap_end:
                updated_segments.append((segment_start, segment_end))
                continue
            if segment_start < overlap_start:
                updated_segments.append((segment_start, overlap_start))
            if overlap_end < segment_end:
                updated_segments.append((overlap_end, segment_end))
        segments = updated_segments
    return segments


class SimioValidationAdapter:
    export_format = "operation_rows"

    def export_problem(self, problem: SchedulingProblem) -> dict[str, object]:
        return {
            "ProblemID": problem.problem_id,
            "Format": self.export_format,
            "Rows": [
                {
                    "OperationID": operation.operation_id,
                    "OrderID": operation.order_id,
                    "ResourceID": operation.resource_id,
                    "DurationMinutes": operation.duration_minutes,
                    "RoutingID": operation.routing_id,
                }
                for operation in problem.operations
            ],
        }


def build_scheduling_problem(
    problem_id: str,
    orders: list[SchedulingOrder],
    routings: list[Routing],
    resource_inputs: list[ResourceInput] | None = None,
    capacity_buckets: list[CapacityBucket] | None = None,
    schedule_start_at: datetime | None = None,
    schedule_end_at: datetime | None = None,
    time_buffer_minutes: int = 0,
    solver_time_limit_seconds: float | None = None,
    fixed_assignments: list[FixedOperationAssignment] | None = None,
    setup_transitions: list[SetupTransition] | None = None,
    objective: SchedulingObjective | None = None,
) -> SchedulingProblem:
    routings_by_product = _primary_routings_by_product(routings)
    operations = []
    order_inputs = []
    for order in orders:
        routing = routings_by_product[order.product_id]
        routing_minutes = sum(
            int(operation.duration_minutes * order.quantity)
            for operation in routing.operations
        )
        protected_due_at = order.due_date - timedelta(minutes=time_buffer_minutes)
        order_inputs.append(
            SchedulingOrderInput(
                order_id=order.order_id,
                product_id=order.product_id,
                quantity=order.quantity,
                due_at=order.due_date,
                protected_due_at=protected_due_at,
                release_not_before=protected_due_at - timedelta(minutes=routing_minutes),
            )
        )
    precedence_constraints: list[PrecedenceConstraint] = []
    for order in orders:
        routing = routings_by_product[order.product_id]
        previous_operation_id: str | None = None
        for operation in sorted(routing.operations, key=lambda item: item.sequence):
            operation_id = f"{order.order_id}:{operation.operation_id}"
            operations.append(
                OperationRequirement(
                    operation_id=operation_id,
                    order_id=order.order_id,
                    resource_id=operation.resource_id,
                    duration_minutes=int(operation.duration_minutes * order.quantity),
                    routing_id=routing.routing_id,
                    alternate_resource_ids=operation.alternate_resource_ids or [],
                    setup_family=operation.setup_family or order.product_id,
                    earliest_start_at=operation.earliest_start_at,
                    latest_end_at=operation.latest_end_at,
                )
            )
            if previous_operation_id is not None:
                precedence_constraints.append(
                    PrecedenceConstraint(
                        before_operation_id=previous_operation_id,
                        after_operation_id=operation_id,
                    )
                )
            previous_operation_id = operation_id
    return SchedulingProblem(
        problem_id=problem_id,
        operations=operations,
        schedule_start_at=schedule_start_at,
        schedule_end_at=schedule_end_at,
        orders=order_inputs,
        resources=resource_inputs or [],
        capacity_buckets=capacity_buckets or [],
        precedence_constraints=precedence_constraints,
        fixed_assignments=fixed_assignments or [],
        setup_transitions=setup_transitions or [],
        objective=objective or SchedulingObjective(),
        options=SchedulingOptions(
            solver_time_limit_seconds=solver_time_limit_seconds,
        ),
    )


def _primary_routings_by_product(routings: list[Routing]) -> dict[str, Routing]:
    result = {}
    for routing in routings:
        if routing.is_primary or routing.product_id not in result:
            result[routing.product_id] = routing
    return result
