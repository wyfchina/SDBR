# CP-SAT Solver Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OR-Tools CP-SAT the only active solver for new Planning Runs and replans while preserving historical Gurobi results and matching the currently verified Gurobi scheduling constraints.

**Architecture:** Keep `SchedulingProblem` and `SchedulingResult` as the solver-neutral boundary. Implement CP-SAT in a focused solver module, route product execution through an explicit active-solver policy, then migrate seeded scenarios and UI capability metadata without changing schedule-output, release, or publication contracts.

**Tech Stack:** Python 3.11+, OR-Tools 9.15 CP-SAT, FastAPI, pytest, vanilla HTML/CSS/JavaScript, SQLite state store.

---

## File Map

- Create `sdbr/cp_sat_solver.py`: CP-SAT model construction, solve, status mapping, and diagnostics.
- Modify `sdbr/scheduling_solver.py`: engine adapter, shared validation/helpers, factory behavior, paused Gurobi product status.
- Modify `sdbr/api.py`: active-solver enforcement for Planning Run and replan execution.
- Modify `sdbr/planning_run_view.py`: CP-SAT available and Gurobi paused capability metadata.
- Modify `sdbr/administration_view.py`: solver administration status.
- Modify `sdbr/test_data.py`: seeded Runs use `ortools`.
- Modify `sdbr/web/planner-workbench.html`: CP-SAT selected; Gurobi disabled.
- Modify `sdbr/web/planner-workbench.js`: CP-SAT capability detection, payloads, prompts, and translations.
- Modify `docs/backend-specification.md`: authoritative `BE-SOLVER-*` status, acceptance evidence, and changelog.
- Modify `docs/ui-specification.md`: `UI-RUN-002` and `UI-ADMIN-002` solver-state change and a new confirmation record.
- Modify `tests/test_scheduling_solver.py`: CP-SAT parity tests.
- Modify `tests/test_api.py`: active-solver policy, Planning Run, replan, capability, and UI tests.
- Modify `tests/test_business_closure.py`: CP-SAT end-to-end business closure.
- Modify `tests/test_test_data.py`: seeded solver assertions.

### Task 1: Change the authoritative capability boundary

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

- [ ] **Step 1: Update backend solver statuses before code**

Change `BE-SOLVER-002` to `[PAUSED]` with evidence noting that code and historical reads remain, but new product execution is disabled. Change `BE-SOLVER-009` from `[PAUSED]` to `[PARTIAL]` because the adapter skeleton and installed dependency exist but parity tests do not yet pass. Update the architecture text and roadmap so CP-SAT is active and Gurobi/Simio are paused.

- [ ] **Step 2: Update UI solver acceptance conditions before code**

In `UI-RUN-002` require `OR-Tools CP-SAT` to be selected by default and require Gurobi to display `已暂停 / Paused`. In `UI-ADMIN-002` require the same capability truth. Add a new acceptance unit after unit 9 for this changed behavior with status `开发中`; do not alter the earlier user-confirmed historical records.

- [ ] **Step 3: Record dated specification changes**

Increment the backend and UI document versions and add 2026-06-19 changelog rows citing `BE-SOLVER-002`, `BE-SOLVER-009`, `UI-RUN-002`, and `UI-ADMIN-002`.

- [ ] **Step 4: Verify the documents contain no contradictory active-engine statements**

Run:

```powershell
rg -n "Gurobi 可用|OR-Tools.*暂停|BE-SOLVER-002|BE-SOLVER-009|UI-RUN-002|UI-ADMIN-002" docs/backend-specification.md docs/ui-specification.md
```

Expected: historical records remain clearly historical; current capability sections say CP-SAT active and Gurobi paused.

- [ ] **Step 5: Commit the specification boundary**

```powershell
git add docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: switch active scheduling engine to cp-sat"
```

### Task 2: Establish CP-SAT engine availability and validation

**Files:**
- Create: `sdbr/cp_sat_solver.py`
- Modify: `sdbr/scheduling_solver.py`
- Modify: `tests/test_scheduling_solver.py`

