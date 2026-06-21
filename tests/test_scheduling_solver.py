from datetime import date, datetime, timedelta, timezone

import pytest

from sdbr.calendar_overrides import apply_calendar_overrides
from sdbr.planner_workbench import (
    MaintenanceWindow,
    Operation,
    Resource,
    Routing,
    SchedulingOrder,
    Shift,
    WorkCalendar,
)
from sdbr.scheduling_solver import (
    BaselineFiniteScheduler,
    CapacityBucket,
    FixedOperationAssignment,
    GurobiEngine,
    OperationRequirement,
    OrToolsEngine,
    PrecedenceConstraint,
    ResourceInput,
    SchedulingObjective,
    SchedulingOrderInput,
    SchedulingOptions,
    SchedulingProblem,
    SchedulingResult,
    SolverDiagnostic,
    SetupTransition,
    SimioValidationAdapter,
    build_capacity_buckets_from_resources,
    build_resource_inputs,
    build_scheduling_problem,
    create_solver_engine,
)


def test_ortools_engine_reports_unavailable_when_dependency_is_missing():
    problem = SchedulingProblem(
        problem_id="P-001",
        operations=[
            OperationRequirement(
                operation_id="OP-1",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            )
        ],
    )

    result = OrToolsEngine(available=False).solve(problem)

    assert result.status == "Unavailable"
    assert result.backend_id == "ortools"
    assert result.message == "OR-Tools backend is not installed or enabled."
    assert result.assignments == []


def test_ortools_engine_detects_installed_cp_sat_and_validates_inputs():
    assert OrToolsEngine().is_available().available is True

    missing_start = OrToolsEngine().solve(
        SchedulingProblem(
            problem_id="P-ORTOOLS-MISSING-START",
            operations=[
                OperationRequirement(
                    operation_id="OP-1",
                    order_id="WO-1",
                    resource_id="R-1",
                    duration_minutes=30,
                )
            ],
        )
    )
    assert missing_start.status == "Error"
    assert missing_start.diagnostics[0].code == "MISSING_SCHEDULE_START"

    duplicate = OperationRequirement(
        operation_id="OP-1",
        order_id="WO-1",
        resource_id="R-1",
        duration_minutes=30,
    )
    duplicate_result = OrToolsEngine().solve(
        SchedulingProblem(
            problem_id="P-ORTOOLS-DUPLICATE",
            schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
            operations=[duplicate, duplicate],
        )
    )
    assert duplicate_result.status == "Error"
    assert duplicate_result.diagnostics[0].code == "DUPLICATE_OPERATION_ID"


def test_ortools_engine_enforces_precedence_and_finite_resource_capacity():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-FINITE",
        schedule_start_at=start,
        operations=[
            OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 120),
            OperationRequirement("WO-2:CUT", "WO-2", "DRUM", 60),
            OperationRequirement("WO-1:ASM", "WO-1", "ASM", 30),
        ],
        resources=[
            ResourceInput("DRUM", "Drum", "FINITE", True),
            ResourceInput("ASM", "Assembly", "INFINITE", False),
        ],
        precedence_constraints=[
            PrecedenceConstraint("WO-1:CUT", "WO-1:ASM", 15)
        ],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    by_id = {item.operation_id: item for item in result.assignments}
    drum = sorted(
        (item for item in result.assignments if item.resource_id == "DRUM"),
        key=lambda item: item.start,
    )
    assert drum[0].end <= drum[1].start
    assert by_id["WO-1:ASM"].start >= by_id["WO-1:CUT"].end + timedelta(minutes=15)


def test_ortools_engine_selects_alternate_only_when_it_improves_schedule():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-ALTERNATE",
        schedule_start_at=start,
        operations=[
            OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 120),
            OperationRequirement(
                "WO-2:CUT", "WO-2", "DRUM", 120,
                alternate_resource_ids=["LASER"],
            ),
        ],
        resources=[
            ResourceInput("DRUM", "Drum", "FINITE", True),
            ResourceInput("LASER", "Laser", "FINITE", False),
        ],
    )

    result = OrToolsEngine().solve(problem)

    by_id = {item.operation_id: item for item in result.assignments}
    assert result.status == "Optimal"
    assert by_id["WO-2:CUT"].resource_id == "LASER"
    assert by_id["WO-1:CUT"].start == by_id["WO-2:CUT"].start

    single = SchedulingProblem(
        problem_id="P-ORTOOLS-PRIMARY",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-3:CUT", "WO-3", "DRUM", 120,
                alternate_resource_ids=["LASER"],
            )
        ],
        resources=problem.resources,
    )
    preferred = OrToolsEngine().solve(single)
    assert preferred.assignments[0].resource_id == "DRUM"


