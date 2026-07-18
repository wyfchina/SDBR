# SDBR Development Handoff - Latest

## 1. Purpose

This is the current continuation entry point for a fresh agent or a new
computer. It supplements, rather than duplicates:

- `docs/SDBR-development-handoff-2026-07-16.md`
- `AGENTS.md`
- `docs/backend-specification.md`
- `docs/ui-specification.md`
- `runme.md`

When these files disagree, use `AGENTS.md`, the backend/UI specifications, and
the contract repository as the authority. Do not use chat memory to reconstruct
contract fields.

## 2. Current Git Baseline

- Repository on the current device: `C:\Users\吴一帆\Documents\SDBR`
- Branch: `master`
- Environment-repair implementation baseline: `4203b30`
- Synchronized remote baseline after the 2026-07-18 push: `4203b30`
- Remote: `git@github.com:wyfchina/SDBR.git`
- The six accepted environment-repair commits through `4203b30` are present on
  `origin/master`.
- `nofinish/` is a local temporary/reference directory. Do not track it.
- Old component branches and worktrees are development history; do not merge
  them into `master` again.

Recent commits:

```text
4203b30 docs: make Windows development setup portable
4d4ba61 fix: resolve DDAE assets from portable environment paths
c6a8b29 test: define portable DDAE environment paths
743c760 docs: plan portable development environment repair
67f7f0b docs: clean environment repair design formatting
68bbb6b docs: design portable development environment repair
030f3a4 docs: add MTO scenario seed instructions
```

First commands on another computer:

```powershell
$SDBR_ROOT = (Resolve-Path (Join-Path $HOME "Documents\SDBR")).Path
$DDAE_CONTRACT_ROOT = (
  Resolve-Path (Join-Path $HOME "Documents\DDAE_INTERFACE_CONTRACT")
).Path
Set-Location $SDBR_ROOT
$env:DDAE_INTERFACE_CONTRACT_ROOT = $DDAE_CONTRACT_ROOT
New-Item -ItemType Directory -Force .tmp | Out-Null
git switch master
git pull --ff-only origin master
git rev-parse --short HEAD
git status --short
git rev-list --left-right --count origin/master...HEAD
```

After pulling, `HEAD` must contain the environment-repair baseline `4203b30`.
The exact current `HEAD` may be newer because this handoff is versioned as a
separate documentation commit.

## 3. Product Boundary

SDBR is a DDOM/S-DBR execution system. It owns:

- material feasibility and lightweight MRP;
- DDMRP runtime evaluation and replenishment advice;
- finite-capacity scheduling with OR-Tools CP-SAT;
- Planning Run lifecycle and frozen evidence;
- work-order release management;
- time/inventory/capacity buffer execution;
- MES dispatch suggestions;
- execution feedback and variance capture;
- optional post-schedule Simio validation.

SDBR does not own DDS&OP/DDAE governance. In particular, do not add:

- DDMRP Buffer Profile, ADU, DLT, variability-factor, adjustment-factor, or
  spike-threshold configuration;
- DDS&OP scenarios, master-setting approval, or strategic what-if;
- silent interpretation of DDAE fields;
- production ERP/MES/WMS/QMS/inventory/quality/supplier authority.

DDAE-origin configuration must follow:

```text
receive -> validate -> freeze -> execute -> feedback
```

If the contract is insufficient, write a Contract Agent change request instead
of adding hidden SDBR-only fields.

## 4. Scheduling, Release, And Feedback

- OR-Tools CP-SAT is the only active solver for new Planning Runs.
- Gurobi remains paused for new execution.
- Simio is optional validation, not the primary scheduler and not a publication
  gate.
- Planning Runs freeze master-data/runtime snapshots, calendars, policies,
  objective settings, and applicable DDAE configuration/package references.
- DDAE-path runs must resolve required Product, Routing, Resource, Item, and
  Location references. Missing references must fail with
  `REFERENCE_NOT_FOUND`; never create placeholders.
- Release management decides whether a scheduled work order may enter
  production.
- Buffer execution controls released work.
- MES dispatch suggestions rank operations at a resource; they do not replace
  work-order release.
- Small disturbances should first be absorbed by buffers, protective capacity,
  repair/overtime, and priority control. Replanning is not the default response.

Detailed capability status is maintained in `docs/backend-specification.md`.

## 5. MTO Order Commitment: Latest Delta

The latest work adds repeatable, algorithm-driven MTO browser scenarios. It
does not insert precomputed evaluation results into the database.

Run:

```powershell
$SDBR_ROOT = (Resolve-Path (Join-Path $HOME "Documents\SDBR")).Path
Set-Location $SDBR_ROOT
pwsh -File .\scripts\seed_mto_order_commitment_browser.ps1 `
  -BaseUrl http://127.0.0.1:8765 `
  -OutputPath .tmp\mto-order-commitment-browser-fixture.json
