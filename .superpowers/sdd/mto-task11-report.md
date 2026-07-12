# MTO Task 11 Delivery Report

Date: 2026-07-12

## Scope

Implemented Task 11 only: decision fingerprinting, MTO Phase 0 acceptance
preparation, and immutable accepted/rejected evaluation record builders.
Applicable backend capability IDs: `BE-SDBR-006` through `BE-SDBR-010`.

No persistence, API, UI, Planning Run creation, external-order acceptance, ERP,
MES, or DDAE integration was implemented.

## Implementation Evidence

- `prepare_mto_acceptance` validates decision eligibility, allowed action,
  frozen capacity/material context, action-specific acknowledgements, and each
  selected reservation deadline before preparing a shared Phase 0 write set.
- The demand commitment is explicitly passed through
  `normalize_demand_commitment` after MTO traceability fields are attached.
  Accepted demand metadata retains the frozen operating-model/configuration
  context and records that external acceptance, Planning Run creation, and
  production mutation were not performed.
- `canonical_decision_fingerprint` includes decision ID, evaluation ID,
  evaluation fingerprint, decision, actor, reason, and both acknowledgement
  booleans. It deliberately excludes `DecidedAt`, allowing an exact replay to
  retain the same canonical decision identity while recording a new server
  observation time.
- Accepted and rejected record builders deep-copy the evaluation, create
  immutable decision evidence, increment the record version, and set only the
  Task 11 terminal lifecycle state (`AcceptedPendingFormalSchedule` or
  `Rejected`).

## TDD And Verification

- RED: `TestOrderCommitmentAcceptancePreparation` collected 11 tests and all
  failed against absent Task 11 production functions.
- Acceptance contexts: 4 collected and passed after implementation.
- Acknowledgement/expiry guards: 5 collected and passed.
- Decision fingerprint and record builders: the focused fingerprint test failed
  before its implementation; both focused tests passed afterward.
- Task 11 class: exactly 11 tests collected.
- Related regression command: 215 passed.
- `python -m compileall -q sdbr`: passed.
- Full suite: 892 passed in 97.20 seconds. The only output warning was the
  existing `fastapi.testclient`/Starlette `httpx` deprecation warning.
- `git diff --check`: passed.

## Self-Review

Reviewed the final diff against Task 11. The canonical fingerprint covers the
required replay identity fields and excludes server observation time; the
normalizer invocation is tested directly; acceptance preserves Phase 0-only
authority boundaries. No blocking issue was found.

## Medium Finding Remediation (2026-07-12)

Applicable backend capability IDs: `BE-SDBR-006` through `BE-SDBR-010`.

- `accepted_evaluation_record` now requires the supplied decision to remain in
  the evaluation's `AllowedActions`, validates the action's frozen
  capacity/material context, and binds the reservation write set to the same
  evaluation ID, selected promise, and expected material commitment status.
- The record builder also requires `decision_id` to equal the write set batch
  `ConfirmationID`, preventing persisted evidence from claiming a different
  decision than the Phase 0 reservation batch.
- TDD RED evidence: the three added regressions failed before the guard was
  implemented because each call returned an accepted record. They cover a
  disallowed decision, a write set from a different action/context, and a
  decision ID that differs from the batch confirmation ID.
- GREEN evidence: `python -m pytest
  tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation
  -q` passed with 14 tests. Related verification passed with 192 tests:
  `python -m pytest tests/test_order_commitment_evaluation.py
  tests/test_planning_reservations.py tests/test_ccr_shadow_scheduler.py -q`.
  `python -m compileall -q sdbr` and `git diff --check` also passed.
- Scope remains Task 11 only. Task 10 fix commit `5b5b9d2` is preserved; no
  Task 12 or later work was included.

## Remaining Medium Finding Remediation (2026-07-12)

Applicable backend capability IDs: `BE-SDBR-006` through `BE-SDBR-010`.

- MTO acceptance preparation now freezes both acknowledgement booleans in the
  reservation batch `ConfirmationContext`. The context is added before the
  reservation payload fingerprint is calculated.
- `accepted_evaluation_record` now requires its CCR and material acknowledgement
  flags to exactly match that frozen write-set context before persisting decision
  evidence.
- TDD RED evidence: the two added regressions failed before the implementation
  because both calls returned an accepted record. They cover a conditional
  material acknowledgement changed from `true` to `false`, and a later-safe,
  reference-fallback CCR acknowledgement changed from `true` to `false`.
- GREEN evidence: the two regressions passed after the binding was installed.
  `python -m pytest
  tests/test_order_commitment_evaluation.py::TestOrderCommitmentAcceptancePreparation
  -q --basetemp .tmp/pytest-mto-task11-ack-class -p no:cacheprovider` passed
  with 16 tests. Related verification passed with 194 tests: `python -m pytest
  tests/test_order_commitment_evaluation.py tests/test_planning_reservations.py
  tests/test_ccr_shadow_scheduler.py -q --basetemp
  .tmp/pytest-mto-task11-ack-related -p no:cacheprovider`.
  `python -m compileall -q sdbr` and `git diff --check` also passed.
- Scope remains Task 11 only. Task 12 commit `47d0f26` remains the worktree
  HEAD parent and was not modified; no Task 13 or later work was included.