def test_ortools_engine_enforces_capacity_buckets_and_reports_infeasible():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    operation = OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 120)
    resource = ResourceInput("DRUM", "Drum", "FINITE", True)
    feasible = SchedulingProblem(
        problem_id="P-ORTOOLS-BUCKET",
        schedule_start_at=start,
        operations=[operation],
        resources=[resource],
        capacity_buckets=[
            CapacityBucket(
                "DRUM", start + timedelta(hours=2), start + timedelta(hours=4), 120
            )
        ],
    )
    result = OrToolsEngine().solve(feasible)
    assert result.status == "Optimal"
    assert result.assignments[0].start == start + timedelta(hours=2)
    assert result.assignments[0].end == start + timedelta(hours=4)

    infeasible = SchedulingProblem(
        problem_id="P-ORTOOLS-BUCKET-INFEASIBLE",
        schedule_start_at=start,
        operations=[operation],
        resources=[resource],
        capacity_buckets=[CapacityBucket("DRUM", start, start + timedelta(hours=2), 60)],
    )
    failed = OrToolsEngine().solve(infeasible)
    assert failed.status == "Infeasible"
    assert failed.diagnostics[-1].code == "ORTOOLS_INFEASIBLE"


def test_ortools_engine_respects_fixed_operation_start_and_resource():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    fixed_start = start + timedelta(hours=2)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-FIXED",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-1:CUT", "WO-1", "DRUM", 60,
                alternate_resource_ids=["LASER"],
            ),
            OperationRequirement("WO-2:CUT", "WO-2", "DRUM", 60),
        ],
        resources=[
            ResourceInput("DRUM", "Drum", "FINITE", True),
            ResourceInput("LASER", "Laser", "FINITE", False),
        ],
        fixed_assignments=[
            FixedOperationAssignment("WO-1:CUT", "LASER", fixed_start)
        ],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    by_id = {item.operation_id: item for item in result.assignments}
    assert by_id["WO-1:CUT"].resource_id == "LASER"
    assert by_id["WO-1:CUT"].start == fixed_start
    assert by_id["WO-1:CUT"].end == fixed_start + timedelta(minutes=60)


def test_ortools_engine_rejects_invalid_fixed_operation_assignment():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-FIXED-INVALID",
        schedule_start_at=start,
        operations=[OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 60)],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
        fixed_assignments=[
            FixedOperationAssignment("WO-1:CUT", "LASER", start)
        ],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Error"
    assert result.diagnostics[0].code == "FIXED_RESOURCE_NOT_ELIGIBLE"
    assert result.diagnostics[0].entity_id == "WO-1:CUT"


def test_ortools_engine_reports_overlapping_fixed_assignments_as_infeasible():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-FIXED-OVERLAP",
        schedule_start_at=start,
        operations=[
            OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 90),
            OperationRequirement("WO-2:CUT", "WO-2", "DRUM", 90),
        ],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
        fixed_assignments=[
            FixedOperationAssignment("WO-1:CUT", "DRUM", start),
            FixedOperationAssignment("WO-2:CUT", "DRUM", start),
        ],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Infeasible"
    assert result.diagnostics[-1].code == "ORTOOLS_INFEASIBLE"


def test_ortools_engine_uses_protected_due_and_returns_diagnostics():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-PROTECTED-DUE",
        schedule_start_at=start,
        operations=[
            OperationRequirement("BUFFERED:CUT", "BUFFERED", "DRUM", 120),
            OperationRequirement("URGENT:CUT", "URGENT", "DRUM", 120),
        ],
        orders=[
            SchedulingOrderInput(
                "BUFFERED", "FG-A", 1,
                datetime(2026, 6, 16, 14, tzinfo=timezone.utc),
                protected_due_at=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            ),
            SchedulingOrderInput(
                "URGENT", "FG-B", 1,
                datetime(2026, 6, 16, 11, tzinfo=timezone.utc),
            ),
        ],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
        objective=SchedulingObjective(makespan_weight=0.0),
        options=SchedulingOptions(solver_time_limit_seconds=5),
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    assert [item.order_id for item in result.assignments] == ["BUFFERED", "URGENT"]
    codes = {item.code for item in result.diagnostics}
    assert "ORTOOLS_TIME_LIMIT_CONFIGURED" in codes
    assert "ORTOOLS_CP_SAT_MODEL" in codes


