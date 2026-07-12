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

## 2026-07-12 Review Remediation Evidence

- Scope: fixed only the two `UI-COMMIT-001` / `BE-SDBR-010` Task25 findings from `.superpowers/sdd/mto-task25-review.md`; Task26 commit `bd1cecc` and the Task27 decision dialog were not changed.
- Audit history now formats `AcceptedPromiseAt` through the localized date/time formatter and renders `CcrRiskAcknowledged`, `MaterialRiskAcknowledged`, and `MaterialCheckEnabled` through localized business boolean labels. The remaining safe audit fields are rendered from the approved whitelist only; no raw JSON or payload path was added.
- Detail fetch now opens a localized loading state, catches failed or missing responses into a localized error state, suppresses stale actions, and exposes a localized retry action for safe recovery.
- TDD red: `pytest tests/test_api.py::TestOrderCommitmentUiReadFlow -q --basetemp .tmp/pytest-mto-task25-findings-red -p no:cacheprovider` - `2 failed, 4 passed, 1 warning`; both failures were the newly added audit-formatting and detail-state regressions.
- TDD green: `pytest tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract -q --basetemp .tmp/pytest-mto-task25-findings-green -p no:cacheprovider` - `7 passed, 1 warning`.
- Focused UI/API verification: `pytest tests/test_api.py::TestOrderCommitmentUiShell tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_order_commitment_api.py::TestOrderCommitmentUiContract tests/test_order_commitment_api.py::TestOrderCommitmentApiIntakeAndReads -q --basetemp .tmp/pytest-mto-task25-findings-focused -p no:cacheprovider` - `24 passed, 1 warning`.
- Syntax and whitespace verification: `python -m compileall -q sdbr` and `git diff --check` passed. `Get-Command node -All` and a worktree executable search found no Node runtime, so no bundled/workspace `node --check` command was available.
