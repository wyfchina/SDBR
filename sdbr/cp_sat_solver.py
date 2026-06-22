from __future__ import annotations

from datetime import timedelta

from sdbr.scheduling_solver import (
    OperationAssignment,
    SchedulingProblem,
    SchedulingResult,
    SolverDiagnostic,
    BUILT_IN_OBJECTIVE_STRATEGY_IDS,
    _capacity_bucket_offsets,
    _effective_duration_minutes,
    _finite_resource_ids,
    _resource_capacity_units,
    _resources_by_id,
    _scheduling_horizon_minutes,
)


OBJECTIVE_SCALE = 1000


def solve_cp_sat(problem: SchedulingProblem) -> SchedulingResult:
    from ortools.sat.python import cp_model

    validation_error = _validate_problem(problem)
    if validation_error is not None:
        return validation_error

    schedule_start = problem.schedule_start_at
    assert schedule_start is not None
    horizon = _scheduling_horizon_minutes(problem)
    model = cp_model.CpModel()

    starts = {}
    ends = {}
    presence = {}
    intervals_by_resource: dict[str, list[object]] = {}
    durations: dict[tuple[str, str], int] = {}
    for operation in problem.operations:
        operation_id = operation.operation_id
        starts[operation_id] = model.new_int_var(0, horizon, f"start[{operation_id}]")
        ends[operation_id] = model.new_int_var(0, horizon, f"end[{operation_id}]")
        choices = []
        for resource_id in operation.eligible_resource_ids:
            duration = _effective_duration_minutes(problem, operation, resource_id)
            durations[(operation_id, resource_id)] = duration
            selected = model.new_bool_var(f"assign[{operation_id},{resource_id}]")
            presence[(operation_id, resource_id)] = selected
            interval = model.new_optional_interval_var(
                starts[operation_id],
                duration,
                ends[operation_id],
                selected,
                f"interval[{operation_id},{resource_id}]",
            )
            intervals_by_resource.setdefault(resource_id, []).append(interval)
            choices.append(selected)
        model.add_exactly_one(choices)
        if operation.earliest_start_at is not None:
            earliest_start = int(
                (operation.earliest_start_at - schedule_start).total_seconds() / 60
            )
            model.add(starts[operation_id] >= earliest_start)
        if operation.latest_end_at is not None:
            latest_end = int(
                (operation.latest_end_at - schedule_start).total_seconds() / 60
            )
            model.add(ends[operation_id] <= latest_end)

    operations_by_id = {
        operation.operation_id: operation for operation in problem.operations
    }
    for assignment in problem.fixed_assignments:
        operation = operations_by_id[assignment.operation_id]
        fixed_start = int(
            (assignment.start_at - schedule_start).total_seconds() / 60
        )
        model.add(starts[assignment.operation_id] == fixed_start)
        for resource_id in operation.eligible_resource_ids:
            model.add(
                presence[(assignment.operation_id, resource_id)]
                == (1 if resource_id == assignment.resource_id else 0)
            )

    for constraint in problem.precedence_constraints:
        if (
            constraint.before_operation_id not in operations_by_id
            or constraint.after_operation_id not in operations_by_id
        ):
            continue
        model.add(
            starts[constraint.after_operation_id]
            >= ends[constraint.before_operation_id] + constraint.min_lag_minutes
        )

    finite_resource_ids = _finite_resource_ids(problem)
    for resource_id in sorted(finite_resource_ids):
        resource_intervals = intervals_by_resource.get(resource_id, [])
        capacity_units = _resource_capacity_units(problem, resource_id)
        if resource_intervals and capacity_units <= 1:
            model.add_no_overlap(resource_intervals)
        elif resource_intervals:
            model.add_cumulative(
                resource_intervals,
                [1 for _ in resource_intervals],
                capacity_units,
            )

    _add_setup_transition_constraints(
        model=model,
        problem=problem,
        starts=starts,
        ends=ends,
        presence=presence,
    )

    _add_capacity_bucket_constraints(
        model=model,
        problem=problem,
        starts=starts,
        ends=ends,
        presence=presence,
        durations=durations,
        finite_resource_ids=finite_resource_ids,
    )

    objective_terms = _add_objective_terms(
        model=model,
        problem=problem,
        ends=ends,
        presence=presence,
        horizon=horizon,
    )
    model.minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    diagnostics = []
    if problem.options.solver_time_limit_seconds is not None:
        solver.parameters.max_time_in_seconds = problem.options.solver_time_limit_seconds
        diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_TIME_LIMIT_CONFIGURED",
                message=(
                    "OR-Tools CP-SAT time limit set to "
                    f"{problem.options.solver_time_limit_seconds:g} seconds."
                ),
            )
        )

    status_code = solver.solve(model)
    if status_code == cp_model.INFEASIBLE:
        return SchedulingResult(
            backend_id="ortools",
            status="Infeasible",
            message="OR-Tools CP-SAT found the scheduling problem infeasible.",
            problem_id=problem.problem_id,
            diagnostics=[
                *diagnostics,
                SolverDiagnostic(
                    severity="Error",
                    code="ORTOOLS_INFEASIBLE",
                    message="OR-Tools CP-SAT found no feasible schedule.",
                ),
            ],
        )
    if status_code == cp_model.MODEL_INVALID:
        return SchedulingResult(
            backend_id="ortools",
            status="Error",
            message="OR-Tools CP-SAT rejected the scheduling model.",
            problem_id=problem.problem_id,
            diagnostics=[
                *diagnostics,
                SolverDiagnostic(
                    severity="Error",
                    code="ORTOOLS_MODEL_INVALID",
                    message="OR-Tools CP-SAT rejected the scheduling model.",
                ),
            ],
        )
    if status_code == cp_model.UNKNOWN:
        return SchedulingResult(
            backend_id="ortools",
            status=(
                "TimeLimit"
                if problem.options.solver_time_limit_seconds is not None
                else "Error"
            ),
            message="OR-Tools CP-SAT stopped without a feasible schedule.",
            problem_id=problem.problem_id,
            diagnostics=[
                *diagnostics,
                SolverDiagnostic(
                    severity="Warning",
                    code="ORTOOLS_TIME_LIMIT_NO_SOLUTION",
                    message="OR-Tools CP-SAT stopped without a feasible schedule.",
                ),
            ],
        )

    assignments = []
    for operation in problem.operations:
        selected_resource = operation.resource_id
        for resource_id in operation.eligible_resource_ids:
            if solver.value(presence[(operation.operation_id, resource_id)]):
                selected_resource = resource_id
                break
        assignments.append(
            OperationAssignment(
                operation_id=operation.operation_id,
                order_id=operation.order_id,
                resource_id=selected_resource,
                start=schedule_start
                + timedelta(minutes=solver.value(starts[operation.operation_id])),
                end=schedule_start
                + timedelta(minutes=solver.value(ends[operation.operation_id])),
            )
        )

    result_status = "Optimal" if status_code == cp_model.OPTIMAL else "Feasible"
    return SchedulingResult(
        backend_id="ortools",
        status=result_status,
        message="OR-Tools CP-SAT finite-capacity schedule generated.",
        problem_id=problem.problem_id,
        objective_value=float(solver.objective_value) / OBJECTIVE_SCALE,
        assignments=sorted(
            assignments,
            key=lambda item: (item.start, item.end, item.operation_id),
        ),
        diagnostics=[
            *diagnostics,
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_CP_SAT_MODEL",
                message=(
                    "Solved optional-resource intervals with precedence, "
                    "finite-resource, setup, parallel-capacity, time-window "
                    "and capacity-bucket constraints."
                ),
            ),
            *_advanced_capability_diagnostics(problem),
        ],
    )


