# MTO Task 14 Report

Date: 2026-07-12

## Scope

Implemented Task 14 only from
`docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.

- Added the controlled `BE-DATA-014` / `BE-SDBR-010` MTO fixture constants
  and `seed_mto_order_commitment_fixture` in `sdbr/test_data.py`.
- Added the test-environment-only MTO reset endpoint in `sdbr/api.py`.
- Added the four prescribed `TestOrderCommitmentBrowserSeed` contract tests
  in `tests/test_test_data.py`.
- Did not add MTO intake, decision, Planning Run bridge, UI, DDAE-contract,
  ERP/WMS, MES, or production-authority behavior from later tasks.

## Fixture Boundary

- The fixture clears only the MTO evaluation and shared Phase 0 runtime
  collections it owns before reseeding; it does not clear external-authority
  collections.
- The endpoint first checks `active_environment.is_production` and returns
  `409 TestDataResetNotAllowed` before writing any fixture data.
- The seeded records are explicitly test data (`TST-*`, `SDBR-TestData`, and
  `sdbr-test-data`). No existing `DemoFixture` / `PublicDemoOnly` data or
  contract boundary was modified.
- The returned browser prerequisite template contains controlled mock ERP
  data, fixed identifiers, a frozen release policy, and no production claims.

## TDD Evidence

RED:

```powershell
pytest tests/test_test_data.py::TestOrderCommitmentBrowserSeed -q --basetemp .tmp/pytest-mto-seed-red -p no:cacheprovider
```

Result: `4 failed` as expected: the first two tests reported the absent
`seed_mto_order_commitment_fixture`; the endpoint tests received `404` because
the route was absent.

Focused GREEN:

```powershell
pytest tests/test_test_data.py::TestOrderCommitmentBrowserSeed -q --basetemp .tmp/pytest-mto-seed-green-focused -p no:cacheprovider
```

Result: `4 passed`.

Task-prescribed collection:

```powershell
pytest tests/test_test_data.py::TestOrderCommitmentBrowserSeed --collect-only -q
```

Result: the four prescribed tests collected.

Task-prescribed regression:

```powershell
pytest tests/test_test_data.py -q --basetemp .tmp/pytest-mto-seed-green -p no:cacheprovider
```

Result: `15 passed, 1 warning`.

Full repository regression:

```powershell
pytest -q --basetemp .tmp/pytest-mto-task14-regression-final -p no:cacheprovider
```

Result: `915 passed, 1 warning`. The warning is the existing FastAPI/Starlette
`TestClient` deprecation warning for `httpx`.

## Self-Review

- Fixture IDs, calendar windows, 180-minute CCR baseline load, material
  snapshot, frozen release policy, completed/published baseline, and exact
  browser intake template match Task 14.
- The endpoint gets `captured_at` only from `server_utc_now()` and its test
  proves repeated resets return the same controlled response and clear stale
  MTO evaluation state.
- Production rejection occurs before baseline or MTO fixture writes.
- The diff is limited to `sdbr/test_data.py`, `sdbr/api.py`,
  `tests/test_test_data.py`, and this report. No specification scope change was
  needed for the preplanned `BE-DATA-014` / `BE-SDBR-010` acceptance work.

## Concern

No Task 14 functional concern remains. The pre-existing FastAPI/Starlette
`TestClient` deprecation warning remains in test output.
