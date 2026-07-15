# SDBR Development Handoff - 2026-07-16

## 1. Handoff Purpose

This document is the repository handoff for continuing SDBR development on another computer. It summarizes the current DDOM/S-DBR execution boundary, scheduling/release/feedback capabilities, DDAE contract obligations, verification commands, and next development gates.

Read these authoritative files before changing behavior:

- Repository agreement: `AGENTS.md`
- Backend capability ledger: `docs/backend-specification.md`
- UI capability ledger: `docs/ui-specification.md`
- Build, test, and startup guide: `runme.md`
- DDMRP runtime principles: `docs/ddom-ddmrp-runtime-principles.md`
- MTO design: `docs/superpowers/specs/2026-07-10-sdbr-order-commitment-evaluation-design.md`
- DDMRP closure design: `docs/superpowers/specs/2026-07-10-ddmrp-runtime-replenishment-closure-design.md`
- DDMRP SampleCo alignment: `docs/superpowers/specs/2026-07-14-ddmrp-sampleco-runtime-alignment-design.md`
- DDAE contract source of truth: `D:\Documents\DDAE_INTERFACE_CONTRACT`

Do not treat this handoff as a replacement for the backend/UI ledgers or the DDAE contract repository.

## 2. Repository And Git Baseline

As of 2026-07-16:

- Repository: `D:\Documents\SDBR`
- Canonical branch for continued work: `master`
- Canonical commit: `5e40a94 docs: update startup instructions after P1 merge`
- Remote: `git@github.com:wyfchina/SDBR.git`
- `master` and `origin/master` are synchronized (`0 / 0` divergence).
- MTO, DDMRP, and P1 integration work are merged into `master`.
- `codex/p1-mto-ddmrp-integration` is locally aligned to the same commit, but it is no longer required for ordinary startup.
- Component worktrees remain locally available only as development history:
  - `codex/mto-order-commitment`
  - `codex/ddmrp-replenishment`
- `nofinish/` is a temporary/reference directory. Do not track or commit it.
- The old root-level `SDBR-handoff-2026-07-14.md` is untracked and obsolete. This document supersedes it.

On a new computer, clone or fetch `master`; do not reconstruct the integrated result by merging the old component branches again.

```powershell
git clone git@github.com:wyfchina/SDBR.git D:\Documents\SDBR
Set-Location D:\Documents\SDBR
git switch master
git pull --ff-only origin master
git rev-parse --short HEAD
```

Expected commit: `5e40a94` or a later explicitly accepted `master` commit.

Local SQLite databases, `.tmp/` evidence, Simio licenses, ignored PDFs, and other runtime artifacts are not restored by Git. Copy them separately only when their local state is intentionally required.

## 3. DDOM / S-DBR Execution Boundary

SDBR is maintained as the DDOM/S-DBR execution system. Its responsibilities are:

- material feasibility, lightweight MRP, and DDMRP runtime evaluation;
- finite-capacity scheduling and Planning Run lifecycle;
- work-order release evaluation and authorization;
- time-buffer, WIP, and buffer-execution control;
- resource/operation-level MES dispatch suggestions;
- execution-event intake, exception handling, variance capture, and feedback;
- optional post-schedule Simio feasibility validation.

SDBR does **not** own DDS&OP/DDAE governance. Do not implement the following in this repository unless a later explicit scope decision changes the boundary:

- DDS&OP scenario governance or strategic what-if;
- master-setting approval workflows;
- Time Buffer Profile, control-point, resource-role, Stock Buffer Profile, ADU, DLT, adjustment-factor, or spike-threshold governance;
- DDMRP parameter configuration and Buffer Profile editing;
- automatic reinterpretation of DDAE-owned parameters;
- production ERP, MES, WMS, QMS, supplier, inventory, or quality authority.

For DDAE-origin configuration, the mandatory lifecycle is:

**receive -> validate -> freeze -> execute -> feedback**