def _validate_problem(problem: SchedulingProblem) -> SchedulingResult | None:
    if problem.schedule_start_at is None:
        return SchedulingResult(
            backend_id="ortools",
            status="Error",
            message="OR-Tools scheduling requires schedule_start_at.",
            problem_id=problem.problem_id,
            diagnostics=[
                SolverDiagnostic(
                    severity="Error",
                    code="MISSING_SCHEDULE_START",
                    message="OR-Tools scheduling requires schedule_start_at.",
                )
            ],
        )
    operation_ids = [operation.operation_id for operation in problem.operations]
    if len(operation_ids) != len(set(operation_ids)):
        return SchedulingResult(
            backend_id="ortools",
            status="Error",
            message="Operation IDs must be unique for OR-Tools scheduling.",
            problem_id=problem.problem_id,
            diagnostics=[
                SolverDiagnostic(
                    severity="Error",
                    code="DUPLICATE_OPERATION_ID",
                    message="Operation IDs must be unique for OR-Tools scheduling.",
                )
            ],
        )
    resources_by_id = _resources_by_id(problem)
    for resource in problem.resources:
        if resource.capacity_units < 1:
            return _validation_error(
                problem,
                code="INVALID_RESOURCE_CAPACITY_UNITS",
                message="Resource capacity_units must be at least 1.",
                entity_id=resource.resource_id,
            )
        if resource.efficiency_percent < 1:
            return _validation_error(
                problem,
                code="INVALID_RESOURCE_EFFICIENCY",
                message="Resource efficiency_percent must be at least 1.",
                entity_id=resource.resource_id,
            )
    operations_by_id = {
        operation.operation_id: operation for operation in problem.operations
    }
    setup_resources = {transition.resource_id for transition in problem.setup_transitions}
    for resource_id in setup_resources:
        resource = resources_by_id.get(resource_id)
        if resource is not None and resource.capacity_units > 1:
            return _validation_error(
                problem,
                code="SETUP_NOT_SUPPORTED_FOR_PARALLEL_RESOURCE",
                message=(
                    "Sequence-dependent setup is supported only for finite "
                    "single-unit resources."
                ),
                entity_id=resource_id,
            )
    for transition in problem.setup_transitions:
        if transition.setup_minutes < 0:
            return _validation_error(
                problem,
                code="INVALID_SETUP_MINUTES",
                message="Setup transition minutes must be non-negative.",
                entity_id=transition.resource_id,
            )
    for operation in problem.operations:
        if operation.earliest_start_at is not None and operation.earliest_start_at < problem.schedule_start_at:
            return _validation_error(
                problem,
                code="OPERATION_WINDOW_BEFORE_SCHEDULE_START",
                message="Operation earliest_start_at cannot be before schedule_start_at.",
                entity_id=operation.operation_id,
            )
        if (
            operation.earliest_start_at is not None
            and operation.latest_end_at is not None
            and operation.earliest_start_at >= operation.latest_end_at
        ):
            return _validation_error(
                problem,
                code="INVALID_OPERATION_TIME_WINDOW",
                message="Operation earliest_start_at must be before latest_end_at.",
                entity_id=operation.operation_id,
            )
    fixed_operation_ids = [
        assignment.operation_id for assignment in problem.fixed_assignments
    ]
    if len(fixed_operation_ids) != len(set(fixed_operation_ids)):
        return SchedulingResult(
            backend_id="ortools",
            status="Error",
            message="Fixed operation assignments must be unique for OR-Tools scheduling.",
            problem_id=problem.problem_id,
            diagnostics=[
                SolverDiagnostic(
                    severity="Error",
                    code="DUPLICATE_FIXED_OPERATION_ASSIGNMENT",
                    message=(
                        "Fixed operation assignments must reference each operation "
                        "at most once."
                    ),
                )
            ],
        )
    for assignment in problem.fixed_assignments:
        operation = operations_by_id.get(assignment.operation_id)
        if operation is None:
            return SchedulingResult(
                backend_id="ortools",
                status="Error",
                message="Fixed operation assignment references an unknown operation.",
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Error",
                        code="FIXED_OPERATION_NOT_FOUND",
                        message=(
                            "Fixed operation assignment references an unknown "
                            "operation."
                        ),
                        entity_id=assignment.operation_id,
                    )
                ],
            )
        if assignment.resource_id not in operation.eligible_resource_ids:
            return SchedulingResult(
                backend_id="ortools",
                status="Error",
                message="Fixed operation assignment uses a non-eligible resource.",
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Error",
                        code="FIXED_RESOURCE_NOT_ELIGIBLE",
                        message=(
                            "Fixed operation assignment must use the primary "
                            "resource or an alternate resource."
                        ),
                        entity_id=assignment.operation_id,
                    )
                ],
            )
        if assignment.start_at < problem.schedule_start_at:
            return SchedulingResult(
                backend_id="ortools",
                status="Error",
                message="Fixed operation assignment starts before the planning horizon.",
                problem_id=problem.problem_id,
                diagnostics=[
                    SolverDiagnostic(
                        severity="Error",
                        code="FIXED_START_BEFORE_SCHEDULE_START",
                        message=(
                            "Fixed operation assignment starts before "
                            "schedule_start_at."
                        ),
                        entity_id=assignment.operation_id,
                    )
                ],
            )
    weights = _objective_weights(problem).values()
    if any(weight < 0 for weight in weights):
        return SchedulingResult(
            backend_id="ortools",
            status="Error",
            message="Scheduling objective weights must be non-negative.",
            problem_id=problem.problem_id,
            diagnostics=[
                SolverDiagnostic(
                    severity="Error",
                    code="INVALID_OBJECTIVE_WEIGHT",
                    message="Scheduling objective weights must be non-negative.",
                )
            ],
        )
    return None