- [ ] **Step 1: Write failing availability and validation tests**

Add tests that require automatic dependency detection and solver-neutral input diagnostics:

```python
def test_ortools_engine_is_available_when_cp_sat_is_installed():
    availability = OrToolsEngine().is_available()
    assert availability.available is True
    assert availability.status == "Available"


def test_ortools_engine_requires_schedule_start():
    result = OrToolsEngine().solve(SchedulingProblem(problem_id="P", operations=[]))
    assert result.status == "Error"
    assert result.diagnostics[0].code == "MISSING_SCHEDULE_START"


def test_ortools_engine_rejects_duplicate_operation_ids():
    problem = scheduling_problem_with_duplicate_operation_ids()
    result = OrToolsEngine().solve(problem)
    assert result.status == "Error"
    assert result.diagnostics[0].code == "DUPLICATE_OPERATION_ID"
```

- [ ] **Step 2: Run the tests and confirm the current skeleton fails**

Run:

```powershell
pytest tests/test_scheduling_solver.py -k "ortools_engine_is_available or ortools_engine_requires or ortools_engine_rejects" -q
```

Expected: FAIL because `OrToolsEngine()` defaults unavailable and returns `NotImplemented` when forced available.

- [ ] **Step 3: Add the focused CP-SAT module boundary**

Create `sdbr/cp_sat_solver.py` with a solver function that imports OR-Tools lazily and returns the existing domain result:

```python
def solve_cp_sat(problem: SchedulingProblem) -> SchedulingResult:
    validation_error = validate_scheduling_problem(problem, backend_id="ortools")
    if validation_error is not None:
        return validation_error
    from ortools.sat.python import cp_model
    return _build_and_solve(problem, cp_model)
```

Move or expose shared validation in `scheduling_solver.py` so Gurobi and CP-SAT use identical `MISSING_SCHEDULE_START` and `DUPLICATE_OPERATION_ID` semantics without importing each other.

- [ ] **Step 4: Make `OrToolsEngine` detect and invoke CP-SAT**

Use `available: bool | None = None`, detect `ortools.sat.python.cp_model`, and invoke `solve_cp_sat`. Preserve an explicit `available=False` path for unavailable-contract tests.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
pytest tests/test_scheduling_solver.py -k "ortools" -q
```

Expected: availability and validation tests PASS; parity tests added in later tasks are not yet present.

- [ ] **Step 6: Commit availability and validation**

```powershell
git add sdbr/cp_sat_solver.py sdbr/scheduling_solver.py tests/test_scheduling_solver.py
git commit -m "feat: establish cp-sat solver adapter"
```

### Task 3: Port resource assignment, precedence, and finite capacity

**Files:**
- Modify: `sdbr/cp_sat_solver.py`
- Modify: `tests/test_scheduling_solver.py`

- [ ] **Step 1: Write failing parity tests**

Add CP-SAT versions of the existing fixed-resource, precedence, alternate-resource, and infinite-resource tests. Assert business invariants rather than matching a Gurobi row order:

```python
def test_ortools_engine_enforces_precedence_and_finite_capacity():
    result = OrToolsEngine().solve(problem_with_precedence_and_shared_constraint())
    assert result.status == "Optimal"
    by_id = {item.operation_id: item for item in result.assignments}
    assert by_id["OP-2"].start >= by_id["OP-1"].end
    assert assignments_do_not_overlap(result.assignments, resource_id="DRUM-1")


def test_ortools_engine_selects_exactly_one_eligible_resource():
    result = OrToolsEngine().solve(problem_with_useful_alternate_resource())
    assert result.status == "Optimal"
    assert {item.operation_id for item in result.assignments} == {"OP-1", "OP-2"}
    assert all(item.resource_id in {"PRIMARY", "ALTERNATE"} for item in result.assignments)