If a contract is insufficient, write a Contract Agent change request. Never add hidden SDBR-only fields, silently create placeholders, or use UI-side parameter workarounds.

## 4. Scheduling And Planning Run Capability

### 4.1 Active Solver

- `BE-SOLVER-009 [VERIFIED]`.
- OR-Tools CP-SAT is the only active solver for new Planning Runs.
- Gurobi is paused for new execution and retained only for historical-result compatibility.
- Simio is not the primary scheduler; it is optional post-schedule validation.

Current CP-SAT behavior includes finite-resource constraints, operation precedence, alternate resources, setup/changeover, parallel capacity, calendar/capacity windows, capacity buckets, time windows, locks/freeze constraints, time limits, and objective strategies.

### 4.2 Planning Run Freeze And Reference Rules

Planning Runs freeze the selected master-data version, runtime snapshot, release policy, objective strategy, calendars/overrides, and applicable DDAE configuration/runtime-package references.

For a DDAE-contract Planning Run, freeze at least:

- `OperatingModelConfigurationID`
- `OperatingModelFingerprint`
- `SchedulingConfigurationID`
- `DDMRPConfigurationID`

The DDAE integration path must resolve required Product, PrimaryRouting, Resource, Item, and Location references before run creation. Missing references return `REFERENCE_NOT_FOUND`. Do not create placeholder resources, routes, calendars, products, items, or locations and do not downgrade to best-effort planning.

Legacy Planning Run creation remains available for compatibility and is explicitly marked `LegacyNonDdsopConfigInboundV1`; it is not a compliant DDAE contract path.

### 4.3 Worker

Queued Planning Runs require the worker when they are not executed synchronously:

```powershell
python -m sdbr.planning_worker --base-url http://127.0.0.1:8765 --worker-id worker-1
```

The product still needs production-grade worker service deployment, retry scheduling, monitoring, cancellation/timeout operations, and capacity/performance baselines.

## 5. MTO Order Commitment

Capability: `BE-SDBR-010 [PARTIAL]`.

Implemented:

- Mock ERP/API intake of an MTO request;
- immutable evaluation identity and evidence references;
- CCR shadow-capacity assessment using formal bucket semantics and active reservations;
- server-selected operational snapshot with a 60-minute freshness limit;
- material availability check enabled by default, with a recorded planner choice to skip it;
- recommendation-only result and planner final decision;
- planner review when the requested date is possible but CCR protection load is exceeded;
- planner acceptance creates shared Phase 0 demand/capacity/material reservations;
- planner acceptance queues one internal OR-Tools Planning Run that freezes the accepted reservation batch.

Important non-claim: accepting an SDBR recommendation does not itself accept the external customer order and does not mutate DDAE, ERP/MES, master data, inventory, quality, supplier, or production authority.

UI route:

```text
http://127.0.0.1:8765/planner/workbench#order-commitments
```

Still partial:

- accepted CCR protection-threshold authority instead of the controlled/default reference;
- formal external-order acceptance authority;
- production ERP/MES confirmation and writeback;
- complete operator workflow for failed Planning Runs and reservation adjustment/reversal.

## 6. DDMRP Runtime Capability

Capabilities `BE-DDMRP-001` through `BE-DDMRP-007` are `[VERIFIED]`. `BE-DDMRP-008` and `BE-DDMRP-009` are `[NOT-STARTED]` behind Contract Agent gates.

Current runtime rules:

- `NetFlowPosition = QualifiedOnHandQty + QualifiedOpenSupplyQty - QualifiedDemandQty`.
- Qualified demand includes past-due, due-today, and DDAE-qualified spike demand.
- An already-qualified DDAE spike is not truncated again by an ordinary DLT window.
- Effective frozen open supply is not cut off by DLT.
- Received, Completed, Closed, and Cancelled supply is excluded from open supply to prevent double counting.
- Planning status uses Net Flow Position.
- Execution status uses qualified on-hand inventory.
- `PlanningPriorityPercent = NetFlowPosition / TopOfGreen * 100`.
- `ExecutionPriorityPercent = QualifiedOnHandQty / TopOfRed * 100`.
- Zero or negative priority denominators return `null`.
- Red/Yellow positions recommend replenishment to Top of Green, adjusted by MOQ/order multiple.
- Green/AboveGreen positions do not generate replenishment advice.
- Buffer, inventory, demand, and supply UOM must agree for the same item-location.
- SDBR does not calculate spike qualification without accepted threshold/window authority.

Historical compatibility:

- Pre-2.86 immutable rows may lack only the two priority fields.
- The original fingerprint must validate first.
- The read model derives those fields without rewriting history.
- Other schema differences and fingerprint tampering remain rejected.

UI route:

```text
http://127.0.0.1:8765/planner/workbench#material-planning
```

Not yet implemented:

- contract-authorized Buy/Make advice and planner confirmation (`BE-DDMRP-008`);
- Plan BOM feasibility/explosion, Make manufacturing candidate, CCR reservation, lower-level material allocation, and Planning Run bridge (`BE-DDMRP-009`);
- formal ERP/MRP replenishment-order creation;
- DDMRP parameter configuration, which remains outside SDBR scope.

## 7. Release, Buffer Execution, And MES Dispatch

Release and execution are separate stages:

1. Planning Run creates the finite-capacity schedule.
2. Release management decides whether a work order may enter production.
3. Buffer execution tracks released work through time-buffer state and execution events.
4. MES dispatch suggestions rank operations at each resource/work center.

Implemented release behavior:

- `BE-REL-012 [VERIFIED]`: release policy drives rope length, buffer ratios, policy WIP limit, material-check window, and stability thresholds.
- Rope time, material, WIP, inventory risk, and stability are evaluated against the Planning Run frozen policy.
- Authorization records retain policy/configuration/snapshot evidence.
- Snapshot expiry blocks authorization until refresh and re-evaluation; it is not an automatic replan trigger.
- Replan remains a planner decision unless accepted stability thresholds explicitly require escalation.

Buffer and dispatch behavior:

- Buffer Board aggregates release, plan, and execution state.
- MES suggestions are resource/operation queue recommendations, not work-order release decisions.
- Priority evidence includes release eligibility, Late/Red/Yellow/Green/Early state, penetration, planned start, and due date.
- Current MES output is a Mock/canonical suggestion package; SDBR does not directly control MES.
- Real direct-adapter or UNS delivery must preserve the canonical payload semantics and feed acknowledgements/events back into the integration ledger.

`BE-REL-011`, `BE-INT-004`, and `BE-INT-005` remain `[PARTIAL]` because production MES connectivity, durable retry/replay, acknowledgement reconciliation, and broader priority-policy configuration are incomplete.

## 8. Execution Feedback And Simio

Execution feedback supports arrival, dispatch acceptance/rejection, operation start/completion, and exception reporting. It updates buffer/dispatch/variance views.

Operational principle: small delays, breakdowns, and ordinary disturbances should first be absorbed by time buffers, protective capacity, repair/overtime, and execution priority. Do not make automatic replanning the default response.

Simio status:

- optional Mock Runner or local Headless post-schedule validation;
- validation results can report feasibility, throughput, WIP, queue, utilization, and schedule-adherence coverage when the model emits those records;
- Simio does not block publication by default;
- Portal, Server Connector, Experiment automation, concurrent runner service, and publication hard gate remain deferred.

For Simio work, invoke `simio-integration-guide` and update `docs/simio-generation-record.md`.

## 9. DDAE Interface Requirements

The only authority for interface fields, statuses, error codes, examples, ACK, replay, dead-letter, and acceptance criteria is:

```text
D:\Documents\DDAE_INTERFACE_CONTRACT
```