def _validation_error(
    problem: SchedulingProblem,
    *,
    code: str,
    message: str,
    entity_id: str | None = None,
) -> SchedulingResult:
    return SchedulingResult(
        backend_id="ortools",
        status="Error",
        message=message,
        problem_id=problem.problem_id,
        diagnostics=[
            SolverDiagnostic(
                severity="Error",
                code=code,
                message=message,
                entity_id=entity_id,
            )
        ],
    )


def _add_setup_transition_constraints(*, model, problem, starts, ends, presence) -> None:
    setup_by_key = {
        (
            transition.resource_id,
            transition.from_family,
            transition.to_family,
        ): transition.setup_minutes
        for transition in problem.setup_transitions
    }
    if not setup_by_key:
        return

    finite_resource_ids = _finite_resource_ids(problem)
    for left_index, left in enumerate(problem.operations):
        for right in problem.operations[left_index + 1:]:
            common_resources = (
                set(left.eligible_resource_ids)
                & set(right.eligible_resource_ids)
                & finite_resource_ids
            )
            for resource_id in sorted(common_resources):
                if _resource_capacity_units(problem, resource_id) > 1:
                    continue
                left_family = left.setup_family or left.order_id
                right_family = right.setup_family or right.order_id
                left_to_right_setup = setup_by_key.get(
                    (resource_id, left_family, right_family), 0
                )
                right_to_left_setup = setup_by_key.get(
                    (resource_id, right_family, left_family), 0
                )
                if left_to_right_setup == 0 and right_to_left_setup == 0:
                    continue
                left_before_right = model.new_bool_var(
                    f"setup_order[{left.operation_id},{right.operation_id},{resource_id}]"
                )
                model.add(
                    starts[right.operation_id]
                    >= ends[left.operation_id] + left_to_right_setup
                ).only_enforce_if(
                    [
                        presence[(left.operation_id, resource_id)],
                        presence[(right.operation_id, resource_id)],
                        left_before_right,
                    ]
                )
                model.add(
                    starts[left.operation_id]
                    >= ends[right.operation_id] + right_to_left_setup
                ).only_enforce_if(
                    [
                        presence[(left.operation_id, resource_id)],
                        presence[(right.operation_id, resource_id)],
                        left_before_right.Not(),
                    ]
                )


