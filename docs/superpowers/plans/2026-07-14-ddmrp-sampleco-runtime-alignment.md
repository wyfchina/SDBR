# DDMRP SampleCo Runtime Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align SDBR DDMRP runtime net-flow, priority, and UOM validation behavior with `SampleCowithDemandDrivenMRP.pdf` while preserving DDAE parameter authority.

**Architecture:** Keep `sdbr/ddmrp.py` as the deterministic runtime calculator and `sdbr/ddsop_runtime_planning_input.py` as the contract adapter. Persist the two PDF priority ratios through the immutable replenishment read model, and reject incompatible item-location units before quantities enter the calculator.

**Tech Stack:** Python 3, dataclasses, pytest, existing SDBR immutable DDMRP evaluation ledger.

## Global Constraints

- Cite `BE-DDMRP-003`, `BE-DDMRP-004`, and `BE-DDMRP-006` in tests and specification evidence.
- DDAE continues to own ADU, DLT, Buffer Profiles, adjustment factors, and spike-threshold governance.
- Do not add hidden runtime-package fields or non-contract error codes.
- `CalculatedBySDBR` spike qualification remains rejected until accepted threshold authority exists.
- All implementation is confined to `codex/p1-mto-ddmrp-integration`.

---

### Task 1: Net-flow qualification and PDF priority ratios

**Files:**
- Modify: `tests/test_ddmrp.py`
- Modify: `sdbr/ddmrp.py`

**Interfaces:**
- Consumes: `DemandSignal.is_qualified_spike`, effective `OpenSupply`, frozen zone tops.
- Produces: `PlanningPriorityPercent` and `ExecutionPriorityPercent` on every runtime line.

- [x] **Step 1: Write failing tests** proving a governed spike beyond DLT and effective open supply beyond DLT are included, and priority ratios equal `NFP / TopOfGreen * 100` and `QualifiedOnHand / TopOfRed * 100`.
- [x] **Step 2: Run** `pytest tests/test_ddmrp.py -q` and confirm the new assertions fail because the current evaluator applies DLT cutoffs and omits priority fields.
- [x] **Step 3: Implement** qualification without the plain-DLT secondary filters and calculate nullable priority percentages with zero-denominator protection.
- [x] **Step 4: Run** `pytest tests/test_ddmrp.py -q` and confirm all tests pass.

### Task 2: Contract UOM validation

**Files:**
- Modify: `tests/test_ddsop_runtime_planning_input.py`
- Modify: `sdbr/ddsop_runtime_planning_input.py`

**Interfaces:**
- Consumes: `StockBufferProfiles.UnitOfMeasure`, inventory/demand/supply `UnitOfMeasure`.
- Produces: `DdmrpRuntimeAuthorityError(code="REFERENCE_NOT_FOUND")` for incompatible item-location UOM references.

- [x] **Step 1: Write failing tests** for buffer/inventory, demand/inventory, and supply/inventory UOM mismatches.
- [x] **Step 2: Run** the three tests and confirm they fail because incompatible quantities currently reach `evaluate_ddmrp_net_flow`.
- [x] **Step 3: Implement** one adapter helper that validates all UOM references for each active item-location before constructing DDMRP dataclasses.
- [x] **Step 4: Run** `pytest tests/test_ddsop_runtime_planning_input.py -q` and confirm all contract-adapter tests pass.

### Task 3: Immutable evaluation and workbench propagation

**Files:**
- Modify: `tests/test_ddmrp_replenishment.py`
- Modify: `tests/test_ddmrp_replenishment_view.py`
- Modify: `sdbr/ddmrp_replenishment.py`
- Modify: `sdbr/ddmrp_replenishment_view.py`

**Interfaces:**
- Consumes: runtime-line `PlanningPriorityPercent` and `ExecutionPriorityPercent`.
- Produces: immutable evaluation rows and workbench rows preserving both metrics; existing `BufferPercent` remains a compatibility alias for planning priority.

- [x] **Step 1: Write failing contract-shape and projection tests** for both priority fields.
- [x] **Step 2: Run** the focused replenishment tests and confirm exact-field validation/projection fails.
- [x] **Step 3: Add** both fields to runtime/evaluation row contracts and projections; calculate no second copy in the view.
- [x] **Step 4: Run** the focused replenishment tests and confirm they pass.

### Task 4: Specification evidence and regression verification

**Files:**
- Modify: `docs/ddom-ddmrp-runtime-principles.md`
- Modify: `docs/backend-specification.md`

**Interfaces:**
- Consumes: passing implementation evidence from Tasks 1-3.
- Produces: final `[VERIFIED]` ledger entries and dated change-log evidence.

- [x] **Step 1: Update** runtime principles to distinguish governed spike qualification from DLT and to include all effective open supply.
- [x] **Step 2: Run** `python -m compileall -q sdbr`.
- [x] **Step 3: Run** focused DDMRP and runtime-package tests.
- [x] **Step 4: Run** `pytest -q --basetemp .tmp/pytest-ddmrp-sampleco-full -p no:cacheprovider`.
- [x] **Step 5: Restore** `BE-DDMRP-003/004/006` to `[VERIFIED]` only if all required evidence passes; otherwise leave them `[PARTIAL]` and record the precise remaining gap.