```

- [ ] **Step 2: Run and verify the tests fail for missing model behavior**

```powershell
pytest tests/test_scheduling_solver.py -k "ortools_engine_enforces_precedence or ortools_engine_selects_exactly" -q
```

Expected: FAIL because no CP-SAT variables or constraints have been built.

- [ ] **Step 3: Implement integer time and optional intervals**

For every operation, create shared integer start/end variables. For each eligible resource create a presence Boolean and optional interval, then require exactly one presence:

```python
presence[(operation_id, resource_id)] = model.new_bool_var(name)
intervals[(operation_id, resource_id)] = model.new_optional_interval_var(
    start[operation_id], duration, end[operation_id],
    presence[(operation_id, resource_id)], interval_name,
)
model.add_exactly_one(
    presence[(operation_id, resource_id)]
    for resource_id in operation.eligible_resource_ids
)
```

- [ ] **Step 4: Implement precedence and finite-resource no-overlap**

Add precedence using shared start/end variables. Group optional intervals by finite resource and call `model.add_no_overlap(...)`. Do not add no-overlap for resources classified as infinite.

- [ ] **Step 5: Extract selected assignments**

Return one `OperationAssignment` per operation using `solver.value(presence)` and minute offsets from `schedule_start_at`. Sort by `(start, end, operation_id)` to preserve result stability.

- [ ] **Step 6: Run parity tests**

```powershell
pytest tests/test_scheduling_solver.py -k "ortools" -q
```

Expected: resource, precedence, alternate-resource, and non-overlap tests PASS.

- [ ] **Step 7: Commit core constraints**

```powershell
git add sdbr/cp_sat_solver.py tests/test_scheduling_solver.py
git commit -m "feat: port finite scheduling constraints to cp-sat"
```

### Task 4: Port capacity buckets, objectives, limits, and diagnostics

**Files:**
- Modify: `sdbr/cp_sat_solver.py`
- Modify: `sdbr/scheduling_solver.py`
- Modify: `tests/test_scheduling_solver.py`

- [ ] **Step 1: Write failing capacity-bucket tests**

Add tests requiring an operation to select one legal bucket on its selected finite resource, remain inside the bucket bounds, and report `Infeasible` when no bucket can fit it.

- [ ] **Step 2: Write failing objective and status tests**

Add tests for protected due-date priority, primary-resource preference when the alternate gives no schedule benefit, configured time-limit diagnostics, and explicit status mapping:

```python
assert any(d.code == "ORTOOLS_TIME_LIMIT_CONFIGURED" for d in result.diagnostics)
assert any(d.code == "ORTOOLS_CP_SAT_MODEL" for d in result.diagnostics)
```

- [ ] **Step 3: Run and verify expected failures**

```powershell
pytest tests/test_scheduling_solver.py -k "ortools and (bucket or protected or time_limit or primary_resource)" -q
```

Expected: FAIL because buckets, weighted objective, and diagnostics are missing.

- [ ] **Step 4: Implement bucket choices and capacity**

For each operation/resource pair on a finite resource, create bucket-choice Booleans only for buckets whose span and capacity can fit the operation. Require their sum to equal the resource presence. Enforce start/end bounds with `only_enforce_if(choice)` and add `sum(duration * choice) <= bucket.capacity_minutes` per bucket.

- [ ] **Step 5: Implement the integer weighted objective**

Use one fixed objective scale of 1000. Convert each non-negative configured weight with `round(weight * scale)` and reject negative weights. Build order completion, non-negative lateness, makespan, and alternate-presence terms. Minimize their weighted sum.

- [ ] **Step 6: Implement CP-SAT parameters and status mapping**

Set `solver.parameters.max_time_in_seconds` when configured. Map `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, and `MODEL_INVALID` to the unified statuses in the design, and return `solver.objective_value` when a solution exists.

- [ ] **Step 7: Run all solver tests**

```powershell
pytest tests/test_scheduling_solver.py -q
```

Expected: all CP-SAT tests PASS; existing Gurobi compatibility tests remain PASS or skip only when their external dependency/license is unavailable.