def _add_capacity_bucket_constraints(
    *, model, problem, starts, ends, presence, durations, finite_resource_ids
) -> None:
    buckets_by_resource = {}
    for bucket in problem.capacity_buckets:
        buckets_by_resource.setdefault(bucket.resource_id, []).append(bucket)

    for resource_id in sorted(finite_resource_ids):
        resource_buckets = sorted(
            buckets_by_resource.get(resource_id, []),
            key=lambda item: (item.bucket_start, item.bucket_end),
        )
        if not resource_buckets:
            continue
        choices_by_bucket: dict[int, list[tuple[int, object]]] = {
            index: [] for index in range(len(resource_buckets))
        }
        for operation in problem.operations:
            if resource_id not in operation.eligible_resource_ids:
                continue
            choices = []
            for index, bucket in enumerate(resource_buckets):
                duration = durations[(operation.operation_id, resource_id)]
                bucket_start, bucket_end = _capacity_bucket_offsets(
                    bucket=bucket,
                    schedule_start_at=problem.schedule_start_at,
                )
                bucket_span_minutes = bucket_end - bucket_start
                if (
                    bucket_end <= 0
                    or bucket.capacity_minutes < duration
                    or bucket_span_minutes < duration
                ):
                    continue
                choice = model.new_bool_var(
                    f"bucket[{operation.operation_id},{resource_id},{index}]"
                )
                model.add(starts[operation.operation_id] >= bucket_start).only_enforce_if(choice)
                model.add(ends[operation.operation_id] <= bucket_end).only_enforce_if(choice)
                choices.append(choice)
                choices_by_bucket[index].append((duration, choice))
            model.add(sum(choices) == presence[(operation.operation_id, resource_id)])

        for index, bucket in enumerate(resource_buckets):
            model.add(
                sum(duration * choice for duration, choice in choices_by_bucket[index])
                <= bucket.capacity_minutes
            )


