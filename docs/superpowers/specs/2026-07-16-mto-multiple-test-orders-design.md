# MTO Multiple Test Orders Design

## Goal

Provide multiple reproducible MTO order examples for the local test environment so planners can verify distinct order-commitment outcomes. The examples must use the existing order intake and evaluation APIs. Test data may be synthetic, but recommendation, capacity, material, and promise-date results must be calculated by the production evaluation logic.

## Scope

- Extend `scripts/seed_mto_order_commitment_browser.ps1`.
- Document the script command and expected cases in `runme.md`.
- Add automated tests for the seeded business outcomes.
- Preserve the existing lifecycle examples for acceptance, rejection, stale evaluation, and material-check override.
- Do not modify the MTO order-commitment algorithm, DDAE parameter semantics, production interfaces, or authoritative master data.

## Existing Fixture Basis

The current controlled MTO fixture provides:

- One CCR resource with 480 available minutes in each test day.
- 180 minutes of existing CCR planned load on the requested day.
- A routing that consumes 60 CCR minutes and 30 non-CCR packaging minutes per unit.
- 100 EA of qualified material availability for `TST-MTO-RM-1` at `TST-MAIN`.
- An explicit 80 percent reference protection line because no accepted DDAE protection policy is frozen in this fixture.

The 80 percent line is reference evidence only. It cannot produce an ordinary automatic acceptance recommendation. Any capacity-feasible result that depends on this fallback still requires a planner decision and CCR-risk acknowledgement.

## Business Scenario Set

The script creates the following business examples before it performs any acceptance action, so accepted reservations cannot contaminate the other scenario evaluations.

| Scenario | Controlled input | Expected calculated outcome |
| --- | --- | --- |
| `TST-MTO-SO-ON-TIME-REFERENCE` | Quantity 1; 5 EA material requirement | Requested date is feasible. CCR load changes from 180 to 240 minutes, or 50 percent. Recommendation requires planner confirmation because the protection line is only the 80 percent fallback. |
| `TST-MTO-SO-OVER-PROTECTION` | Quantity 4; 20 EA material requirement | Requested date remains capacity-feasible. CCR load changes from 180 to 420 minutes, or 87.5 percent. Recommendation requires planner confirmation because the reference protection line is exceeded. |
| `TST-MTO-SO-LATER-SAFE-DATE` | Quantity 6; 30 EA material requirement | The requested-day window cannot contain the additional CCR load. The evaluator must calculate a later safe promise date. Under the fallback protection source, the later date still requires planner confirmation. |
| `TST-MTO-SO-MATERIAL-SHORTAGE` | Quantity 1; 120 EA material requirement | Capacity remains assessable, but qualified material availability is insufficient. The recommendation is not to accept until material evidence changes. |
| `TST-MTO-SO-MATERIAL-SKIPPED` | Quantity 1; 5 EA material requirement; planner re-evaluation with material check disabled and a reason | The result is capacity-only. Material remains pending confirmation, and the planner must make the final decision. No full material-feasibility claim is allowed. |

Exact recommendation codes are asserted from the API response. The business-facing script report also records capacity status, threshold state, material status, selected promise date, CCR load before and after, and load percentage.

## Lifecycle Scenario Set

The existing operational examples remain, but their names and output group identify them as lifecycle tests rather than distinct capacity or material cases:

- planner accepts the requested date;
- planner rejects the order;
- a stale evaluation fingerprint is rejected with HTTP 409;
- accepted order creates an internal CCR reservation and queued Planning Run;
- external ERP/MES acceptance remains unexecuted.

Where possible, lifecycle actions reuse a business scenario evaluation or create a separately named copy. They must not change the expected results already asserted for the five business scenarios.

## Script Behavior

The PowerShell script will:

1. Call `POST /planner/workbench/test-data/order-commitment/reset`.
2. Clone only the controlled intake template inputs.
3. Create all five business evaluations through `POST /planner/workbench/order-commitments/intake`.
4. Re-evaluate the material-skipped case through the public re-evaluation endpoint with a non-empty skip reason.
5. Compare every actual result with its expected business outcome.
6. Stop with a non-zero error if any recommendation, capacity state, material state, threshold state, CCR load, or safe-date expectation differs.
7. Create the separate lifecycle examples and verify their API outcomes.
8. Write a local JSON evidence summary under `.tmp/`.

The script must not directly write the SQLite database or insert precomputed evaluation rows.

## Runbook Entry

`runme.md` will include:

- prerequisite: the local service is running at `http://127.0.0.1:8765`;
- the PowerShell command for seeding the MTO scenarios;
- the output evidence path;
- the order-commitment page route;
- a concise expected-results table;
- a warning that the reset endpoint clears existing MTO evaluation, reservation, and related test state.

## Verification

Automated verification will cover:

- all five scenario IDs exist;
- each scenario returns the expected capacity, material, threshold, and recommendation outcome;
- the safe-date scenario selects a date later than the requested date;
- the skipped-material scenario records the skip reason and never claims material feasibility;
- the accepted lifecycle scenario creates a CCR reservation and an internal queued Planning Run;
- the stale decision remains rejected;
- no production authority data is created or mutated.

## Specification Traceability

- Backend: `BE-SDBR-010` MTO order commitment evaluation and planner decision workflow.
- UI: `UI-COMMIT-001` order commitment workbench and business-facing outcome display.

This change adds repeatable test evidence only. It does not change either capability boundary.
