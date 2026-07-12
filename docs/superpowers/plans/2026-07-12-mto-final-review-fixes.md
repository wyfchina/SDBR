# MTO Final Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all five MTO final-review findings while preserving the strict public API, immutable replay/revision behavior, atomic Phase 0 acceptance, bilingual responsive UI, and the pending user-confirmation gate.

**Architecture:** Canonicalize and validate request text at the FastAPI boundary, retain domain conflict mapping around normalization/fingerprinting, and reuse one material skip-reason canonicalizer for evaluation and staleness evidence. Correct the whitelisted view projection, then extend the existing drawer and reevaluation state machines with focus restoration, modal exclusion, Escape handling, and localized recoverable transport failures.

**Tech Stack:** Python 3, FastAPI/Pydantic, pytest, vanilla JavaScript/HTML/CSS, Node syntax checking, Playwright browser acceptance.

## Global Constraints

- Cite `BE-SDBR-010` and `UI-COMMIT-001` in focused tests and evidence.
- Do not change external-order, automatic Planning Run, DDAE, ERP/WMS, MES, supplier, master-data, or production authority.
- Preserve exact replay, revision guards, rollback, and atomic reservation acceptance.
- Keep `UI-COMMIT-001` and acceptance unit 17.13 at `已验证待用户确认`; never write `用户已确认`.
- Deliver all fixes, tests, evidence, and reports in one commit.

---

### Task 1: Strict Request Text and Structured Domain Failures

**Files:**
- Modify: `tests/test_order_commitment_api.py`
- Modify: `sdbr/api.py`

**Interfaces:**
- Consumes: `MtoOrderCommitmentIntakePayload`, `MtoOrderCommitmentReevaluationPayload`, `MtoOrderCommitmentDecisionPayload`, `_order_commitment_error`.
- Produces: stripped nonblank request strings and structured `422` validation or `409` domain responses with no partial persistence.

- [ ] **Step 1: Add adversarial endpoint tests**

Parameterize blank and whitespace-only required identifiers/reasons across intake, reevaluation, and decision. Assert `422`, structured validation detail, no HTTP 500, and an unchanged store snapshot.

- [ ] **Step 2: Run the tests and verify RED**

Run the selected tests with a unique `--basetemp`; expect the current blank probes to return `500` or pass model construction unexpectedly.

- [ ] **Step 3: Implement the minimal boundary fix**

Define reusable Pydantic nonblank string annotations with whitespace stripping, apply them to required and optional MTO request strings, and map any remaining `OrderCommitmentConflict` raised by route-level normalization or decision fingerprinting to structured `409` responses.

- [ ] **Step 4: Run the selected tests and verify GREEN**

Expect every adversarial case to pass while the existing strict-extra, datetime, boolean, replay, revision, and rollback tests remain green.

---

### Task 2: Canonical Material Opt-Out Evidence

**Files:**
- Modify: `tests/test_order_commitment_evaluation.py`
- Modify: `tests/test_order_commitment_api.py`
- Modify: `sdbr/order_commitment_evaluation.py`
- Modify: `sdbr/api.py`

**Interfaces:**
- Produces: `normalize_material_check_skip_reason(value) -> str | None` and identical canonical values in `MaterialAssessment.SkipReason` and `DecisionStalenessBasis.MaterialPolicy.SkipReason`.

- [ ] **Step 1: Add whitespace-equivalence tests**

Assert that reevaluation with a padded opt-out reason persists the trimmed reason in both evidence locations and that a subsequent valid conditional decision is accepted rather than falsely stale.

- [ ] **Step 2: Run the tests and verify RED**

Expect the basis assertion or decision call to fail with `OrderCommitmentEvaluationStale`.

- [ ] **Step 3: Canonicalize once for both consumers**

Normalize the skip reason before material evaluation and basis construction; retain domain validation when material checks are disabled without a canonical reason.

- [ ] **Step 4: Run the tests and verify GREEN**

Expect canonical evidence equality and successful decision acceptance with all exact replay behavior unchanged.

---

### Task 3: Canonical CCR Threshold Projection

**Files:**
- Modify: `tests/test_order_commitment_view.py`
- Modify: `tests/test_order_commitment_api.py`
- Modify: `sdbr/order_commitment_view.py`

**Interfaces:**
- Consumes: canonical `ProtectionPolicy.TargetPercent`.
- Produces: non-null `ProtectionThresholdPercent` in workbench rows.

- [ ] **Step 1: Change the fixture to `TargetPercent` and assert the real API value**

Add exact assertions for fixture and production-backed workbench rows.

- [ ] **Step 2: Run the tests and verify RED**

Expect `ProtectionThresholdPercent` to be `None`.

- [ ] **Step 3: Project `TargetPercent`**

Change only the whitelisted row projection field lookup.

- [ ] **Step 4: Run the tests and verify GREEN**

Expect the canonical threshold percentage and unchanged exact key sets.

---

### Task 4: Accessible Drawer and Recoverable Reevaluation Failures

**Files:**
- Modify: `tests/test_api.py`
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`

**Interfaces:**
- Produces: modal drawer semantics, focus-on-open, app-shell inertness, local Escape close, opener focus restoration, and localized retry feedback for rejected fetch or invalid JSON.

- [ ] **Step 1: Add static/adversarial UI contract tests**

Assert dialog semantics, close-button focus, opener tracking, `inert` background handling, Escape close, focus restoration, and a `try/catch` around both reevaluation fetch and JSON parsing that renders localized recoverable feedback and leaves no unhandled rejection.

- [ ] **Step 2: Run the tests and verify RED**

Expect missing semantics and error guard assertions to fail.

- [ ] **Step 3: Implement focused UI state changes**

Capture the invoking control only on first open, focus the close control, mark the app shell inert while a side drawer is open, close the MTO drawer on Escape, and restore the connected invoking control. Wrap reevaluation transport and decoding in `try/catch`, preserve controls, show the existing localized failure message, and avoid automatic retry.

- [ ] **Step 4: Run the tests and verify GREEN**

Expect static UI tests and bundled Node syntax checks to pass.

---

### Task 5: Verification, Browser Evidence, and One-Wave Commit

**Files:**
- Modify: `docs/mto-order-commitment-task28-evidence-2026-07-12.md`
- Create: `.superpowers/sdd/mto-final-fix-report.md`
- Modify only if counts/evidence require it: `docs/ui-specification.md`, `docs/backend-specification.md`

**Interfaces:**
- Produces: exact automated counts, fresh desktop/mobile screenshots, console/overflow/focus/error-recovery evidence, residual risks, and one final commit.

- [ ] **Step 1: Run compile, bundled Node syntax, focused tests, and full suite**

Use fresh unique `--basetemp` directories and record exact observed counts and warnings.

- [ ] **Step 2: Run real browser acceptance at desktop and 390x844 mobile**

Capture screenshots and assert focus on open, app-shell inertness, Escape close, focus return, localized reevaluation transport failure recovery, zero unhandled errors, and no page overflow.

- [ ] **Step 3: Update evidence accurately**

Append final-fix evidence and correct Task 28 counts only where fresh runs supersede prior claims. Keep `UI-COMMIT-001` at `已验证待用户确认`.

- [ ] **Step 4: Verify diff and commit**

Run `git diff --check`, review the scoped diff, commit all fixes in one wave, and report `DONE`, commit SHA, exact counts, browser evidence, and residual risks.