def test_ortools_engine_enforces_sequence_dependent_setup_with_precedence():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-SETUP-PRECEDENCE",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-A:CUT", "WO-A", "DRUM", 60, setup_family="FAM-A"
            ),
            OperationRequirement(
                "WO-B:CUT", "WO-B", "DRUM", 60, setup_family="FAM-B"
            ),
        ],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
        precedence_constraints=[PrecedenceConstraint("WO-A:CUT", "WO-B:CUT")],
        setup_transitions=[SetupTransition("DRUM", "FAM-A", "FAM-B", 45)],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    by_id = {item.operation_id: item for item in result.assignments}
    assert by_id["WO-B:CUT"].start >= by_id["WO-A:CUT"].end + timedelta(minutes=45)
    assert "ORTOOLS_SETUP_TRANSITIONS_ENABLED" in {
        item.code for item in result.diagnostics
    }


def test_ortools_engine_chooses_lower_setup_sequence_for_makespan():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-SETUP-SEQUENCE",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-A:CUT", "WO-A", "DRUM", 60, setup_family="FAM-A"
            ),
            OperationRequirement(
                "WO-B:CUT", "WO-B", "DRUM", 60, setup_family="FAM-B"
            ),
        ],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
        setup_transitions=[
            SetupTransition("DRUM", "FAM-A", "FAM-B", 120),
            SetupTransition("DRUM", "FAM-B", "FAM-A", 0),
        ],
        objective=SchedulingObjective(makespan_weight=1.0),
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    ordered = sorted(result.assignments, key=lambda item: item.start)
    assert [item.operation_id for item in ordered] == ["WO-B:CUT", "WO-A:CUT"]
    assert ordered[1].start == ordered[0].end


def test_ortools_engine_does_not_add_setup_for_same_family_without_transition():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-SETUP-SAME-FAMILY",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-1:CUT", "WO-1", "DRUM", 60, setup_family="FAM-A"
            ),
            OperationRequirement(
                "WO-2:CUT", "WO-2", "DRUM", 60, setup_family="FAM-A"
            ),
        ],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
        setup_transitions=[SetupTransition("DRUM", "FAM-A", "FAM-B", 90)],
        objective=SchedulingObjective(makespan_weight=1.0),
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    ordered = sorted(result.assignments, key=lambda item: item.start)
    assert ordered[1].start == ordered[0].end


def test_ortools_engine_allows_parallel_units_on_finite_resource():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-PARALLEL-UNITS",
        schedule_start_at=start,
        operations=[
            OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 120),
            OperationRequirement("WO-2:CUT", "WO-2", "DRUM", 120),
        ],
        resources=[
            ResourceInput("DRUM", "Drum", "FINITE", True, capacity_units=2)
        ],
        objective=SchedulingObjective(makespan_weight=1.0),
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    assert {item.start for item in result.assignments} == {start}
    assert "ORTOOLS_PARALLEL_RESOURCE_CAPACITY_ENABLED" in {
        item.code for item in result.diagnostics
    }


def test_ortools_engine_applies_resource_efficiency_to_duration():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-EFFICIENCY",
        schedule_start_at=start,
        operations=[OperationRequirement("WO-1:CUT", "WO-1", "DRUM", 60)],
        resources=[
            ResourceInput("DRUM", "Drum", "FINITE", True, efficiency_percent=50)
        ],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Optimal"
    assert result.assignments[0].end == start + timedelta(minutes=120)
    assert "ORTOOLS_RESOURCE_EFFICIENCY_ENABLED" in {
        item.code for item in result.diagnostics
    }


def test_ortools_engine_enforces_operation_time_windows():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-TIME-WINDOW",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-1:CUT",
                "WO-1",
                "DRUM",
                120,
                earliest_start_at=start + timedelta(hours=1),
                latest_end_at=start + timedelta(hours=2),
            )
        ],
        resources=[ResourceInput("DRUM", "Drum", "FINITE", True)],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Infeasible"