- [ ] **Step 8: Commit parity completion**

```powershell
git add sdbr/cp_sat_solver.py sdbr/scheduling_solver.py tests/test_scheduling_solver.py
git commit -m "feat: complete cp-sat parity model"
```

### Task 5: Enforce CP-SAT as the active product solver

**Files:**
- Modify: `sdbr/api.py`
- Modify: `sdbr/planning_run_view.py`
- Modify: `sdbr/administration_view.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_replanning.py`

- [ ] **Step 1: Write failing API policy tests**

Require capability endpoints to report CP-SAT available and Gurobi paused. Require creation/execution of a new Gurobi Planning Run and Gurobi replan to return a structured conflict such as `SolverBackendPaused`. Require `ortools` execution to proceed.

- [ ] **Step 2: Run policy tests and verify they fail**

```powershell
pytest tests/test_api.py tests/test_replanning.py -k "solver and (paused or ortools or replan)" -q
```

Expected: FAIL because API and replan code currently require Gurobi.

- [ ] **Step 3: Centralize active-solver policy**

Define product constants in the solver boundary:

```python
ACTIVE_SOLVER_BACKEND_ID = "ortools"
PAUSED_SOLVER_BACKEND_IDS = frozenset({"gurobi"})
```

Use these constants in Planning Run creation/execution and approved-replan execution. Return a structured 409 response for paused backends; do not mutate completed historical runs.

- [ ] **Step 4: Switch capability read models**

`planning_run_view.py` and `administration_view.py` must expose CP-SAT as `Available` and selectable, Gurobi as `Paused` and non-selectable, and Simio unchanged as unavailable.

- [ ] **Step 5: Migrate replan defaults and validation**

Replace the hard-coded `Literal["gurobi"]` and “must use gurobi” checks with `ortools` and the centralized policy. Preserve solver backend ID in audit and schedule output.

- [ ] **Step 6: Run API and replan tests**

```powershell
pytest tests/test_api.py tests/test_replanning.py -q
```

Expected: active-solver and historical-compatibility tests PASS.

- [ ] **Step 7: Commit product policy**

```powershell
git add sdbr/api.py sdbr/planning_run_view.py sdbr/administration_view.py sdbr/scheduling_solver.py tests/test_api.py tests/test_replanning.py
git commit -m "feat: make cp-sat the active product solver"
```

### Task 6: Migrate seeded business closure to CP-SAT

**Files:**
- Modify: `sdbr/test_data.py`
- Modify: `tests/test_test_data.py`
- Modify: `tests/test_business_closure.py`

- [ ] **Step 1: Write failing seed and closure assertions**

Change expected `SolverBackendID` to `ortools` and assert completed schedules also report `ortools`. Keep the three release outcomes unchanged: baseline has ready candidates, shortage has `MATERIAL_SHORTAGE`, and WIP has `WIP_LIMIT_EXCEEDED`.

- [ ] **Step 2: Run and verify failures against Gurobi-seeded data**

```powershell
pytest tests/test_test_data.py tests/test_business_closure.py -q
```

Expected: FAIL because seeded runs and explicit test payloads still use `gurobi`.

- [ ] **Step 3: Switch all current test scenario runs to CP-SAT**

Update `TST-RUN-BASELINE-001`, `TST-RUN-MATERIAL-SHORTAGE-001`, `TST-RUN-WIP-LIMIT-001`, and dynamically created closure runs to `SolverBackendID: "ortools"`.

- [ ] **Step 4: Run closure tests**

```powershell
pytest tests/test_test_data.py tests/test_business_closure.py -q
```

Expected: PASS with CP-SAT `Completed/Optimal` or `Completed/Feasible` results and unchanged downstream release semantics.

- [ ] **Step 5: Commit test-data migration**

```powershell
git add sdbr/test_data.py tests/test_test_data.py tests/test_business_closure.py
git commit -m "test: migrate planning closure scenarios to cp-sat"
```

