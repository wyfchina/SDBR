# MTO Task 23 Report

Date: 2026-07-12
Worktree: `D:\Documents\SDBR\.worktrees\mto-order-commitment`

## Scope

Executed Task 23 only. No UI Task 24 or later files were modified. The UI
specification remains pending and unchanged.

## Backend Evidence

- `BE-SDBR-010` is `[PARTIAL]` at backend specification version 2.81.
- The recorded implementation covers CCR shadow assessment, 60-minute
  operational-snapshot freshness, material assessment, recommendation and
  planner-decision handling, safe read models, persisted evaluation/event
  state, atomic Phase 0 reservations, and the explicit Planning Run bridge.
- The remaining scope is approved CCR-threshold intake, external formal-order
  authority, later explicit Planning Run creation, and ERP/MES authority.

## Verification

- `python -m compileall -q sdbr`: exit 0, no output.
- Focused collection: 374 tests collected, 1 warning, 1.75s.
- Focused execution: 374 passed, 1 warning, 33.62s.
- Preserved business paths: 473 passed, 1 warning, 57.81s.
- Full suite: 1006 passed, 1 warning, 106.16s.
- The only warning was the existing `StarletteDeprecationWarning` for
  `starlette.testclient` and `httpx`.
- Scope scans found required `BE-SDBR-010` / `BE-RUN-011` citations and
  explicit `NotPerformed` authority boundaries. The sole
  `MaterialCheckWindowMinutes` JavaScript hit was the existing release-policy
  detail display, not an MTO request path.

## Commit Status

The report is under the repository's ignored `.superpowers/` directory. The
tracked backend specification change is ready for its Task 23 documentation
commit.

## Repeatability Correction

Date: 2026-07-12

- `BE-SDBR-010` remains `[PARTIAL]`; this correction does not expand product,
  authority, or UI scope.
- Fresh focused replay: `pytest tests/test_ccr_shadow_scheduler.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_order_commitment_api.py tests/test_planning_run_reservation_bridge.py tests/test_state_store.py tests/test_sdbr_market_control.py -q --basetemp .tmp/pytest-mto-task23-focused-20260712-140809-0560 -p no:cacheprovider` completed with `413 passed, 1 warning in 30.62s`.
- Fresh preserved-path replay: `pytest tests/test_scheduling_solver.py tests/test_schedule_output.py tests/test_release_candidates.py tests/test_release_authorization.py tests/test_material_state.py tests/test_sdbr_market_control.py tests/test_sdbr_what_if.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_planning_run_reservation_bridge.py tests/test_api.py -q --basetemp .tmp/pytest-mto-task23-preserved-20260712-140809-0560 -p no:cacheprovider` completed with `475 passed, 1 warning in 53.79s`.
- Fresh full replay: `pytest -q --basetemp .tmp/pytest-mto-task23-full-20260712-140809-0560 -p no:cacheprovider` completed with `1047 passed, 1 warning in 108.76s`.
- Focused collection found `413 tests collected, 1 warning in 1.31s`; `python -m compileall -q sdbr` exited 0 with no output. The one warning in every pytest run was the existing `StarletteDeprecationWarning` from `starlette.testclient` and `httpx`.
- All three basetemp directories were new for this replay. The locked `.tmp/pytest-mto-full` path was not reused.