def test_ortools_engine_rejects_setup_on_parallel_resource():
    start = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-ORTOOLS-PARALLEL-SETUP",
        schedule_start_at=start,
        operations=[
            OperationRequirement(
                "WO-A:CUT", "WO-A", "DRUM", 60, setup_family="FAM-A"
            ),
            OperationRequirement(
                "WO-B:CUT", "WO-B", "DRUM", 60, setup_family="FAM-B"
            ),
        ],
        resources=[
            ResourceInput("DRUM", "Drum", "FINITE", True, capacity_units=2)
        ],
        setup_transitions=[SetupTransition("DRUM", "FAM-A", "FAM-B", 30)],
    )

    result = OrToolsEngine().solve(problem)

    assert result.status == "Error"
    assert result.diagnostics[0].code == "SETUP_NOT_SUPPORTED_FOR_PARALLEL_RESOURCE"


def test_gurobi_engine_reports_unavailable_when_dependency_or_license_is_missing():
    problem = SchedulingProblem(
        problem_id="P-002",
        operations=[
            OperationRequirement(
                operation_id="OP-1",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            )
        ],
    )

    result = GurobiEngine(available=False).solve(problem)

    assert result.status == "Unavailable"
    assert result.backend_id == "gurobi"
    assert result.message == "Gurobi backend is not installed, enabled, or licensed."
    assert result.assignments == []
    assert result.diagnostics == [
        SolverDiagnostic(
            severity="Warning",
            code="GUROBI_UNAVAILABLE",
            message="Gurobi backend is not installed, enabled, or licensed.",
            entity_id=None,
        )
    ]


def test_gurobi_engine_exposes_availability_contract():
    availability = GurobiEngine(available=False).is_available()

    assert availability.backend_id == "gurobi"
    assert availability.available is False
    assert availability.status == "Unavailable"
    assert availability.message == "Gurobi backend is not installed, enabled, or licensed."


def test_gurobi_engine_solves_fixed_resource_finite_capacity_model_when_available():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-SOLVE",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="WO-2:CUT",
                order_id="WO-2",
                resource_id="WC-DRUM",
                duration_minutes=60,
            ),
        ],
        orders=[],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            )
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assert result.status in {"Optimal", "Feasible"}
    assert len(result.assignments) == 2
    first, second = sorted(result.assignments, key=lambda item: item.start)
    assert first.end <= second.start
    assert {item.operation_id for item in result.assignments} == {"WO-1:CUT", "WO-2:CUT"}


def test_gurobi_engine_enforces_precedence_when_available():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-PRECEDENCE",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="WO-1:ASM",
                order_id="WO-1",
                resource_id="WC-ASM",
                duration_minutes=60,
            ),
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            ),
            ResourceInput(
                resource_id="WC-ASM",
                name="Assembly Cell",
                capacity_mode="INFINITE",
                is_constraint=False,
            ),
        ],
        precedence_constraints=[
            PrecedenceConstraint(
                before_operation_id="WO-1:CUT",
                after_operation_id="WO-1:ASM",
            )
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assignments = {item.operation_id: item for item in result.assignments}
    assert result.status in {"Optimal", "Feasible"}
    assert assignments["WO-1:CUT"].end <= assignments["WO-1:ASM"].start


def test_gurobi_engine_selects_alternate_resource_to_reduce_makespan_when_available():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-ALT-RESOURCE",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="WO-2:CUT",
                order_id="WO-2",
                resource_id="WC-DRUM",
                alternate_resource_ids=["WC-LASER"],
                duration_minutes=120,
            ),
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            ),
            ResourceInput(
                resource_id="WC-LASER",
                name="Laser Cell",
                capacity_mode="FINITE",
                is_constraint=False,
            ),
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assignments = {item.operation_id: item for item in result.assignments}
    assert result.status in {"Optimal", "Feasible"}
    assert assignments["WO-1:CUT"].resource_id == "WC-DRUM"
    assert assignments["WO-2:CUT"].resource_id == "WC-LASER"
    assert assignments["WO-1:CUT"].start == assignments["WO-2:CUT"].start