Do not reconstruct contract fields from this handoff or chat memory.

### 9.1 Configuration Inbound

Consume `DDSOP-CONFIG-INBOUND-V1` exactly as contracted:

- schema and semantic validation;
- fingerprint validation;
- status/approval validation;
- reference validation;
- idempotency/replay behavior;
- contracted ACK generation and storage.

Only Approved or Active usable configurations may enter a DDAE-path Planning Run.

### 9.2 Runtime Planning Input

Consume `DDSOP-RUNTIME-PLANNING-INPUT-V1` exactly as contracted:

- only `PackageStatus = AcceptedForBoundedPlanning` may create a package-based run;
- validate source-configuration link and fingerprint;
- validate parameter-authority evidence;
- validate runtime-row and executable-scheduling-row traceability;
- validate numeric values, spike semantics, mapping confidence, scenario compatibility, and canonical consumer rules;
- freeze package identity and `DeliveryLedgerCorrelationID` into the run/ledger context;
- do not silently create missing execution master data.

### 9.3 Feedback Outbound

Generate only contract-defined:

- `PlanningRunFeedbackPublished`
- `VarianceAnalysisFeedbackPublished`

Feedback must retain configuration version, run version, timestamp, data source, exception reason, traceable ID, and delivery-ledger correlation exactly as the contract requires.

Current controlled path supports SDBR push to the DDAE inbound endpoint, DDAE ACK validation, and SDBR delivery-ledger/ACK record. Production retry scheduling, dead-letter operator workflow, long-term persistence, external health monitoring, and operational alerts remain incomplete.

Do not add outbound fields without a Contract Agent addendum.

Public-demo and AdventureWorks payloads are controlled fixture evidence only (`PublicDemoOnly` / `ProductDemoOnly`). They are not production authority, production material feasibility, `ProductionValidated`, or Business Golden Loop readiness.

## 10. Installation, Startup, And Verification

Use `runme.md` as the executable guide. If the new computer uses a different checkout path, change `$SDBR_ROOT` before running commands.

Install:

```powershell
Set-Location D:\Documents\SDBR
python -m pip install -U pip
python -m pip install -e ".[api]"
python -m pip install pytest ortools
```

Start the test service:

```powershell
$SDBR_ROOT = "D:\Documents\SDBR"
Set-Location $SDBR_ROOT
$env:SDBR_ENVIRONMENT = "test"
$env:SDBR_WORKBENCH_DB_PATH = Join-Path $SDBR_ROOT "data\test\workbench-state.db"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
```

Application URL:

```text
http://127.0.0.1:8765/planner/workbench
```

Compile and full regression:

```powershell
python -m compileall -q sdbr
pytest -q --basetemp .tmp\pytest-handoff-full -p no:cacheprovider
```

MTO focused verification:

```powershell
pytest tests\test_ccr_shadow_scheduler.py tests\test_order_commitment_evaluation.py tests\test_order_commitment_view.py tests\test_order_commitment_api.py tests\test_planning_run_reservation_bridge.py tests\test_state_store.py -q --basetemp .tmp\pytest-handoff-mto -p no:cacheprovider
```

DDMRP focused verification:

```powershell
pytest tests\test_ddmrp.py tests\test_ddmrp_replenishment.py tests\test_ddmrp_replenishment_view.py tests\test_ddsop_runtime_planning_input.py tests\test_api.py -q -k "ddmrp or runtime_planning_input" --basetemp .tmp\pytest-handoff-ddmrp -p no:cacheprovider
```

Release/MES/integration verification:

```powershell
pytest tests\test_release_candidates.py tests\test_release_authorization.py tests\test_dispatch_priority.py tests\test_integration_contracts.py -q --basetemp .tmp\pytest-handoff-release -p no:cacheprovider
```

Latest verified evidence for the merged code state:

- `python -m compileall -q sdbr`: passed.
- Full suite before fast-forward merge: `1236 passed, 1 warning`.
- DDMRP post-merge focused suite: `149 passed, 268 deselected, 1 warning`.
- Warning is the existing `StarletteDeprecationWarning` from FastAPI TestClient/httpx compatibility.
- The post-merge documentation-only commit does not alter runtime code.

Use a new `--basetemp` path for each Windows test run; stale pytest directories may remain locked.

## 11. Next Tasks

Recommended order:

1. **New-computer baseline**: clone `master`, install dependencies, run compileall and full pytest, start the test service, and verify `#order-commitments` plus `#material-planning` before changing code.
2. **UI acceptance**: complete user verification of merged MTO/DDMRP pages. Any UI change must update `docs/ui-specification.md` first, implement one acceptance unit, verify it, then stop for explicit user confirmation.
3. **DDMRP contract gates**: request Contract Agent acceptance for planning-advice, target-date/calendar semantics, Plan BOM feasibility, and production authority. Do not start `BE-DDMRP-008/009` before these gates close.
4. **DDMRP operational closure**: after accepted contracts, implement planner-confirmed Buy/Make advice; then Make candidate, CCR reservation, lower-level material allocation, Planning Run bridge, and Mock ERP advice output.
5. **MTO closure**: replace the controlled/default CCR protection threshold with accepted authority input and add external formal-order acceptance only through an accepted ERP contract.
6. **Unified execution loop**: finish reservation adjustment/reversal, event-driven re-evaluation, release/buffer priority linkage, failed-run operator workflow, retry/dead-letter operations, and feedback observability.
7. **Production integration**: service the Planning Run worker, add deployment/monitoring, durable ERP/MES/DDAE delivery retries, ACK reconciliation, and capacity/performance baselines.
8. **Simio enhancement**: only when required, deepen queue/WIP/utilization output and runner operations without making Simio a hidden replacement for CP-SAT or a publication gate.
9. **Branch cleanup**: after the new computer verifies `master`, archive/remove obsolete local worktrees only with explicit approval; do not delete them during migration troubleshooting.

## 12. Non-Claims To Preserve

- No DDS&OP/DDAE configuration governance in SDBR.
- No DDMRP Buffer Profile/ADU/DLT/adjustment-factor governance in SDBR.
- No silent contract-field extension or reference fallback.
- No external customer-order acceptance from an internal MTO recommendation alone.
- No production inventory, quality, supplier, ERP, MES, WMS, or QMS authority.
- No direct MES equipment control.
- No production-material-feasibility claim from public-demo data.
- No `ProductionValidated` claim.
- No Business Golden Loop readiness claim.
- No formal production CP-SAT claim from bounded/public-demo adapter fixtures.

## 13. Suggested Skills

The next agent should invoke relevant skills before acting:

- `superpowers:using-superpowers` - establish the required workflow first.
- `superpowers:systematic-debugging` - investigate runtime or test defects.
- `superpowers:test-driven-development` - implement behavior changes from failing tests.
- `superpowers:writing-plans` - prepare substantial implementation plans.
- `superpowers:executing-plans` - execute an accepted plan in controlled batches.
- `superpowers:using-git-worktrees` - isolate parallel feature work.
- `superpowers:subagent-driven-development` - only for independent tasks with explicit ownership.
- `superpowers:verification-before-completion` - run fresh evidence before completion claims.
- `superpowers:finishing-a-development-branch` - merge, push, and clean up safely.
- `simio-integration-guide` - required for any Simio model/API/headless work.

## 14. First Commands For The Next Agent

```powershell
Set-Location D:\Documents\SDBR
git remote -v
git branch --show-current
git rev-parse --short HEAD
git status --short
git rev-list --left-right --count origin/master...master
python -m compileall -q sdbr
```

Then read `AGENTS.md`, `docs/backend-specification.md`, `docs/ui-specification.md`, and the design documents listed in section 1 before editing files.