```

Page:

```text
http://127.0.0.1:8765/planner/workbench#order-commitment
```

Business cases:

| OrderID | Expected behavior |
| --- | --- |
| `TST-MTO-SO-ON-TIME-REFERENCE` | On-time, material feasible, CCR load 180 -> 240 minutes (50%), planner confirmation required |
| `TST-MTO-SO-OVER-PROTECTION` | On-time, material feasible, CCR load 180 -> 420 minutes (87.5%), planner confirmation required because the reference protection line is exceeded |
| `TST-MTO-SO-LATER-SAFE-DATE` | Requested date lacks CCR capacity; the engine selects the next feasible safe date |
| `TST-MTO-SO-MATERIAL-SHORTAGE` | Capacity is possible but material is short; do not recommend acceptance |
| `TST-MTO-SO-MATERIAL-SKIPPED` | Planner explicitly skips the material check; result remains pending planner confirmation |

Lifecycle cases also prove planner accept, reject, and stale-evaluation
handling. Planner acceptance creates internal reservations and queues one
internal Planning Run; it does not itself accept the external customer order or
write ERP/MES.

Relevant artifacts:

- `scripts/seed_mto_order_commitment_browser.ps1`
- `tests/test_order_commitment_api.py`
- `runme.md`, section 10.1
- `docs/superpowers/specs/2026-07-16-mto-multiple-test-orders-design.md`
- `docs/superpowers/plans/2026-07-16-mto-multiple-test-orders.md`

Latest focused verification:

```text
291 passed, 1 existing Starlette deprecation warning
```

## 6. DDMRP Runtime Rules

Authoritative runtime interpretation:

- `docs/ddom-ddmrp-runtime-principles.md`
- `docs/superpowers/specs/2026-07-14-ddmrp-sampleco-runtime-alignment-design.md`
- `sdbr/ddmrp.py`

Current formulas:

```text
NetFlowPosition =
    QualifiedOnHandQty
    + QualifiedOpenSupplyQty
    - QualifiedDemandQty

PlanningPriorityPercent =
    NetFlowPosition / TopOfGreen * 100

ExecutionPriorityPercent =
    QualifiedOnHandQty / TopOfRed * 100
```

Runtime decisions:

- Red or Yellow planning status recommends replenishment.
- Green or Above Green does not recommend replenishment.
- Replenishment target is Top of Green, adjusted by MOQ and order multiple.
- Planning status uses Net Flow Position.
- Execution status uses qualified on-hand inventory.
- DDAE-qualified spikes are not truncated again by a plain DLT window.
- Effective frozen open supply is not cut off by DLT.
- Received/closed/cancelled supply is not counted as open supply.
- Inventory, supply, demand, and buffer quantities must share a compatible UOM.

Parameter rationale:

- Yellow protects expected consumption during DLT.
- Red protects variability.
- Green controls order cycle and typical order size.
- Recommended DDMRP profile ranges are starting guides, not statistical laws.
- DDAE/DDS&OP owns profile/factor selection and approval. SDBR consumes the
  frozen zone results and returns operational evidence.

Do not add a DDMRP parameter configuration UI to SDBR.

## 7. DDAE Contract Requirements

The sole source of truth is selected by `DDAE_INTERFACE_CONTRACT_ROOT`. On the
current device it is:

```text
C:\Users\吴一帆\Documents\DDAE_INTERFACE_CONTRACT
```

The runtime keeps `D:\Documents\DDAE_INTERFACE_CONTRACT` only as a legacy
fallback when the environment variable is absent.

SDBR must consume exactly the accepted versions of:

- `DDSOP-CONFIG-INBOUND-V1`
- `DDSOP-RUNTIME-PLANNING-INPUT-V1`
- `DDSOP-FEEDBACK-OUTBOUND-V1`

Planning Runs on the DDAE path freeze at least:

- `OperatingModelConfigurationID`
- `OperatingModelFingerprint`
- `SchedulingConfigurationID`
- `DDMRPConfigurationID`
- applicable runtime package and delivery-ledger correlation references

Only approved/active usable configuration and
`PackageStatus = AcceptedForBoundedPlanning` may create the corresponding
contract-path Planning Run.

Feedback is limited to the contract-defined Planning Run and variance feedback
payloads. Do not add fields without Contract Agent acceptance.

Public-demo/AdventureWorks data remains controlled fixture evidence only. It
does not establish production authority, production material feasibility,
`ProductionValidated`, or Business Golden Loop readiness.

## 8. Startup

Always define `$SDBR_ROOT` before using `Join-Path`:

```powershell
$SDBR_ROOT = (Resolve-Path (Join-Path $HOME "Documents\SDBR")).Path
$DDAE_CONTRACT_ROOT = (
  Resolve-Path (Join-Path $HOME "Documents\DDAE_INTERFACE_CONTRACT")
).Path
Set-Location $SDBR_ROOT
$env:DDAE_INTERFACE_CONTRACT_ROOT = $DDAE_CONTRACT_ROOT
New-Item -ItemType Directory -Force .tmp | Out-Null
$env:SDBR_ENVIRONMENT = "test"
$env:SDBR_WORKBENCH_DB_PATH = Join-Path $SDBR_ROOT "data\test\workbench-state.db"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
```

Application:

```text
http://127.0.0.1:8765/planner/workbench
```

Use `runme.md` for installation, database reset, worker startup, MTO scenarios,
DDMRP checks, and other operational commands.

## 9. Verification Commands

Compile:

```powershell
python -m compileall -q sdbr
```

Full regression:

```powershell
python -m pytest -q --basetemp .tmp\pytest-handoff-full -p no:cacheprovider
```

MTO:

```powershell
python -m pytest tests\test_order_commitment_api.py `
  tests\test_order_commitment_evaluation.py `
  tests\test_order_commitment_view.py `
  -q --basetemp .tmp\pytest-handoff-mto -p no:cacheprovider
```

