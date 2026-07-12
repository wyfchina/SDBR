# MTO Task27 Report

Date: 2026-07-12

## Scope

Implemented Task27 only from `docs/superpowers/plans/2026-07-11-mto-order-commitment-workflow.md`.

- UI specification: `UI-COMMIT-001` (remains `开发中`)
- Backend specification: `BE-SDBR-010`
- Worktree: `D:\Documents\SDBR\.worktrees\mto-order-commitment`
- Task28 browser acceptance, reproducible seed, UI evidence, and specification finalization were not started.

## Delivered

- Closed the Task26 review gap by defining and binding `openOrderCommitmentDecision` before the existing `AllowedActions`-derived decision buttons can invoke it.
- Kept the decision dialog gated by both `AwaitingPlannerDecision` and the selected detail's projected `Recommendation.AllowedActions`; terminal details remain read-only.
- Derived visible and native-required CCR/material acknowledgements from `ActionAcknowledgementRequirements[action]`, reset both controls for each choice, and kept reject free of acceptance acknowledgements through the canonical server projection.
- Required a trimmed business reason and every acknowledgement visible for the selected action before enabling or submitting confirmation.
- Rendered a bilingual decision summary with action, requested and selected promises, CCR load, protection source/state, material status, and the three `NotPerformed` authority boundaries.
- Sent one deterministic, replay-safe decision request containing `If-Match`, the exact evaluation fingerprint, and all seven canonical decision fields. No client material window, Planning Run creation, or external-authority mutation path was added.
- Refreshed list and detail after success or exact replay. Revision, stale-evidence, fingerprint, and replay conflicts refresh without automatic decision retry, clear the old choice, disable submission, and present localized business text.
- Added native-dialog keyboard cancellation, first-required-control focus, labelled/required form controls, alert feedback, bilingual live re-rendering, and static responsive/terminal checks.

## TDD Evidence

1. RED: `pytest tests/test_api.py::TestOrderCommitmentUiDecisionFlow -q --basetemp .tmp/pytest-mto-ui-decision-red-20260712 -p no:cacheprovider`
   - Observed `9 failed` because `orderCommitmentDecisionRequirements` and the Task27 decision handlers were absent.
2. GREEN: `pytest tests/test_api.py::TestOrderCommitmentUiDecisionFlow -q --basetemp .tmp/pytest-mto-ui-decision-green-20260712 -p no:cacheprovider`
   - Observed `9 passed`, with one existing Starlette deprecation warning.

## Verification

- Bundled workspace Node syntax check: loaded `sdbr/web/planner-workbench.js` with the Node REPL runtime and `new vm.Script(...)`; observed `planner-workbench.js syntax OK`.
- Focused UI/API suite: shell, read flow, re-evaluation, decision flow, Task28 status gate, safe API view contract, decision replay, staleness, and terminal action projection; observed `60 passed`, with one existing Starlette deprecation warning.
- Canonical acknowledgement matrix: reference/exceeded CCR acknowledgement, both conditional material acknowledgements, and reject with no risk acknowledgements; observed `3 passed`.
- PowerShell static/responsive/accessibility/boundary check: observed `Task27 static/responsive/accessibility/boundary checks OK`.
- `git diff --check`: passed before final verification.

## Self-Review

- Task27 plan coverage: all seven planned decision-flow behaviors are covered; two additional tests cover bilingual failure/replay handling and keyboard/focus/responsive/terminal gates.
- Request safety: exactly one `/decision` fetch exists in the submit function and there is no recursive submit or retry call.
- Lifecycle safety: both rendering and opening use projected `AllowedActions`; opening additionally requires `AwaitingPlannerDecision`.
- Replay safety: `DecisionID` is deterministic for evaluation, record version, and action; exact server replay follows the same success refresh path, while replay conflict follows refresh-only recovery.
- Authority safety: the dialog displays `ExternalOrderAcceptance`, `PlanningRunCreation`, and `ProductionMutation`; no Task27 request can set them.
- Scope/status safety: only the planner JavaScript, focused UI tests, and this report changed; `UI-COMMIT-001` and acceptance record 17.13 remain `开发中` at UI specification version 5.35.

## Concerns

- The focused runs continue to report the repository's existing `StarletteDeprecationWarning` for `fastapi.testclient`; it is unrelated to Task27.
- Actual desktop/mobile browser acceptance and screenshot evidence remain intentionally deferred to Task28.