def test_gurobi_engine_prefers_primary_resource_when_alternate_has_no_schedule_benefit():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-PRIMARY-PREFERRED",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                alternate_resource_ids=["WC-LASER"],
                duration_minutes=120,
            )
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            ),
            ResourceInput(
                resource_id="WC-LASER",
                name="Laser Cell",
                capacity_mode="FINITE",
                is_constraint=False,
            ),
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assert result.assignments[0].resource_id == "WC-DRUM"


def test_gurobi_engine_can_disable_alternate_resource_penalty_when_requested():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-ALT-NO-PENALTY",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                alternate_resource_ids=["WC-LASER"],
                duration_minutes=120,
            )
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            ),
            ResourceInput(
                resource_id="WC-LASER",
                name="Laser Cell",
                capacity_mode="FINITE",
                is_constraint=False,
            ),
        ],
        objective=SchedulingObjective(alternate_resource_weight=0.0),
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assert result.status in {"Optimal", "Feasible"}


def test_gurobi_engine_places_finite_operations_inside_capacity_buckets_when_available():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-BUCKET",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="WO-2:CUT",
                order_id="WO-2",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            )
        ],
        capacity_buckets=[
            CapacityBucket(
                resource_id="WC-DRUM",
                bucket_start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
                bucket_end=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
                capacity_minutes=120,
            ),
            CapacityBucket(
                resource_id="WC-DRUM",
                bucket_start=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
                bucket_end=datetime(2026, 6, 16, 12, tzinfo=timezone.utc),
                capacity_minutes=120,
            ),
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assert result.status in {"Optimal", "Feasible"}
    assert sorted((item.start, item.end) for item in result.assignments) == [
        (
            datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
            datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            datetime(2026, 6, 16, 12, tzinfo=timezone.utc),
        ),
    ]


def test_gurobi_engine_reports_infeasible_when_capacity_bucket_cannot_fit_operation():
    pytest.importorskip("gurobipy")
    problem = SchedulingProblem(
        problem_id="P-GUROBI-BUCKET-INFEASIBLE",
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        operations=[
            OperationRequirement(
                operation_id="WO-1:CUT",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            )
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            )
        ],
        capacity_buckets=[
            CapacityBucket(
                resource_id="WC-DRUM",
                bucket_start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
                bucket_end=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
                capacity_minutes=60,
            )
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assert result.status == "Infeasible"
    assert result.diagnostics[0].code == "GUROBI_NON_FEASIBLE_STATUS"


def test_create_solver_engine_returns_named_solver_contracts():
    assert create_solver_engine("ortools").backend_id == "ortools"
    assert create_solver_engine("gurobi").backend_id == "gurobi"


def test_simio_validation_adapter_exports_problem_operation_rows():
    problem = SchedulingProblem(
        problem_id="P-SIM",
        operations=[
            OperationRequirement(
                operation_id="OP-1",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            )
        ],
    )

    payload = SimioValidationAdapter().export_problem(problem)

    assert payload == {
        "ProblemID": "P-SIM",
        "Format": "operation_rows",
        "Rows": [
            {
                "OperationID": "OP-1",
                "OrderID": "WO-1",
                "ResourceID": "WC-DRUM",
                "DurationMinutes": 120,
                "RoutingID": "PRIMARY",
            }
        ],
    }


def test_build_scheduling_problem_expands_orders_and_routings_to_operations():
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=2,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=120,
                sequence=1,
            ),
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=60,
                sequence=2,
            ),
        ],
    )

    problem = build_scheduling_problem(
        problem_id="P-BUILD",
        orders=[order],
        routings=[routing],
    )

    assert problem.problem_id == "P-BUILD"
    assert problem.orders[0].order_id == "WO-1"
    assert problem.orders[0].due_at == datetime(2026, 6, 20, 8, tzinfo=timezone.utc)
    assert problem.precedence_constraints == [
        PrecedenceConstraint(
            before_operation_id="WO-1:CUT",
            after_operation_id="WO-1:ASM",
            min_lag_minutes=0,
        ),
    ]
    assert problem.operations == [
        OperationRequirement(
            operation_id="WO-1:CUT",
            order_id="WO-1",
            resource_id="WC-DRUM",
            duration_minutes=240,
            routing_id="PRIMARY",
            setup_family="FG-A",
        ),
        OperationRequirement(
            operation_id="WO-1:ASM",
            order_id="WO-1",
            resource_id="WC-ASM",
            duration_minutes=120,
            routing_id="PRIMARY",
            setup_family="FG-A",
        ),
    ]