DDMRP:

```powershell
python -m pytest tests\test_ddmrp.py `
  tests\test_ddmrp_replenishment.py `
  tests\test_ddmrp_replenishment_view.py `
  tests\test_ddsop_runtime_planning_input.py `
  -q --basetemp .tmp\pytest-handoff-ddmrp -p no:cacheprovider
```

Git:

```powershell
git diff --check
git status --short
git rev-list --left-right --count origin/master...HEAD
```

Use a new `--basetemp` directory for each Windows test run to avoid stale file
locks.

## 10. 2026-07-18 New-Device Environment Repair Evidence

Applicable backend specifications: `BE-RUN-010`, `BE-INT-008`.

The portable environment repair is implemented locally and verified:

- the migrated package directory is normalized to lowercase `sdbr/`;
  `import sdbr` succeeds with `PYTHONCASEOK` unset;
- user `DDAE_INTERFACE_CONTRACT_ROOT` is
  `C:\Users\吴一帆\Documents\DDAE_INTERFACE_CONTRACT`;
- Python 3.12 Scripts appears exactly once in the user `PATH`, and direct
  `pytest --version` reports `pytest 9.0.2` after a normal PATH refresh;
- PowerShell is installed as Microsoft Store/MSIX package version `7.6.3`, and
  `pwsh --version` reports `PowerShell 7.6.3`;
- `python -m pip check`: no broken requirements;
- `python -m compileall -q sdbr`: exit code 0, no output;
- new environment-path tests: `4 passed` after an observed missing-module RED;
- focused contract/public-demo migration tests: `91 passed` after an observed
  `84 failed, 3 passed` old-path RED;
- MTO suite: `291 passed in 43.41s`;
- full regression: `1243 passed in 125.16s`;
- Uvicorn startup completed and `/planner/workbench` returned HTTP 200 with
  `text/html; charset=utf-8`; the service was stopped and port 8765 released.

Repository hygiene after verification and publication:

- `docs/SDBR-development-handoff-latest.md` is tracked as the continuation entry
  point;
- `nofinish/` remains an intentionally untracked local reference directory;
- the six environment-repair commits were pushed, and local `master` matched
  `origin/master` at `4203b30` before this documentation commit.

## 11. Recommended Next Tasks

1. Perform user-facing acceptance of the five MTO scenarios and confirm that the
   displayed reason, load before/after, material state, selected safe date, and
   planner decision match the generated evidence file.
2. Keep DDMRP parameter governance outside SDBR. If planners need help
   understanding parameters, add read-only business explanations only after
   updating `docs/ui-specification.md`.
3. Close Contract Agent gates before implementing DDMRP Buy/Make advice,
   target-date/calendar semantics, Plan BOM feasibility, manufacturing
   candidates, lower-level allocation, or ERP/MRP output.
4. Replace the MTO controlled/default CCR protection reference only after an
   accepted authority contract exists.
5. Continue the unified execution loop: reservation adjustment/reversal,
   event-driven reevaluation, failed Planning Run recovery, durable delivery
   retries, ACK reconciliation, and operational observability.
6. Do not remove old worktrees or branches during migration troubleshooting
   without explicit approval.

## 12. Suggested Skills

The next agent should invoke:

- `superpowers:using-superpowers`
- `superpowers:systematic-debugging` for failures
- `superpowers:test-driven-development` for behavior changes
- `superpowers:writing-plans` for substantial work
- `superpowers:executing-plans` for accepted plans
- `superpowers:using-git-worktrees` for isolated feature branches
- `superpowers:verification-before-completion`
- `superpowers:finishing-a-development-branch`
- `simio-integration-guide` for any Simio work
- `handoff` when compacting the next long development session

## 13. Non-Claims

- No DDS&OP/DDAE configuration governance in SDBR.
- No DDMRP parameter governance in SDBR.
- No silent contract extension or master-data fallback.
- No external customer-order acceptance from an internal recommendation alone.
- No direct production MES control.
- No production inventory, quality, supplier, ERP, MES, WMS, or QMS authority.
- No `ProductionValidated` claim.
- No Business Golden Loop readiness claim.
- No production CP-SAT claim from controlled public-demo fixtures.