def _add_objective_terms(*, model, problem, ends, presence, horizon):
    terms = []
    weights = _objective_weights(problem)
    tardiness_coefficient = round(weights["tardiness"] * OBJECTIVE_SCALE)
    for order in problem.orders:
        order_ends = [
            ends[operation.operation_id]
            for operation in problem.operations
            if operation.order_id == order.order_id
        ]
        if not order_ends:
            continue
        completion = model.new_int_var(0, horizon, f"completion[{order.order_id}]")
        model.add_max_equality(completion, order_ends)
        due_at = order.protected_due_at or order.due_at
        due_minutes = int(
            (due_at - problem.schedule_start_at).total_seconds() / 60
        )
        lateness = model.new_int_var(0, horizon, f"lateness[{order.order_id}]")
        model.add(lateness >= completion - due_minutes)
        if tardiness_coefficient:
            terms.append(tardiness_coefficient * lateness)

    makespan = model.new_int_var(0, horizon, "makespan")
    if ends:
        model.add_max_equality(makespan, list(ends.values()))
    else:
        model.add(makespan == 0)
    makespan_coefficient = round(weights["makespan"] * OBJECTIVE_SCALE)
    if makespan_coefficient:
        terms.append(makespan_coefficient * makespan)

    alternate_coefficient = round(weights["alternate_resource"] * OBJECTIVE_SCALE)
    if alternate_coefficient:
        terms.extend(
            alternate_coefficient * presence[(operation.operation_id, resource_id)]
            for operation in problem.operations
            for resource_id in operation.alternate_resource_ids
        )
    return terms


def _objective_weights(problem: SchedulingProblem) -> dict[str, float]:
    objective = problem.objective
    if objective.strategy_id == "v1_delivery_flow_bottleneck":
        return {
            "tardiness": max(objective.tardiness_weight, 8.0),
            "makespan": max(objective.makespan_weight, 1.0),
            "alternate_resource": max(objective.alternate_resource_weight, 0.5),
        }
    if objective.strategy_id == "delivery_first":
        return {
            "tardiness": max(objective.tardiness_weight, 5.0),
            "makespan": objective.makespan_weight,
            "alternate_resource": objective.alternate_resource_weight,
        }
    if objective.strategy_id == "flow_first":
        return {
            "tardiness": objective.tardiness_weight,
            "makespan": max(objective.makespan_weight, 1.0),
            "alternate_resource": objective.alternate_resource_weight,
        }
    if objective.strategy_id == "bottleneck_protect":
        return {
            "tardiness": max(objective.tardiness_weight, 2.0),
            "makespan": objective.makespan_weight,
            "alternate_resource": max(objective.alternate_resource_weight, 1.0),
        }
    return {
        "tardiness": objective.tardiness_weight,
        "makespan": objective.makespan_weight,
        "alternate_resource": objective.alternate_resource_weight,
    }


def _advanced_capability_diagnostics(problem: SchedulingProblem) -> list[SolverDiagnostic]:
    objective_source = (
        "BuiltIn"
        if problem.objective.strategy_id in BUILT_IN_OBJECTIVE_STRATEGY_IDS
        else "Custom"
    )
    diagnostics = [
        SolverDiagnostic(
            severity="Info",
            code="ORTOOLS_OBJECTIVE_STRATEGY",
            message=(
                "OR-Tools CP-SAT objective strategy: "
                f"{problem.objective.strategy_id} ({objective_source})."
            ),
        )
    ]
    if objective_source == "Custom":
        diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_CUSTOM_OBJECTIVE_WEIGHTS_ENABLED",
                message="Custom objective weights are applied to CP-SAT.",
                entity_id=problem.objective.strategy_id,
            )
        )
    if problem.setup_transitions:
        diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_SETUP_TRANSITIONS_ENABLED",
                message="Sequence-dependent setup transitions are enabled.",
            )
        )
    if any(resource.capacity_units > 1 for resource in problem.resources):
        diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_PARALLEL_RESOURCE_CAPACITY_ENABLED",
                message="Parallel resource capacity units are enabled.",
            )
        )
    if any(resource.efficiency_percent != 100 for resource in problem.resources):
        diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_RESOURCE_EFFICIENCY_ENABLED",
                message="Resource efficiency adjusted operation durations.",
            )
        )
    if any(
        operation.earliest_start_at is not None or operation.latest_end_at is not None
        for operation in problem.operations
    ):
        diagnostics.append(
            SolverDiagnostic(
                severity="Info",
                code="ORTOOLS_OPERATION_TIME_WINDOWS_ENABLED",
                message="Operation time windows are enabled.",
            )
        )
    return diagnostics