def test_build_scheduling_problem_uses_time_buffer_for_protected_due_and_rope_release():
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )
    routing = Routing(
        product_id="FG-A",
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=120,
                sequence=1,
            ),
            Operation(
                operation_id="ASM",
                resource_id="WC-ASM",
                duration_minutes=60,
                sequence=2,
            ),
        ],
    )

    problem = build_scheduling_problem(
        problem_id="P-BUFFERED-DUE",
        orders=[order],
        routings=[routing],
        time_buffer_minutes=240,
    )

    assert problem.orders[0].due_at == datetime(2026, 6, 20, 8, tzinfo=timezone.utc)
    assert problem.orders[0].protected_due_at == datetime(
        2026, 6, 20, 4, tzinfo=timezone.utc
    )
    assert problem.orders[0].release_not_before == datetime(
        2026, 6, 20, 1, tzinfo=timezone.utc
    )


def test_gurobi_engine_prioritizes_protected_due_date_when_available():
    pytest.importorskip("gurobipy")
    schedule_start_at = datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    problem = SchedulingProblem(
        problem_id="P-PROTECTED-DUE",
        schedule_start_at=schedule_start_at,
        operations=[
            OperationRequirement(
                operation_id="WO-BUFFERED:CUT",
                order_id="WO-BUFFERED",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="WO-URGENT:CUT",
                order_id="WO-URGENT",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
        ],
        orders=[
            SchedulingOrderInput(
                order_id="WO-BUFFERED",
                product_id="FG-A",
                quantity=1,
                due_at=datetime(2026, 6, 16, 14, tzinfo=timezone.utc),
                protected_due_at=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            ),
            SchedulingOrderInput(
                order_id="WO-URGENT",
                product_id="FG-B",
                quantity=1,
                due_at=datetime(2026, 6, 16, 11, tzinfo=timezone.utc),
            ),
        ],
        resources=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            )
        ],
        capacity_buckets=[
            CapacityBucket(
                resource_id="WC-DRUM",
                bucket_start=schedule_start_at,
                bucket_end=datetime(2026, 6, 16, 16, tzinfo=timezone.utc),
                capacity_minutes=480,
            )
        ],
    )

    result = GurobiEngine(available=True).solve(problem)

    if result.status == "Unavailable":
        pytest.skip(result.message)
    assert result.status in {"Optimal", "Feasible"}
    assert [assignment.order_id for assignment in result.assignments] == [
        "WO-BUFFERED",
        "WO-URGENT",
    ]


def test_build_scheduling_problem_uses_primary_route_by_default():
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
    )
    primary = Routing(
        product_id="FG-A",
        routing_id="PRIMARY",
        is_primary=True,
        operations=[
            Operation(
                operation_id="CUT",
                resource_id="WC-DRUM",
                duration_minutes=120,
                sequence=1,
            )
        ],
    )
    alternate = Routing(
        product_id="FG-A",
        routing_id="ALT",
        is_primary=False,
        operations=[
            Operation(
                operation_id="LASER",
                resource_id="WC-LASER",
                duration_minutes=90,
                sequence=1,
            )
        ],
    )

    problem = build_scheduling_problem(
        problem_id="P-PRIMARY",
        orders=[order],
        routings=[alternate, primary],
    )

    assert [operation.resource_id for operation in problem.operations] == ["WC-DRUM"]


