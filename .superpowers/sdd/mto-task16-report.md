# MTO Task 16 Report

Date: 2026-07-12

## Scope

Implemented Task 16, State-to-Evaluation Orchestration, for
`BE-SDBR-006` through `BE-SDBR-010` only. No Task 17+ MTO HTTP endpoints,
UI work, server-owned actor/time/revision behavior, or intake idempotency
behavior was added.

## Implementation

- Added the `create_app`-scoped `_build_order_commitment_evaluation_from_state`
  resolver and its exact tolerant capacity/material ledger prefilters.
- Enforced completed and approved/published baseline evidence, selected and
  froze baseline master/configuration/release/route/calendar evidence, and
  evaluated only the reference 80% CCR protection policy.
- Kept malformed or unrelated ledger rows outside the relevant evidence and
  fingerprint scope.
- Returned fail-closed shadow-capacity evidence for missing routing, resource,
  calendar, and schedule evidence while preserving explicit stale/future
  operational snapshots as material evidence-insufficient.

## TDD Evidence

- RED: `pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiOrchestration -q --basetemp .tmp/pytest-mto-orchestration-red -p no:cacheprovider`
  produced eight expected failures because the resolver was absent.
- GREEN: the same focused resolver suite passed with `8 passed` after the
  minimal resolver implementation.
- The eight tests cover baseline eligibility, schedule/master/route evidence,
  latest-current and explicit stale/future snapshots, frozen references,
  reference-only protection policy, exact relevant-ledger fingerprinting, and
  calendar-timezone failure behavior.

## Verification

- Collection: 8 resolver tests collected.
- Focused: 8 passed, 1 FastAPI/Starlette deprecation warning.
- Related: 221 passed, 1 warning across MTO API/evaluation/view, CCR shadow,
  and reservation suites.
- Full: 933 passed, 1 warning in 98.59 seconds; process exit 0.
- `git diff --check` completed without whitespace errors.

## Self-Review and Concern

- Reviewed the resolver against the Task 16 plan: it has no MTO route
  declarations and does not mutate evaluation, reservation, or revision state.
- The Task 16--21 import list in the plan includes
  `assert_reservation_write_set_replay_matches`, but that symbol does not
  exist in this worktree and is a Task 21 concern. It was intentionally not
  imported or implemented here so Task 16 remains importable and scoped.
