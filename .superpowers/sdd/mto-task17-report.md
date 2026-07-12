# MTO Task 17 Report

Date: 2026-07-12

## Scope

Implemented only Task 17, **Idempotent Intake and Sanitized Reads**, from
`docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.

Applicable backend specification: `BE-SDBR-010`.

## Delivered

- Added authenticated MTO intake at
  `/planner/workbench/order-commitments/intake`.
- Intake normalizes server-owned order identity, evaluates with material checking
  enabled, records a stable safe audit event, and returns only a workbench-row
  projection plus the recommendation-only boundary.
- Exact replay returns the original evaluation without observing a new clock,
  mutating state, increasing the workbench revision, or appending an event.
- Added sanitized workbench and evaluation-detail reads with the middleware
  revision header and explicit `OrderCommitmentEvaluationNotFound` handling.
- Added atomic v1-to-v2 supersession, terminal/no-action projection coverage,
  concurrent version-rank coverage, rejected-version continuation, and the
  accepted-version amendment block.

## Deliberately Not Implemented

No reevaluation route, decision route, Phase 0 reservation/demand write,
Planning Run creation, UI work, or DDAE/ERP/MES/master-data mutation was added.
The superseded-decision check uses the existing domain eligibility guard; the
public decision endpoint remains Task 19 scope.

## TDD And Verification Evidence

- RED slice A:
  `pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads -q --basetemp .tmp/pytest-mto-intake-red-a -p no:cacheprovider`
  produced 7 expected route-absence failures (404 / missing response data).
- GREEN slice A: the same class produced 7 passing tests.
- RED slice B: with the atomic Created/persistence branch temporarily removed,
  the class produced 8 failures; restoration produced 11 passing tests.
- Related:
  `pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-intake-related-b -p no:cacheprovider`
  produced 25 passing tests.
- Full:
  `pytest -q --basetemp .tmp/pytest-full-mto-task17-rerun -p no:cacheprovider`
  completed successfully (exit 0).
- `git diff --check` passed for the Task 17 implementation and final test diff.

## Review

Manual self-review confirmed safe response projections use the existing
whitelisted view builders; raw order/basis/master-data/snapshot/event payloads
remain internal. Exact duplicate replay uses the existing state-admission
boundary and avoids persistence revision changes.

## Concerns

The focused and related pytest runs emit the pre-existing Starlette TestClient
deprecation warning for the installed `httpx` version. It does not affect the
Task 17 behavior or test result.
