# MTO Task 10 Execution Report

Date: 2026-07-12

Scope: Task 10 only from `docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.

Applicable backend specification IDs: `BE-SDBR-006`, `BE-SDBR-010`.

## Implemented

- Added exact relevant-state projections and frozen audit/decision-staleness bases.
- Added canonical decision facts, canonical evaluation identity, and duplicate-safe registration.
- Added exact replay/version-order checks and supersession restricted to open planner-decision evaluations.
- Added the required material opt-out coverage: material snapshot/evidence remains in the audit basis but is excluded from the decision-staleness basis when the check is disabled.
- Did not modify API, UI, persistence, or later-task files.

## TDD Evidence

1. RED:
   `pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity -q --basetemp .tmp/pytest-mto-identity-red -p no:cacheprovider`
   Result: `15 failed`; each failure was the expected missing `build_order_commitment_basis` production symbol.
2. Focused GREEN:
   `pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity -q --basetemp .tmp/pytest-mto-identity-complete -p no:cacheprovider`
   Result: `15 passed in 0.42s`.
3. Related suite:
   `pytest tests/test_order_commitment_evaluation.py -q --basetemp .tmp/pytest-mto-evaluation-related -p no:cacheprovider`
   Result: `106 passed in 0.92s`.
4. Full suite:
   `python -m pytest -q --basetemp .tmp/pytest-mto-task10-full-controlled -p no:cacheprovider`
   Result: `881 passed, 1 warning in 97.01s`.
5. Self-review:
   `git diff --check`
   Result: no whitespace errors. Review confirmed only Task 10 evaluator/tests/report files changed and no later API/UI/persistence work was introduced.

## Changed Files

- `sdbr/order_commitment_evaluation.py`
- `tests/test_order_commitment_evaluation.py`
- `.superpowers/sdd/mto-task10-report.md`

## Concern

The full suite emits one existing FastAPI/Starlette warning about `httpx` compatibility in `fastapi.testclient`; it does not fail tests and is outside Task 10 scope.

## Review Finding Remediation

Date: 2026-07-12

Applicable backend specification IDs: `BE-SDBR-010`.

- Corrected Task 10 relevant-capacity matching to compare timezone-aware windows after canonical UTC normalization, so equivalent offset representations freeze the same reservation evidence.
- Restricted Task 10 pending-capacity basis capture to `ActivePlanReservation` and `HeldForPlanningError`; `LinkedToFormalOrder` remains available to broader reservation read models but is excluded because it has crossed into the formal-order side of the intake boundary.
- Added regressions for both review findings without changing API, UI, persistence, or later-task behavior.

### Verification Evidence

1. RED:
   `pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_timezone_equivalent_aware_capacity_window_is_included tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_linked_to_formal_order_capacity_reservation_is_excluded -q --basetemp .tmp/pytest-mto-task10-review-red -p no:cacheprovider`
   Result: `2 failed` as expected: the offset-equivalent row was omitted and the `LinkedToFormalOrder` row was included.
2. Focused GREEN:
   `pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_timezone_equivalent_aware_capacity_window_is_included tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity::test_linked_to_formal_order_capacity_reservation_is_excluded -q --basetemp .tmp/pytest-mto-task10-review-green -p no:cacheprovider`
   Result: `2 passed in 0.10s`.
3. Task 10 identity coverage:
   `pytest tests/test_order_commitment_evaluation.py::TestOrderCommitmentEvaluationIdentity -q --basetemp .tmp/pytest-mto-task10-review-identity -p no:cacheprovider`
   Result: `17 passed in 0.23s`.
4. Related evaluator suite:
   `pytest tests/test_order_commitment_evaluation.py -q --basetemp .tmp/pytest-mto-task10-review-related -p no:cacheprovider`
   Result: `119 passed in 0.45s`.
5. Compile check:
   `python -m compileall -q sdbr`
   Result: exit code `0` with no output.
