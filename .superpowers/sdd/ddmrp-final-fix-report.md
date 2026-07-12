# DDMRP Final Review Fix Report

Date: 2026-07-12
Branch: `codex/ddmrp-replenishment`
Scope: complete four-finding final-review fix wave for `BE-DDMRP-007` and `UI-DDMRP-003`

## Findings Closed

1. GET/read-model validation fails closed when any of the nine frozen run-to-authority source links drifts, even if the run self-fingerprint is recomputed.
2. Exact immutable replay returns `Duplicate` without a persistence commit, revision increment, `LastSavedAt` change, ledger mutation, or restart-state change.
3. Current non-terminal Red/Yellow recommendation chains remain visible in history and summary after a later Green/AboveGreen monitor evaluation.
4. The material-planning table renders the authoritative safe `QualifiedOnHandQty` with an explicit bilingual label and exact seeded values.

## Implementation

- `sdbr/ddmrp_replenishment.py`: centralized evaluation-run authority provenance validation and reused it in both normal record validation and persisted replay graph validation.
- `sdbr/api.py`: marked only the exact validated DDMRP duplicate branch as no-save while retaining replay-before-`If-Match` behavior and the authoritative current revision header.
- `sdbr/ddmrp_replenishment_view.py`: includes every non-terminal chain in history and derives recommendation lifecycle summary counts from immutable history state rather than only latest monitor rows.
- `sdbr/web/planner-workbench.html` and `.js`: bind the on-hand column to `QualifiedOnHandQty` and label it `权威可用在手量` / `Authority-available on hand`.
- Regression coverage spans direct projection, GET API corruption, SQLite persistence/restart, lifecycle API, seeded safe values, and the UI source contract.

## Verification

```text
RED exact final-review selection
15 failed, 1 passed, 1 warning in 10.05s

GREEN identical selection
16 passed, 1 warning in 4.96s

python -m compileall -q sdbr tests
exit 0

local node.exe --check sdbr/web/planner-workbench.js
exit 0

focused Task 12 suite
412 passed, 1 warning in 73.72s

full repository suite
862 passed, 1 warning in 106.70s
```

The warning in every pytest run is the pre-existing FastAPI/Starlette `TestClient` deprecation warning.

## Browser Evidence

- Refreshed `.tmp/ddmrp-ui-acceptance/browser-report.md` and all seven named PNGs.
- HTTP observations: seeded 200, empty 200, error 500, forbidden 403, conflict 409.
- Seeded DOM at 1280x720, 1920x1080, and 390x844: four rows; values `10`, `35`, `75`, `150`; no `-` in the authoritative quantity column; no confirmation control; no page-level horizontal overflow.
- Search, Red filter, suggested-quantity sort, Chinese/English label switching, and keyboard focus were exercised.
- Acceptance server stopped; port 8011 confirmed free.

## Preserved Boundaries

- Safe projection still excludes authority signatures, package/config payloads, evidence rows, request-result records, event payloads, and shared reservation rows.
- No Activation A1-A8 route, control, target-date calculation, accepted advice/BOM adapter, candidate, reservation, allocation, or external-order behavior was added.
- `BE-DDMRP-008` and `BE-DDMRP-009` remain `[NOT-STARTED]`; `UI-DDMRP-004` remains `未开始`; `UI-DDMRP-003` remains `已验证待用户确认`; no `用户已确认` status was added.

## Remaining Concerns

- The existing Starlette `TestClient` deprecation warning remains.
- NOW replay is verified for SQLite persistence and restart, but not for two already-open SQLite store instances. That broader authoritative two-store replay orchestration remains outside this final-fix wave and must not be interpreted as Activation readiness.
