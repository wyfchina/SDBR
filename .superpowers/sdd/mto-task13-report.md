# MTO Task 13 Report

Date: 2026-07-12

## Scope

Implemented Task 13 only from
`docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.

- Added `sdbr/order_commitment_view.py` with pure, read-only workbench and
  detail projections for `BE-SDBR-010` and `UI-COMMIT-001`.
- Added `tests/test_order_commitment_view.py` with the nine prescribed
  contract tests.
- Did not change seed data, API routes, UI code, persistence, or later-task
  files.

## TDD Evidence

RED:

```powershell
pytest tests/test_order_commitment_view.py::TestOrderCommitmentViewContract -q --basetemp .tmp/pytest-mto-view-red -p no:cacheprovider
```

Result: expected collection failure, `ModuleNotFoundError: No module named
'sdbr.order_commitment_view'`.

GREEN:

```powershell
pytest tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-view-green-readonly -p no:cacheprovider
```

Result: `9 passed`.

Recursive nested-allowlist hardening RED:

```powershell
pytest tests/test_order_commitment_view.py::TestOrderCommitmentViewContract::test_detail_has_exact_top_level_and_whitelisted_capacity_material_fields -q --basetemp .tmp/pytest-mto-view-recursive-red -p no:cacheprovider
```

Result: expected failure because an object embedded in `AlternateResourceIDs`
was copied through the capacity-window projection.

Recursive nested-allowlist GREEN:

```powershell
pytest tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-view-final-green -p no:cacheprovider
```

Result: `9 passed`; alternate-resource lists now retain only string resource IDs.

Focused collection:

```powershell
pytest tests/test_order_commitment_view.py::TestOrderCommitmentViewContract --collect-only -q
```

Result: the nine prescribed tests collected.

Related regression coverage:

```powershell
pytest tests/test_order_commitment_evaluation.py -q --basetemp .tmp/pytest-mto-evaluation-related -p no:cacheprovider
```

Result: `124 passed`.

Full repository suite:

```powershell
pytest -q --basetemp .tmp/pytest-mto-task13-full -p no:cacheprovider
```

Result: `911 passed, 1 warning`. The warning is an existing FastAPI/
Starlette TestClient deprecation warning for `httpx`.

Final full repository suite after the recursive-allowlist hardening:

```powershell
pytest -q --basetemp .tmp/pytest-mto-task13-final-full -p no:cacheprovider
```

Result: `911 passed, 1 warning`.

## Self-Review

- Workbench rows and detail top levels use exact declared field sets.
- Nested order, capacity-window, material-line, recommendation, audit-detail,
  decision, reservation, evidence-reference, and technical projections use
  explicit allowlists.
- Raw basis, authority, master, operational-snapshot, event trace/causation,
  and unknown audit-detail payloads are excluded.
- Fingerprints and trace/correlation identifiers are confined to collapsed
  `TechnicalDetails`.
- Workbench linking prefers decision IDs, then uses the matching evaluation ID.
- Ordering is evaluated-at descending, then order ID and evaluation ID
  ascending; the test also asserts that projection does not mutate input rows.
- The module is pure and has no store/API/persistence imports or write paths.

## Concern

No Task 13 functional concern remains. The full suite retains the unrelated
FastAPI TestClient deprecation warning noted above.

## Review Follow-up: Recommendation Action Contract

Date: 2026-07-12

Addresses the independent-review finding for `BE-SDBR-010` / `UI-COMMIT-001`
in `.superpowers/sdd/mto-task13-review.md`.

- `AllowedActions` is now required to be a unique list of the six supported
  MTO action strings. Structured values, non-string scalars, and unknown
  action names raise `ValueError` rather than crossing the view boundary or
  being coerced to acknowledgement keys.
- Acknowledgement requirements are projected only for those validated actions.
  A requirement key for another supported action raises `ValueError`; raw or
  unrelated producer metadata remains excluded by the existing projection.
- Each active action must provide both acknowledgement flags as booleans. The
  view exposes only those two flags, so structured flag payloads cannot leak.

### TDD Evidence

RED:

```powershell
pytest tests/test_order_commitment_view.py::TestOrderCommitmentViewContract::test_detail_rejects_unsafe_action_and_acknowledgement_requirement_shapes -q --basetemp .tmp/pytest-mto-task13-contract-refined-red -p no:cacheprovider
```

Result: `5 failed` as expected because the prior projection copied or coerced
unsafe action and acknowledgement data.

Focused GREEN:

```powershell
pytest tests/test_order_commitment_view.py -q --basetemp .tmp/pytest-mto-task13-view-green -p no:cacheprovider
```

Result: `14 passed`.

Related regression:

```powershell
pytest tests/test_order_commitment_evaluation.py -q --basetemp .tmp/pytest-mto-task13-evaluation-related-final -p no:cacheprovider
```

Result: `124 passed`.

Task 14 preservation:

```powershell
pytest tests/test_test_data.py::TestOrderCommitmentBrowserSeed -q --basetemp .tmp/pytest-mto-task14-preservation-final -p no:cacheprovider
```

Result: `4 passed, 1 warning`; the warning is the existing FastAPI/Starlette
`TestClient` deprecation warning. Commit `e168c60` remains unchanged.