def test_build_scheduling_problem_accepts_resource_inputs_and_capacity_buckets():
    order = SchedulingOrder(
        order_id="WO-1",
        product_id="FG-A",
        quantity=1,
        due_date=datetime(2026, 6, 20, 8, tzinfo=timezone.utc),
        target_start_date=date(2026, 6, 16),
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
    capacity_bucket = CapacityBucket(
        resource_id="WC-DRUM",
        bucket_start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        bucket_end=datetime(2026, 6, 16, 16, tzinfo=timezone.utc),
        capacity_minutes=480,
    )

    problem = build_scheduling_problem(
        problem_id="P-RESOURCE",
        orders=[order],
        routings=[routing],
        resource_inputs=[
            ResourceInput(
                resource_id="WC-DRUM",
                name="Constraint Cutter",
                capacity_mode="FINITE",
                is_constraint=True,
            )
        ],
        capacity_buckets=[capacity_bucket],
        schedule_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    assert problem.schedule_start_at == datetime(2026, 6, 16, 8, tzinfo=timezone.utc)
    assert problem.resources == [
        ResourceInput(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            capacity_mode="FINITE",
            is_constraint=True,
        )
    ]
    assert problem.capacity_buckets == [capacity_bucket]


def test_build_resource_inputs_marks_constraints_as_finite_and_non_constraints_as_infinite():
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
            daily_capacity_minutes={date(2026, 6, 16): 960},
        ),
    ]

    assert build_resource_inputs(resources) == [
        ResourceInput(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            capacity_mode="FINITE",
            is_constraint=True,
        ),
        ResourceInput(
            resource_id="WC-ASM",
            name="Assembly Cell",
            capacity_mode="INFINITE",
            is_constraint=False,
        ),
    ]


def test_build_capacity_buckets_from_resources_expands_daily_capacity():
    resources = [
        Resource(
            resource_id="WC-DRUM",
            name="Constraint Cutter",
            is_constraint=True,
            daily_capacity_minutes={
                date(2026, 6, 16): 480,
            },
        )
    ]

    buckets = build_capacity_buckets_from_resources(
        resources,
        tzinfo=timezone.utc,
    )

    assert buckets == [
        CapacityBucket(
            resource_id="WC-DRUM",
            bucket_start=datetime(2026, 6, 16, 0, tzinfo=timezone.utc),
            bucket_end=datetime(2026, 6, 17, 0, tzinfo=timezone.utc),
            capacity_minutes=480,
        )
    ]


def test_build_capacity_buckets_from_resources_uses_calendar_shifts_and_maintenance():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 999},
        calendar=WorkCalendar(
            calendar_id="CAL-DRUM",
            working_weekdays={0, 1, 2, 3, 4},
            shifts=[Shift(name="Day", start=datetime.strptime("08:00", "%H:%M").time(), end=datetime.strptime("12:00", "%H:%M").time())],
            maintenance_windows=[
                MaintenanceWindow(
                    start=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
                    end=datetime(2026, 6, 16, 11, tzinfo=timezone.utc),
                )
            ],
            holidays=set(),
        ),
    )

    buckets = build_capacity_buckets_from_resources(
        [resource],
        tzinfo=timezone.utc,
    )

    assert buckets == [
        CapacityBucket(
            resource_id="WC-DRUM",
            bucket_start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
            bucket_end=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            capacity_minutes=120,
        ),
        CapacityBucket(
            resource_id="WC-DRUM",
            bucket_start=datetime(2026, 6, 16, 11, tzinfo=timezone.utc),
            bucket_end=datetime(2026, 6, 16, 12, tzinfo=timezone.utc),
            capacity_minutes=60,
        ),
    ]


