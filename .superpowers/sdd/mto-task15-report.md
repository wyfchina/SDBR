# MTO Task 15 Report

Date: 2026-07-12

## Scope

Implemented only Task 15 from
`docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.
This slice establishes the strict public MTO API payload boundary and registers
the MTO path with existing authorization middleware. It does not add an MTO
orchestration endpoint, Planning Run creation, external-order mutation, or
DDAE/master-data authority behavior.

## BE-SDBR-010 Evidence

- Added strict MTO intake, re-evaluation, decision, and material-requirement
  Pydantic payload models in `sdbr/api.py` using `ConfigDict(extra="forbid")`.
- Added `_mto_order_from_payload` to reduce the accepted intake payload to the
  internal order fields; the explicit operational snapshot selection remains
  outside that order record.
- Added the live order-commitment evaluation/event aliases in `create_app` for
  later Task 16-21 routes.
- Added `/planner/workbench/order-commitments` to the existing protected path
  tuple. Existing role policy therefore allows Viewer, Planner, Worker, and
  Admin GET access, while non-GET requests allow Planner and Admin only.
- Added five fixed-time seeded-fixture contract tests in
  `tests/test_order_commitment_api.py` for explicit snapshot input, prohibited
  material/window/authority fields, all allowed decisions, direct role policy,
  and protected-prefix registration.

## TDD Record

1. RED: `pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiContracts -q --basetemp .tmp/pytest-mto-api-contract-red -p no:cacheprovider`
   produced `5 failed`: the three MTO models were absent and the MTO path
   returned 404 rather than the authorization middleware's 401.
2. GREEN: after the minimal Task 15 implementation, the same command with
   `pytest-mto-api-contract-green` produced `5 passed`.

## Verification

- Collection: `5 tests collected`.
- Focused: `5 passed` using
  `pytest tests/test_order_commitment_api.py -q --basetemp .tmp/pytest-mto-api-focused -p no:cacheprovider`.
- Related: `414 passed` using
  `pytest tests/test_api.py tests/test_test_data.py tests/test_order_commitment_evaluation.py tests/test_order_commitment_view.py tests/test_state_store.py -q --basetemp .tmp/pytest-mto-api-related-captured -p no:cacheprovider`.
- Full: `925 passed` using
  `pytest -q --basetemp .tmp/pytest-full-mto-task15 -p no:cacheprovider`.
- `python -m compileall -q sdbr` completed successfully.
- `git diff --check` completed successfully before the report was added and is
  rerun as the pre-commit check.

## Self-Review

- Payload fields and defaults match the Task 15 contract exactly, including
  timezone-aware `RequestedDueAt` and `ReceivedAt`, positive quantities, and
  the five enumerated decisions.
- Every MTO payload model rejects unrecognized fields, preventing client-side
  threshold, material-window, external-acceptance, Planning Run, DDAE, raw
  snapshot, or other authority extensions.
- No route decorators were added. Later Task 16-21 orchestration remains out
  of scope.
- The test suite emits one `fastapi.testclient` deprecation warning from the
  installed dependency stack; it is unrelated to this slice and causes no test
  failure.
