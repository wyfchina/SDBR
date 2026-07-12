# MTO Order Commitment Task28 Evidence Report

**Date:** 2026-07-12

**Specifications:** `UI-COMMIT-001`, `BE-SDBR-010`

**Result:** DONE - implementation and evidence verified; user confirmation remains pending.

## Scope

Task28 closes the reproducible API seed, real SQLite-backed server smoke, browser acceptance, and UI evidence for the MTO order commitment workbench. It does not create an automatic Planning Run, accept an external order, or mutate DDAE, ERP/WMS, MES, supplier, master-data, or production authority.

## Preserved Work Review

The resumed uncommitted changes were reviewed before execution:

- `scripts/seed_mto_order_commitment_browser.ps1` uses only public HTTP endpoints and writes only its requested fixture JSON.
- `TestOrderCommitmentBrowserSequence` creates ordinary, skipped-material, accepted, rejected, and stale-decision states, repeats the stale request, and asserts no ledger mutation or automatic Planning Run.
- `planner-workbench.js` adds missing Chinese and English business labels used by the already implemented detail, re-evaluation, decision, and trace views.
- The changes match Task28's plan-authorized files and preserve the accepted recommendation-only and external-authority boundaries.

## Automated Verification

Commands and observed results:

```powershell
# Real PowerShell file parse
[System.Management.Automation.Language.Parser]::ParseFile(...)
# PASS, zero parse errors

python -m compileall -q sdbr
# exit 0

pytest tests/test_api.py::TestOrderCommitmentUiShell tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_api.py::TestOrderCommitmentUiDecisionFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence --collect-only -q
# 24 tests collected

pytest tests/test_api.py::TestOrderCommitmentUiShell tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_api.py::TestOrderCommitmentUiDecisionFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence -q --basetemp .tmp/pytest-mto-task28-focused-20260712-1622-8f3c -p no:cacheprovider
# 24 passed, 1 warning in 7.96s

pytest -q --basetemp .tmp/pytest-full-mto-task28-20260712-1624-41d7 -p no:cacheprovider
# 1072 passed, 1 warning in 157.49s

pytest tests/test_api.py::test_ui_commit_specification_is_verified_pending_confirmation_after_task_28 tests/test_api.py::TestOrderCommitmentUiShell tests/test_api.py::TestOrderCommitmentUiReadFlow tests/test_api.py::TestOrderCommitmentUiReevaluation tests/test_api.py::TestOrderCommitmentUiDecisionFlow tests/test_order_commitment_api.py::TestOrderCommitmentUiContract tests/test_order_commitment_api.py::TestOrderCommitmentBrowserSequence -q --basetemp .tmp/pytest-mto-task28-final-focused-20260712-1648-c4e9 -p no:cacheprovider
# 25 passed, 1 warning in 6.18s

pytest -q --basetemp .tmp/pytest-full-mto-task28-final-20260712-1649-f6ad -p no:cacheprovider
# 1072 passed, 1 warning in 128.68s

git diff --check
# no whitespace errors; Git emitted only configured LF-to-CRLF notices
```

The warning is the existing Starlette deprecation notice for `fastapi.testclient` using `httpx`.

## Real Server And Seed

Server:

```powershell
$env:SDBR_ENVIRONMENT = "test"
$env:SDBR_WORKBENCH_DB_PATH = ".tmp/mto-order-commitment-task28-browser-20260712-1628.db"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8876
```

Seed:

```powershell
pwsh -File scripts/seed_mto_order_commitment_browser.ps1 -BaseUrl "http://127.0.0.1:8876" -OutputPath ".tmp/mto-order-commitment-task28-browser-fixture-20260712-1628.json"
```

Observed fixed source data and generated evidence:

- Baseline Planning Run: `TST-MTO-RUN-BASELINE`
- Operational snapshot: `TST-MTO-OPS-CURRENT`
- Ordinary evaluation: `OCE-795e95bfea2265bec618`
- Skipped-material evaluation: `OCE-49db6043f28ccba4ee9e`
- Accepted evaluation: `OCE-452b520aad9440125f47`
- Accepted reservation batch: `PRB-1853f2d9a192e5286126`
- Rejected evaluation: `OCE-0cb271063e645d9a546a`
- Stale evaluation: `OCE-24c6a734d16b88cf8c0b`
- Stale result: `OrderCommitmentEvaluationStale`
- Final workbench revision: `9`

## Browser Evidence

The browser was local Microsoft Edge at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, launched and controlled directly by standalone Playwright. The in-app browser was not used for acceptance evidence.

Desktop proof:

- Viewport and PNG: exactly `1280x720`, DPR 1.
- Document width: `clientWidth=1280`, `scrollWidth=1280`; no page-level horizontal overflow.
- The selected order-commitment route, four summaries, six fixture rows, and exactly 11 table columns rendered.
- The table owns its required horizontal overflow (`clientWidth=976`, `scrollWidth=1265`).

Mobile proof:

- Browser DOM: `innerWidth=390`, `innerHeight=844`, `clientWidth=390`, `clientHeight=844`, DPR 1, screen `390x844`.
- Document: `scrollWidth=390`; no page-level horizontal overflow.
- Every mobile PNG was independently parsed from its PNG IHDR and measured exactly `390x844`.
- The table owns its required horizontal overflow (`clientWidth=362`, `scrollWidth=1265`).
- Navigation drawer rect was `0,0,280,844`; detail drawer stayed within `23.4,0,390,844`; decision dialog stayed within `19,16,371,828` and used internal vertical scrolling.

Key screenshots:

- `.tmp/mto-order-commitment-task28-desktop-1280x720.png`
- `.tmp/mto-order-commitment-task28-desktop-en-detail-1280x720.png`
- `.tmp/mto-order-commitment-task28-mobile-main-390x844.png`
- `.tmp/mto-order-commitment-task28-mobile-nav-390x844.png`
- `.tmp/mto-order-commitment-task28-mobile-detail-controls-390x844.png`
- `.tmp/mto-order-commitment-task28-mobile-decision-controls-390x844.png`
- `.tmp/mto-order-commitment-task28-mobile-material-pending-dialog-390x844.png`
- `.tmp/mto-order-commitment-task28-mobile-stale-error-390x844.png`

## State And Interaction Coverage

- Ordinary awaiting-decision detail exposes re-evaluation plus accept/reject actions.
- Skipped-material detail shows `SkippedPendingConfirmation`, zero material lines, and both CCR and material acknowledgements for conditional acceptance.
- Accepted detail shows the valid reservation batch and no active controls.
- Rejected detail shows the recorded rejection and no active controls.
- Superseded detail shows no active controls.
- Blank material opt-out reason is native-invalid, receives focus, and sends zero re-evaluation requests.
- Decision submit remains disabled with a reason but without required CCR acknowledgement, then enables after keyboard acknowledgement.
- A stale decision sends exactly one POST, receives 409, refreshes the detail, shows the localized stale-evidence message, clears the selected action, and does not retry.
- Chinese-to-English switching translates summaries, all 11 headers, detail sections, actions, material/recommendation/lifecycle/reservation/exception/boundary labels, while IDs remain unchanged and no visible CJK text remains in the English list/detail evidence.
- Keyboard Tab reaches the order-commitment route; Enter opens it. The route and detail action show a solid 3px focus outline. Native checkbox focus is visible and the dialog moves focus to the required acknowledgement.

## Runtime Health And Residual Risk

- Application JavaScript emitted zero uncaught `pageerror` events.
- The only ordinary console resource error was `/favicon.ico` returning 404; all application CSS, JavaScript, workbench, health, list, and detail requests succeeded. The stale-decision 409 was intentional acceptance evidence.
- The Task28 screenshots and SQLite database are `.tmp` evidence and are not committed product assets.
- User confirmation for acceptance unit 13 is still required. The specification is `已验证待用户确认`, not `用户已确认`.