### Task 7: Switch the planner UI capability truth

**Files:**
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing UI contract tests**

Require `solver-ortools` to be enabled and checked, `solver-gurobi` to be disabled, creation payloads to use `ortools`, and Chinese/English text to identify CP-SAT and Gurobi paused status. Require the execution confirmation prompt to avoid saying it will call Gurobi.

- [ ] **Step 2: Run and verify the UI tests fail**

```powershell
pytest tests/test_api.py -k "planning_run_ui or administration or solver" -q
```

Expected: FAIL because the current HTML and JavaScript select Gurobi.

- [ ] **Step 3: Update solver controls and capability binding**

Show `OR-Tools CP-SAT` as the checked radio option. Show Gurobi disabled with localized `已暂停 / Paused`. Bind availability using `BackendID === "ortools"`; keep Simio disabled.

- [ ] **Step 4: Update payload and prompt translations**

Set `SolverBackendID: "ortools"` in the creation flow and make the confirmation generic or CP-SAT-specific in both languages. Preserve raw backend IDs in technical columns while adding translated display labels.

- [ ] **Step 5: Run UI contract tests**

```powershell
pytest tests/test_api.py -k "planning_run_ui or administration or solver" -q
```

Expected: PASS.

- [ ] **Step 6: Commit the UI switch**

```powershell
git add sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js tests/test_api.py
git commit -m "feat: expose cp-sat as the active planner solver"
```

### Task 8: Runtime acceptance, full regression, and ledger completion

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

- [ ] **Step 1: Run the complete automated suite**

```powershell
pytest -q
```

Expected: all tests PASS; only already documented non-functional warnings may remain.

- [ ] **Step 2: Rebuild the isolated test database**

```powershell
sdbr-reset-test-data
```

Expected: the default test DB contains three Pending `TST-RUN-*` scenarios using `ortools`; the reset function's production guard remains covered by `tests/test_test_data.py`.

- [ ] **Step 3: Execute all three scenarios through the API lifecycle**

Start the test service, then for each run call enqueue, claim-next, and execute. Assert schedule result KPI order count is 12, Gantt and load rows exist, and publication status is `Draft` internally.

- [ ] **Step 4: Verify downstream release outcomes**

Evaluate release management at `2026-07-02T12:00:00+00:00` with snapshot max age 30000 minutes. Expected: baseline has at least one ready candidate; material shortage contains `MATERIAL_SHORTAGE`; WIP limit contains `WIP_LIMIT_EXCEEDED`.

- [ ] **Step 5: Verify paused Gurobi and historical reads**

Attempt a new Gurobi run and expect structured rejection. Query a retained completed Gurobi fixture or compatibility record and expect its existing schedule output to remain readable.

- [ ] **Step 6: Complete specification evidence**

Mark `BE-SOLVER-009` `[VERIFIED]` only after Tasks 1-5 and runtime evidence pass. Keep `BE-SOLVER-002` `[PAUSED]`. Add test counts, runtime scenario evidence, and a dated changelog entry. Mark the new UI acceptance unit `已验证待用户确认`; do not mark it `用户已确认`.

- [ ] **Step 7: Stop for UI confirmation**

Report `UI-RUN-002` and `UI-ADMIN-002`, the test result, and the local URL. Wait for explicit user confirmation before changing the UI acceptance unit to `用户已确认` or starting the separate plan-publication UI unit.

- [ ] **Step 8: Commit acceptance evidence**

```powershell
git add docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: verify cp-sat scheduling migration"
```

## Deferred Follow-Up

After this plan is verified and the UI solver-state unit is user-confirmed:

1. Add the approved plan-publication UI design as a separate `UI-*` acceptance unit using the排程结果内嵌治理区 layout.
2. Implement advanced CP-SAT capabilities in this order: sequence-dependent setup, frozen/locked operations, resource quantity and efficiency, then versioned multi-objective strategies.
3. Keep Simio paused until explicitly resumed.