def test_calendar_overrides_apply_maintenance_overtime_and_temporary_windows():
    resource = Resource(
        resource_id="WC-DRUM",
        name="Constraint Cutter",
        is_constraint=True,
        daily_capacity_minutes={date(2026, 6, 16): 999},
        calendar=WorkCalendar(
            calendar_id="CAL-DRUM",
            working_weekdays={0, 1, 2, 3, 4},
            shifts=[
                Shift(
                    name="Day",
                    start=datetime.strptime("08:00", "%H:%M").time(),
                    end=datetime.strptime("12:00", "%H:%M").time(),
                )
            ],
            maintenance_windows=[],
            holidays=set(),
        ),
    )

    application = apply_calendar_overrides(
        resources=[resource],
        overrides=[
            {
                "OverrideID": "CAL-OVR-MAINT",
                "CalendarID": "CAL-DRUM",
                "OverrideType": "ExclusionOrMaintenance",
                "EffectiveStartAt": "2026-06-16T09:00:00+00:00",
                "EffectiveEndAt": "2026-06-16T10:00:00+00:00",
                "Status": "Active",
            },
            {
                "OverrideID": "CAL-OVR-OT",
                "CalendarID": "CAL-DRUM",
                "ResourceID": "WC-DRUM",
                "OverrideType": "Overtime",
                "EffectiveStartAt": "2026-06-16T06:00:00+00:00",
                "EffectiveEndAt": "2026-06-16T08:00:00+00:00",
                "CapacityDeltaMinutes": 90,
                "Status": "Active",
            },
            {
                "OverrideID": "CAL-OVR-SHIFT",
                "CalendarID": "CAL-DRUM",
                "OverrideType": "TemporaryShiftOverride",
                "EffectiveStartAt": "2026-06-16T13:00:00+00:00",
                "EffectiveEndAt": "2026-06-16T15:00:00+00:00",
                "Status": "Active",
            },
        ],
    )

    buckets = build_capacity_buckets_from_resources(
        application.resources,
        tzinfo=timezone.utc,
    )

    assert CapacityBucket(
        resource_id="WC-DRUM",
        bucket_start=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        bucket_end=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
        capacity_minutes=60,
    ) in buckets
    assert CapacityBucket(
        resource_id="WC-DRUM",
        bucket_start=datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
        bucket_end=datetime(2026, 6, 16, 12, tzinfo=timezone.utc),
        capacity_minutes=120,
    ) in buckets
    assert CapacityBucket(
        resource_id="WC-DRUM",
        bucket_start=datetime(2026, 6, 16, 6, tzinfo=timezone.utc),
        bucket_end=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        capacity_minutes=90,
    ) in buckets
    assert CapacityBucket(
        resource_id="WC-DRUM",
        bucket_start=datetime(2026, 6, 16, 13, tzinfo=timezone.utc),
        bucket_end=datetime(2026, 6, 16, 15, tzinfo=timezone.utc),
        capacity_minutes=120,
    ) in buckets
    assert {diagnostic.code for diagnostic in application.diagnostics} == {
        "CALENDAR_OVERRIDES_APPLIED"
    }


def test_calendar_override_reports_not_applied_when_no_resource_matches():
    application = apply_calendar_overrides(
        resources=[],
        overrides=[
            {
                "OverrideID": "CAL-OVR-NOMATCH",
                "CalendarID": "CAL-MISSING",
                "OverrideType": "Overtime",
                "EffectiveStartAt": "2026-06-16T06:00:00+00:00",
                "EffectiveEndAt": "2026-06-16T08:00:00+00:00",
                "Status": "Active",
            }
        ],
    )

    assert application.applied_overrides == []
    assert application.diagnostics[0].code == "CALENDAR_OVERRIDE_NOT_APPLIED"
    assert application.diagnostics[0].entity_id == "CAL-OVR-NOMATCH"


def test_baseline_finite_scheduler_serializes_operations_on_same_resource():
    problem = SchedulingProblem(
        problem_id="P-FINITE",
        operations=[
            OperationRequirement(
                operation_id="OP-1",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="OP-2",
                order_id="WO-2",
                resource_id="WC-DRUM",
                duration_minutes=60,
            ),
        ],
    )

    result = BaselineFiniteScheduler().solve(
        problem,
        start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    assert result.status == "Feasible"
    assert [(item.operation_id, item.start, item.end) for item in result.assignments] == [
        (
            "OP-1",
            datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
            datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
        ),
        (
            "OP-2",
            datetime(2026, 6, 16, 10, tzinfo=timezone.utc),
            datetime(2026, 6, 16, 11, tzinfo=timezone.utc),
        ),
    ]
    assert [item.order_id for item in result.assignments] == ["WO-1", "WO-2"]


def test_baseline_finite_scheduler_allows_parallel_work_on_different_resources():
    problem = SchedulingProblem(
        problem_id="P-PARALLEL",
        operations=[
            OperationRequirement(
                operation_id="OP-1",
                order_id="WO-1",
                resource_id="WC-DRUM",
                duration_minutes=120,
            ),
            OperationRequirement(
                operation_id="OP-2",
                order_id="WO-2",
                resource_id="WC-ASM",
                duration_minutes=60,
            ),
        ],
    )

    result = BaselineFiniteScheduler().solve(
        problem,
        start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    assert [(item.operation_id, item.start) for item in result.assignments] == [
        ("OP-1", datetime(2026, 6, 16, 8, tzinfo=timezone.utc)),
        ("OP-2", datetime(2026, 6, 16, 8, tzinfo=timezone.utc)),
    ]
