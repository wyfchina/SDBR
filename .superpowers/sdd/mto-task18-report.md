# MTO Task 18 Report

Date: 2026-07-12

## Scope

Implemented Task 18, `BE-SDBR-010`: audited MTO order-commitment
re-evaluation using current operational evidence.

- Added `POST /planner/workbench/order-commitments/{evaluation_id}/reevaluate`.
- The route accepts only open evaluations, reuses the source order, optionally
  changes the server-owned baseline reference, and resolves the material window
  only through the selected baseline's frozen release policy.
- New evidence supersedes only open evaluations and writes immutable
  supersession/re-evaluation events using one server timestamp and effective
  actor.
- Exact replay returns `Duplicate`, appends no event, and suppresses persistence
  so the workbench revision remains unchanged.
- No decision, acceptance, UI, Phase 0, Planning Run, external authority, or
  DDAE behavior was added.

## TDD Evidence

RED:

```powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiReevaluation -q --basetemp .tmp/pytest-mto-reevaluation-red -p no:cacheprovider
```

Observed: 10 failures, all because the re-evaluation route was absent (`404`).

GREEN / focused:

```powershell
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiReevaluation --collect-only -q
pytest tests/test_order_commitment_api.py::TestOrderCommitmentApiReevaluation -q --basetemp .tmp/pytest-mto-reevaluation-final -p no:cacheprovider
```

Observed: 11 collected and 11 passed. Coverage includes latest and explicit
stale/future snapshots, material opt-out validation, material-window rejection,
open-only supersession, event actor/time/causation, exact replay/revision,
terminal-state gating, and no Phase 0/Planning Run writes.

Related:

```powershell
pytest tests/test_order_commitment_api.py -q --basetemp .tmp/pytest-mto-order-commitment-api-related -p no:cacheprovider
```

Observed: 36 passed.

Full:

```powershell
pytest -q --basetemp .tmp/pytest-full-mto-task18-verified -p no:cacheprovider
```

Observed: 957 passed.

## Self-Review

- Confirmed event details contain only the Task 18 audit facts.
- Confirmed both events share the single captured `observed_at` and effective
  actor.
- Confirmed duplicate re-evaluation does not advance `X-Workbench-Revision`.
- Confirmed `git diff --check` exits successfully.

## Concern

All pytest runs emit one pre-existing Starlette deprecation warning for
`fastapi.testclient` importing `httpx`; no Task 18 behavior failed.
