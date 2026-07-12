# MTO Task25 Report

Date: 2026-07-12

## Scope

Implemented Task25 only from `docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.

- UI specification: `UI-COMMIT-001`
- Backend specification: `BE-SDBR-010`
- Worktree: `D:\Documents\SDBR\.worktrees\mto-order-commitment`

## Delivered

- Added the independent `order-commitments` route, workbench/detail fetches, and `X-Workbench-Revision` capture.
- Added business-safe list rendering for all eleven approved columns, including reservation and exception state, plus order/product/status filtering.
- Added business-safe detail sections for order, capacity, material, recommendation, decision, reservation, audit history, and boundary; technical trace data remains in a collapsed `details` section.
- Added Chinese and English labels for every Task25 backend enum. Unknown values use localized `unknownStatus`, never a raw enum.
- Added loading, empty, and error states for the read flow, and responsive summary/table styling.
- Added no re-evaluation or decision submission wiring. Existing Task24 controls remain inert for Task26+ work.
- Added UI read-flow and API response-contract tests.

## TDD Evidence

1. `pytest tests/test_api.py::TestOrderCommitmentUiReadFlow -q --basetemp .tmp/pytest-mto-ui-read-red -p no:cacheprovider`
   - Observed 4 expected failures before the Task25 read implementation.
2. `pytest tests/test_api.py::TestOrderCommitmentUiReadFlow::test_detail_renderer_has_no_json_stringify_or_raw_payload_path -q --basetemp .tmp/pytest-mto-ui-business-labels-red -p no:cacheprovider`
   - Observed 1 expected failure before localizing boolean detail evidence.
3. `pytest tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract -q --basetemp .tmp/pytest-mto-ui-read-green -p no:cacheprovider`
   - Observed `5 passed, 1 warning`.

## Final Verification

- `python -m compileall -q sdbr` - passed.
- Node-backed kernel parse of `sdbr/web/planner-workbench.js` using `node:vm` - passed.
- `pytest tests/test_api.py::TestOrderCommitmentUiShell tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads -q --basetemp .tmp/pytest-mto-task25-focused -p no:cacheprovider` - `17 passed, 1 warning`.
- `git diff --check` - passed.
- `node --check sdbr/web/planner-workbench.js` could not run because neither `node` on `PATH` nor a worktree-local Node executable was available; the Node-backed kernel parse above supplied equivalent syntax validation.

## Changed Paths

- `sdbr/web/planner-workbench.js`
- `sdbr/web/planner-workbench.css`
- `tests/test_api.py`
- `tests/test_order_commitment_api.py`
- `.superpowers/sdd/mto-task25-report.md`

## Concerns

- Browser acceptance, re-evaluation controls, and planner decision controls remain deferred to Tasks 26 through 28.
