# DDMRP Runtime Replenishment Closure Staged Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First deliver an authority-correct, immutable DDMRP runtime evaluation and read-only replenishment workbench; preserve planner-confirmed Buy/Make and atomic Make candidate/CCR/material activation as an explicitly blocked second tranche that cannot execute until Contract Agent-accepted target-time, ERP/MRP advice, Plan BOM/feasibility, and production-authority evidence exists. Transfer remains a separate deferred non-claim outside both executable NOW scope and this activation blueprint.

**Architecture:** Keep `sdbr/ddmrp.py` as the pure V1 net-flow engine and keep `sdbr/ddsop_runtime_planning_input.py` as the only current consumer of `DDSOP-RUNTIME-PLANNING-INPUT-V1`. Add an immutable evaluation/recommendation ledger and safe workbench projection now, but record missing operational authority as structured gates rather than accepting caller-asserted advice or deriving an unsupported target date. After the external gate is accepted, a fresh contract-mapping revision may activate Buy/Make confirmation; Make then uses the shared reservation foundation through copy-on-write composite staging and extends the Planning Run frozen graph so the candidate, CCR reservations, and material allocations have one lifecycle.

**Tech Stack:** Python 3.11+ (the current test runtime is Python 3.12), FastAPI, Pydantic v2, dataclasses, the existing memory/SQLite `WorkbenchStateStore`, pytest, vanilla HTML/CSS/JavaScript, and the in-app browser for reproducible visual verification.

## Execution Labels And Hard Stops

- **NOW:** executable against the repository and accepted contracts as they exist on 2026-07-11.
- **GATE:** Contract Agent-owned evidence that must exist before any activation task starts.
- **BLOCKED-ACTIVATION:** exact SDBR invariants and review boundaries for the eventual business behavior, but not executable while `CONTRACT-GATE-DDMRP-ACTIVATION-001` is closed.
- Completing NOW does **not** close planner confirmation or Make activation. It closes only immutable evaluation and the read-only workbench.
- After the NOW UI acceptance unit is implemented and verified, stop and request explicit user confirmation before starting another UI unit.
- Even after that UI confirmation, no BLOCKED-ACTIVATION task may start until the Contract Agent gate is open.

## Current Authority Facts Verified On 2026-07-11

| Authority surface | Current fact | Consequence |
| --- | --- | --- |
| `DDSOP-RUNTIME-PLANNING-INPUT-V1` | Contract status is `Reviewed Draft`; its schema has `AvailableQty`, `OperationalStateSnapshotID`, `SnapshotAt`, evidence refs, scenario/mapping confidence, and production-authority labels. | Safe read-only evaluation is possible after normal package validation. |
| Inventory availability | `AvailableQty` is an explicit ERP/WMS/QMS authority field. Valid quality states are `Unrestricted`, `Inspection`, `Blocked`, and `Released`. | Consume `AvailableQty` exactly. Never add `Released`-only reinterpretation and never use `InspectionHold`. |
| DLT target semantics | `DDSOP-CONFIG-INBOUND-V1` has `DLTMinutes` and configuration `TimeZone`, but no elapsed-vs-working-minute rule, receipt calendar, holiday/shift rule, or target-date policy ID/fingerprint. | `StandardTargetReceiptAt` remains `null` with `DLT_TARGET_SEMANTICS_INSUFFICIENT`; no `timedelta` target is authorized. |
| Advice/BOM authority | No accepted inbound ERP/MRP Buy/Make advice package or Plan BOM package exists. The current runtime schema has routings/operations for bounded scheduling but no `BomVersionID`, routing version, replenishment advice authority, or dependent-demand feasibility package. | The operational API must not accept raw advice/capacity/material rows. Buy/Make remains blocked. |
| Production evidence | `PRODUCTION-INVENTORY-QUALITY-EVIDENCE-V1` and `SDBR-EXECUTION-OBJECT-EVIDENCE-V1` are Reviewed Draft contracts. Current reviewed fixtures produce `SourceAuthoritativeUsable=False`. | Reviewed/public-demo fixtures can explain a workbench row but cannot create shared operational reservations. |
| Public demo package | The golden package is `ScenarioLabel=ControlledContractGoldenLoopDemo`, `MappingConfidence=PublicDemoOnly`, and parameter evidence is `ProductionAuthorityStatus=PublicDemoOnly`. | It is a required negative test for operational confirmation. |
| Shared demand identity | `LogicalDemandKey` excludes `SourceObjectVersion` but includes `SourceObjectID`. | MTA demand must use a stable logical replenishment ID as `SourceObjectID`, never a per-evaluation recommendation ID. |
| Shared reservation apply | `apply_reservation_write_set(...)` validates and mutates in one call; no public preflight-only function exists. | Eventual DDMRP/shared composition must stage against deep copies and publish only a fully validated replacement graph. |
| Planning Run bridge | `freeze_planning_reservations(...)` and `transition_planning_reservations_for_run(...)` freeze demand/batch/capacity/material only. | Make activation cannot be complete until candidate identity and lifecycle are added to this graph. |

## Global Constraints

- SDBR remains a DDOM / S-DBR execution system. DDAE/DDS&OP owns Buffer Profiles, adjustment factors, decoupling-point design, and master-setting approval.
- Preserve the accepted `DDSOP-RUNTIME-PLANNING-INPUT-V1` and `DDSOP-CONFIG-INBOUND-V1` schemas. Do not add SDBR-only contract fields or reinterpret accepted field meanings.
- Red and Yellow rows may create versioned replenishment recommendation records. Green and AboveGreen remain zero-quantity monitor rows.
- NOW recommendations are read-only and may be `Blocked`; no Buy/Make action, demand commitment, candidate, CCR reservation, or material allocation is created.
- A missing contract field produces a named structured gate. It never produces a local default, inferred routing/BOM, synthetic calendar, or request-body authority row.
- ERP/MRP remains authoritative for source selection, Plan BOM, routing/version, formal production/purchase orders, and external order acceptance. ERP/WMS/QMS remains authoritative for inventory, allocation, movement, and quality facts.
- Public-demo, reviewed, fixture-seeded, candidate-only, or unresolved evidence cannot mutate operational shared reservation ledgers.
- Preserve OR-Tools CP-SAT as the only executable solver for new Planning Runs. This work does not change Gurobi or Simio scope.
- Do not expose raw DDAE payloads, ERP/MRP evidence, BOM rows, capacity requests, material requests, or raw JSON in the planner workflow.
- Focused single-capability test modules use an exact module docstring naming their applicable `BE-*`/`UI-*` acceptance IDs. Multi-capability modules such as `tests/test_api.py` use an exact comment on every new test; the DDMRP RBAC tests cite `BE-OPS-001` as well as the applicable DDMRP/UI ID.
- The approved design's eventual Transfer behavior is intentionally not claimed by `BE-DDMRP-008`, `BE-DDMRP-009`, or `UI-DDMRP-004` in this plan. Transfer requires accepted source-selection, feasibility, governance, and authority evidence plus a future specification revision and implementation plan.
- Do not modify `nofinish/`.

## Review Finding Closure Map

| Finding | Closure in this revision |
| --- | --- |
| C1 caller-asserted advice | NOW API accepts only stored runtime package ID plus request ID; raw authority extras are 422. The named Contract Agent gate owns future advice acceptance. |
| C2 Phase 3 writes before feasibility | NOW has no confirmation/shared writes. Activation A2 completes BOM/material/CCR preview before A4/A5 can create a graph. |
| C3 unsupported target time | NOW target is null with `DLT_TARGET_SEMANTICS_INSUFFICIENT`; the gate requires the accepted business-time/calendar rule before activation. |
| C4 inventory reinterpretation | Task 2 consumes `AvailableQty` directly through schema-valid package processing and uses only contract-valid quality states. |
| C5 incomplete freshness | Task 3 defines every runtime/config/advice/BOM/material/capacity ID/fingerprint pair; A1 has one drift test per source. |
| C6 duplicate active replenishment | Task 4 establishes stable chain/cycle/version identity; A3/A5 enforce adjustment or release before another active graph. |
| C7 demo authority overreach | Public-demo/reviewed inputs are mandatory read-only negative cases and can never reach the shared apply path. |
| I1 undefined composite atomicity | A5 specifies deep-copy staging, reuse of the real shared apply on copies, full-graph validation, rollback-safe live replacement, and failure injection at each boundary. |
| I2 placeholders/partial snippets | NOW tasks give exact paths, public signatures, record fields, named tests, RED/GREEN commands, response shapes, and commit boundaries. Contract-dependent mappings are deliberately outside the executable tranche instead of being guessed. |
| I3 oversized tasks | Evaluation build/apply/store/view/API/seed/UI are separate commits; activation authority/feasibility/lifecycle/shared write/composite apply/bridge/API/UI are separate review gates. |
| I4 incomplete lifecycle/bridge | Immutable recommendation events, bidirectional version links, active/history projection, full candidate states, and candidate-aware Planning Run freeze/transition are explicit. |
| I5 wrong UI/API interface | UI parses `{Endpoint, StatusCode, Data}`, retains `X-Workbench-Revision`, and uses existing `showNotification`; exact GET/POST shapes are fixed. |
| I6 RBAC/audit/impact/retry | Viewer/Worker/Planner/Admin behavior, server principal/time, retained UUID, real reason, impact dialog, pending disable, `If-Match`, and lost-response replay are explicit. |
| M1 zero-test selector | Task 10 requires and selects one exact `test_ui_ddmrp_003_...` function. |
| M2 mutable Pydantic defaults | New request models contain no list defaults; any future list model must use `Field(default_factory=list)` unconditionally. |
| M3 browser reproducibility | Tasks 11/12 create and test the seeded/empty/error/403/409 acceptance app, verify the exact catalog/workbench case, preflight the port, bound health retries, guarantee `try/finally` shutdown, and name report/screenshot evidence at 1280/1920/390 viewports. |
| M4 spec versions/date | `2.80 -> 2.81` and `5.35 -> 5.36`, all dated `2026-07-11`, are exact and justified. |
| M5 global-only traceability | The per-test table at the end requires module/test-level BE/UI edits in every touched test file. |
| Round-2 I1 NOW replay/global revision | Task 3 replaces the global store revision with a canonical DDMRP-relevant planning-ledger identity. Tasks 4/5 persist an immutable request-result record, and Task 8 performs exact lookup/graph validation before rebuilding. |
| Round-2 I2 strict model/runtime time | Task 8 imports `ConfigDict`/`TypeAdapter`, forbids request extras, parses `RuntimeEvidenceSnapshot.SnapshotAt` once, normalizes it to UTC `+00:00`, and passes the same normalized `datetime` to signature and evaluation builders. |
| Round-2 I3 activation freshness/replay | The signature includes target-policy ID/version/fingerprint and calendar version. A5 persists exact confirmation request/results and validates replay before freshness; A7 performs the same route ordering, including stale-`If-Match` lost-response retry. |
| Round-2 I4 identity/execution facts | Task 4 hashes canonical structured JSON and tests delimiter-shaped identifiers. Gated A3 defines the exact V2 candidate/formal-supply adapter, count-once handoff, cancellation/release, allocation exclusion, residual need, and signed adjustment delta while preserving the active-graph guard. |
| Round-2 I5 exact lifecycle/projections/persistence | Tasks 4/5 define exact event/issue/request-result fields, fingerprints, creation folds, reused-chain membership, and orphan rejection; Task 7 fixes every nested allowlist; gated A6P persists and binds all thirteen composite ledgers before A7. |
| Round-2 I6 RED/GREEN evidence | Every NOW task that adds tests has matching exact-node RED/GREEN commands, an expected RED reason, and explicit selected/pass counts; Task 9 uses the identical seed node in both phases. |
| Round-2 M1 browser reproducibility | Tasks 9/11/12 add tested acceptance-only seeded/empty/error/403/409 modes, exact catalog/workbench assertions, a port check, bounded health polling, and `try/finally` shutdown. |
| Round-2 M2 traceability | The final table includes `tests/test_ddmrp_feasibility.py`, per-test API comments, and NOW/activation RBAC coverage of `BE-OPS-001`. |
| Round-2 M3 deferred-action boundary | The executable and blocked activation tasks are Buy/Make-only. The future behavior appears only as an explicit non-claim and requires a later specification revision plus accepted contract-mapping plan. |
| Round-3 I1 confirmation result ordering | A5 replaces the bare processed-key set with an immutable `ActionRequestID` request-result ledger and exact graph validator. A7 performs lookup/validation before `If-Match`, authority, time, build, and freshness; changed reuse is 409 and only unprocessed actions reach freshness. |
| Round-3 I2 active execution facts | A3 defines status allowlists, candidate/formal handoff, runtime-supply matching, count-once arithmetic, terminal behavior, allocation exclusion, residual need, and signed positive/zero/negative adjustment governance with end-to-end tests. |
| Round-3 I3 event/issue contracts | Task 4 enumerates all NOW event payloads and creation versions, supplies complete fold helpers, persists exact issue records, and removes unsupported open-supply fields; Task 5 partitions created and reused chain membership. |
| Round-3 I4 canonical snapshot time | Tasks 3/4/8 freeze one UTC `+00:00` timestamp in signature, run, rows, and fingerprints and test `Z`, positive offset, negative offset, naive, and invalid inputs. |
| Round-3 I5 activation persistence | A6P enumerates all thirteen store fields and covers payload/load/apply/clear/count/snapshot/restore, backward compatibility, `create_app` bindings, memory/SQLite/restart/replay/save-failure/rollback tests. |
| Round-3 I6 seed TDD | Task 9 runs the exact seed node once RED and once GREEN, each with one selected case and explicit expected outcome, then runs a separate broad regression. |
| Round-3 I7 Buy/Make-only activation | No activation algorithm, test, response, UI, or traceability row contains the deferred action; it remains only a future non-claim. |
| Round-3 I8 reproducible browser evidence | Task 11 creates/tests the acceptance app; Task 12 verifies port/health/process cleanup, exact catalog/workbench content, all five modes, and fixed report/screenshot paths. |

## Capability And Version Sequence

The latest changelog rows verified before writing this plan are backend `2.79` dated `2026-07-11` and UI `5.34` dated `2026-07-09`; the document headers are stale (`2.67` and `5.29`). Use the following sequence exactly:

1. Backend `2.80`, date `2026-07-11`: define the staged `BE-DDMRP-007` through `BE-DDMRP-009` boundaries before implementation.
2. UI `5.35`, date `2026-07-11`: define `UI-DDMRP-003` read-only versioned workbench and `UI-DDMRP-004` gated confirmation as separate ordered acceptance units.
3. Backend `2.81`, date `2026-07-11`: only after NOW backend verification, mark `BE-DDMRP-007` `[VERIFIED]`; keep `BE-DDMRP-008` and `BE-DDMRP-009` `[NOT-STARTED]` with the external gate named.
4. UI `5.36`, date `2026-07-11`: only after NOW browser verification, mark `UI-DDMRP-003` `已验证待用户确认`; keep `UI-DDMRP-004` `未开始`.
5. BLOCKED-ACTIVATION must re-read then-current spec versions and allocate the next versions at gate reopening. It must not reuse or preclaim `2.81`/`5.36`.

The two backend versions represent two genuine ledger changes: `2.80` establishes a new staged capability boundary, and `2.81` records verified read-only implementation while explicitly preserving the activation gap.

## File Structure

### NOW files

- Modify `docs/backend-specification.md`: add `BE-DDMRP-007` through `BE-DDMRP-009`, then record only `BE-DDMRP-007` verification.
- Modify `docs/ui-specification.md`: add `UI-DDMRP-003` and `UI-DDMRP-004` as separate acceptance units; complete only `UI-DDMRP-003`.
- Modify `sdbr/ddmrp.py`: expose accepted source IDs/UOM and `QualifiedOnHandQty`; do not calculate a target receipt timestamp.
- Modify `sdbr/ddsop_runtime_planning_input.py`: consume authority `AvailableQty` exactly and preserve source context.
- Create `sdbr/ddmrp_replenishment.py`: own authority signatures, immutable evaluations, stable logical replenishment chains, recommendation versions, events, staging, replay, and gate codes.
- Create `sdbr/ddmrp_replenishment_view.py`: return the safe read-only workbench projection.
- Modify `sdbr/state_store.py`: persist the new immutable ledgers, active-graph registry, and processed keys.
- Modify `sdbr/api.py`: add server-built evaluation/read endpoints with wrapper/RBAC/revision conventions; accept no advice rows.
- Modify `sdbr/test_data.py`: seed a controlled read-only DDMRP acceptance case that remains operationally blocked.
- Modify `sdbr/web/planner-workbench.html`, `sdbr/web/planner-workbench.js`, and `sdbr/web/planner-workbench.css`: render the safe workbench and gate state without confirmation controls.
- Modify `tests/test_ddmrp.py`, `tests/test_ddsop_runtime_planning_input.py`, `tests/test_state_store.py`, `tests/test_api.py`, and `tests/test_test_data.py`.
- Create `tests/test_ddmrp_replenishment.py` and `tests/test_ddmrp_replenishment_view.py`.
- Create `tests/ddmrp_browser_acceptance_app.py`: acceptance-only ASGI fixture modes for reproducible seeded/empty/error/403/409 browser states; never imported by the production app.
- Create `tests/test_ddmrp_browser_acceptance_app.py`: exact fixture-mode contract tests for `UI-DDMRP-003` / `BE-DDMRP-007`.

### BLOCKED-ACTIVATION files

- Modify the new DDMRP domain/view/store/API/UI files only after the gate.
- Modify `sdbr/planning_commitments.py`, `sdbr/planning_reservations.py`, `sdbr/planning_reservation_view.py`, and `sdbr/planning_run_reservation_bridge.py` for stable MTA identity, candidate-aware atomic writes, feasibility projections, and candidate lifecycle.
- Modify their existing tests plus the DDMRP/API/UI tests.
- No external contract schema, example, or acceptance file is authored inside SDBR.

---

## NOW: Contract-Safe Read-Only Tranche

### Task 1: Specification-First Staged Boundary

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes: `BE-DDMRP-001` through `BE-DDMRP-006`, `BE-SDBR-006` through `BE-SDBR-009`, `BE-RUN-011`, `BE-INT-003`, `BE-INT-008`, `UI-DDMRP-001`, and `UI-DDMRP-002`.
- Produces: `BE-DDMRP-007`, `BE-DDMRP-008`, `BE-DDMRP-009`, `UI-DDMRP-003`, and `UI-DDMRP-004`.

- [ ] **Step 1: Verify the source versions and date**

Run:

```powershell
rg -n "^\| 文档版本|^\| 日期|^\| 2\.79 \||^\| 5\.34 \|" docs/backend-specification.md docs/ui-specification.md
```

Expected: backend latest changelog `2.79 / 2026-07-11`; UI latest changelog `5.34 / 2026-07-09`; headers are stale and will be corrected.

- [ ] **Step 2: Add the exact backend targets under version 2.80**

Set the backend header to `2.80`, date `2026-07-11`, and append this changelog row:

```markdown
| 2.80 | 2026-07-11 | 定义 DDMRP 运行补货分阶段边界：先实现权威输入驱动的不可变评估与只读工作台；Buy/Make 确认及 Make 候选/CCR/物料预留保持 Contract Agent 契约门控，不接受调用方自报 ERP/MRP 证据，不声明运行补货闭环完成 |
```

Add these capability rows after `BE-DDMRP-006`:

```markdown
| `BE-DDMRP-007` | 不可变 DDMRP 运行评估与版本化只读补货建议 | `[NOT-STARTED]` | `D` approved design and staged implementation plan | 直接消费已校验运行包 `AvailableQty`；冻结完整权威签名；Red/Yellow 形成稳定逻辑补货链上的不可变版本；缺失目标日期、Advice/BOM/物料/产能或生产权威时返回结构化阻塞；不产生操作写入。 |
| `BE-DDMRP-008` | 契约授权的 Buy/Make 建议与计划员确认治理 | `[NOT-STARTED]` | `D` approved design and staged implementation plan | 仅在 `CONTRACT-GATE-DDMRP-ACTIVATION-001` 关闭项全部验收后启动；建议类型由服务端已验收契约证据决定，计划员逐条确认，身份/时间由服务端记录，当前不得新增调用方自报 advice envelope；Transfer 属于原设计的后续目标，但本验收项不包含且不得声明。 |
| `BE-DDMRP-009` | Make 可行性、计划制造候选和共享 CCR/物料预留 | `[NOT-STARTED]` | `D` approved DDMRP and shared-reservation designs | 仅在已验收 Plan BOM、目标日期、物料/CCR 日历可行性和生产权威证据存在后启动；确认 Make 必须原子创建候选、CCR 预留和下级物料分配，并进入完整 Planning Run 生命周期。 |
```

Do not change `BE-SDBR-006` through `BE-SDBR-009` or `BE-RUN-011` from `[PARTIAL]`.

- [ ] **Step 3: Add two ordered UI units under version 5.35**

Set the UI header to `5.35`, date `2026-07-11`, and append:

```markdown
| 5.35 | 2026-07-11 | 新增 `UI-DDMRP-003` 版本化只读补货评估与契约门控工作台，以及后续 `UI-DDMRP-004` Buy/Make 人工确认单元；两单元分开验收，当前不暴露确认动作或外部订单创建 |
```

Define `UI-DDMRP-003` as the safe read-only evaluation/workbench unit and `UI-DDMRP-004` as the contract-gated **Buy/Make-only** confirmation unit. Add an explicit specification boundary note that Transfer remains deferred until accepted Transfer authority/feasibility/governance evidence, a future backend/UI version, and a fresh implementation plan exist. This narrows the implementation tranche without changing the approved design's eventual product direction. Add section 16 rows in this order:

```markdown
| 13 | DDMRP 版本化评估与契约门控工作台 | UI-DDMRP-003 | 是 |
| 14 | DDMRP Buy/Make 计划员确认 | UI-DDMRP-004 | 是 |
```

`UI-DDMRP-003` starts `未开始`; `UI-DDMRP-004` starts `未开始` and names both the user-confirmation prerequisite for unit 13 and `CONTRACT-GATE-DDMRP-ACTIVATION-001`. Do not change any existing item to `用户已确认`.

- [ ] **Step 4: Verify and commit the specification boundary**

Run:

```powershell
rg -n "2\.80|5\.35|BE-DDMRP-007|BE-DDMRP-008|BE-DDMRP-009|UI-DDMRP-003|UI-DDMRP-004|CONTRACT-GATE-DDMRP-ACTIVATION-001" docs/backend-specification.md docs/ui-specification.md
git diff --check
```

Expected: exact versions/date and five new IDs; activation items remain not started; no new `用户已确认`.

Commit:

```powershell
git add docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: stage DDMRP replenishment authority gates"
```

---

### Task 2: Authority `AvailableQty` And Source Traceability

**Files:**
- Modify: `sdbr/ddmrp.py` at `DemandSignal`, `OpenSupply`, and `_evaluate_point`
- Modify: `sdbr/ddsop_runtime_planning_input.py` at `evaluate_ddmrp_runtime_signals_from_package`
- Modify: `tests/test_ddmrp.py`
- Modify: `tests/test_ddsop_runtime_planning_input.py`

**Interfaces:**
- Preserves: `evaluate_ddmrp_net_flow(...) -> dict[str, object]` and `EvaluationMode="DDMRPNetFlowV1"`.
- Adds: optional `demand_id`, `supply_id`, and `uom`; output `QualifiedOnHandQty`, source IDs/UOM, and runtime inventory context.
- Explicitly does not add `StandardTargetReceiptAt`.

- [ ] **Step 1: Add exact acceptance traceability docstrings**

Use:

```python
"""Acceptance evidence for BE-DDMRP-003, BE-DDMRP-004, BE-DDMRP-005, and BE-DDMRP-007."""
```

in `tests/test_ddmrp.py`, and:

```python
"""Acceptance evidence for BE-DDMRP-007 and BE-INT-008."""
```

in `tests/test_ddsop_runtime_planning_input.py`.

- [ ] **Step 2: Write schema-valid failing authority tests**

Add tests with these exact names:

```python
@pytest.mark.parametrize(
    ("quality_state", "available_qty"),
    [
        ("Unrestricted", 34),
        ("Inspection", 0),
        ("Blocked", 0),
        ("Released", 34),
    ],
)
def test_be_ddmrp_007_consumes_authority_available_qty_without_quality_reinterpretation(
    quality_state: str,
    available_qty: int,
) -> None:
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    inventory = message["Payload"]["RuntimeEvidenceSnapshot"]["InventoryPositions"][0]
    inventory.update(
        {
            "OnHandQty": 42,
            "AllocatedQty": 8,
            "AvailableQty": available_qty,
            "QualityState": quality_state,
        }
    )
    accepted_config = _accepted_configuration_for(message)
    processed = process_runtime_planning_input_message(
        message,
        received_at=RECEIVED_AT,
        accepted_configurations={
            accepted_config["Payload"]["OperatingModelConfigurationID"]: accepted_config
        },
        contract_root=DEFAULT_CONTRACT_ROOT,
    )
    assert processed.processing_status == "Accepted"
    assert processed.package_record is not None

    result = evaluate_ddmrp_runtime_signals_from_package(
        processed.package_record,
        accepted_config,
        evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
    )
    line = result["Lines"][0]
    assert line["QualifiedOnHandQty"] == available_qty
    assert line["OnHandQty"] == available_qty
    assert line["PhysicalOnHandQty"] == 42
    assert line["AuthorityAllocatedQty"] == 8
    assert line["AuthorityAvailableQty"] == available_qty
    assert line["QualityState"] == quality_state
    assert line["Uom"] == inventory["UnitOfMeasure"]
```

Add `test_be_ddmrp_007_preserves_contract_demand_supply_ids_and_uom` and assert `DemandID`, `SupplyID`, and `Uom` from the validated package. Assert `"StandardTargetReceiptAt" not in line`.

- [ ] **Step 3: Run RED**

```powershell
$tests = @(
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_consumes_authority_available_qty_without_quality_reinterpretation',
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_preserves_contract_demand_supply_ids_and_uom'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-available-red -p no:cacheprovider
```

Expected RED: 5 selected cases (four quality-state parametrizations plus one source-ID case), 0 passed, 5 failed because the adapter still uses `OnHandQty` and source/context fields are missing. Record the actual selected/failed counts in the task report.

- [ ] **Step 4: Extend the pure records without changing formulas**

Use these exact dataclass tails so positional compatibility remains:

```python
@dataclass(frozen=True, slots=True)
class DemandSignal:
    item_id: str
    location_id: str
    demand_qty: float
    demand_due_at: datetime
    demand_type: str = "CustomerOrder"
    is_qualified_spike: bool = False
    demand_id: str | None = None
    uom: str | None = None


@dataclass(frozen=True, slots=True)
class OpenSupply:
    item_id: str
    location_id: str
    supply_qty: float
    expected_at: datetime | None
    status: str = "Open"
    supply_id: str | None = None
    uom: str | None = None
```

In `_evaluate_point`, add only:

```python
"QualifiedOnHandQty": buffer.on_hand_qty,
```

and source IDs/UOM to component dictionaries. Do not add a target timestamp.

- [ ] **Step 5: Map the accepted contract exactly**

In `evaluate_ddmrp_runtime_signals_from_package`, use:

```python
authority_available_qty = float(inventory["AvailableQty"])
```

as `InventoryBufferPolicy.on_hand_qty`, regardless of `QualityState`. Populate IDs/UOM from `DemandID`, `SupplyID`, and `UnitOfMeasure`. Join each result line to its already validated inventory row and add:

```python
line.update(
    {
        "PhysicalOnHandQty": float(inventory["OnHandQty"]),
        "AuthorityAllocatedQty": float(inventory["AllocatedQty"]),
        "AuthorityAvailableQty": float(inventory["AvailableQty"]),
        "QualityState": str(inventory["QualityState"]),
        "Uom": str(inventory["UnitOfMeasure"]),
    }
)
```

Do not validate a new quality/availability invariant in SDBR; contract clarification owns any missing invariant.

- [ ] **Step 6: Run GREEN and compatibility tests**

```powershell
$tests = @(
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_consumes_authority_available_qty_without_quality_reinterpretation',
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_preserves_contract_demand_supply_ids_and_uom'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-available-green -p no:cacheprovider
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_api.py -q -k "ddmrp" --basetemp .tmp/pytest-ddmrp-available-regression -p no:cacheprovider
python -m compileall -q sdbr
```

Expected GREEN: the exact focused selection reports 5 passed; the separate regression selection passes with a non-zero recorded count; Green/AboveGreen remain zero and no target timestamp appears.

- [ ] **Step 7: Commit**

```powershell
git add sdbr/ddmrp.py sdbr/ddsop_runtime_planning_input.py tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py
git commit -m "fix: consume authoritative DDMRP availability"
```

---

### Task 3: Complete Read-Only Authority Signature, Relevant Ledger Identity, And Target Gate

**Files:**
- Create: `sdbr/ddmrp_replenishment.py`
- Modify: `sdbr/ddsop_runtime_planning_input.py`
- Create: `tests/test_ddmrp_replenishment.py`
- Modify: `tests/test_ddsop_runtime_planning_input.py`

**Interfaces:**
- Produces `DdmrpAuthoritySignature`, `DdmrpRelevantPlanningLedgerIdentity`, `DdmrpGate`, `canonical_fingerprint(...)`, `build_relevant_planning_ledger_identity(...)`, and `build_read_only_authority_signature(...)`.
- The global `WorkbenchStateStore.current_revision()` is deliberately absent. The local identity changes only when a canonical, item/location-scoped active planning fact changes.
- Every target/advice/BOM/material/capacity authority ID has its exact paired version/fingerprint where defined below; absence is explicit `None`, never omission.
- `build_read_only_authority_signature(...)` receives the already parsed, UTC-normalized evaluation `datetime`; it never re-reads or freezes the raw package timestamp text.

- [ ] **Step 1: Write traceability and all failing tests**

Start `tests/test_ddmrp_replenishment.py` with:

```python
"""Acceptance evidence for BE-DDMRP-007; activation-only cases also trace BE-DDMRP-008 and BE-DDMRP-009."""
```

Add these exact names. Use local imports inside these initial tests so all node IDs collect while the new module is still absent:

```text
test_be_ddmrp_007_signature_freezes_runtime_config_and_all_current_authority_slots
test_be_ddmrp_007_public_demo_signature_is_read_only
test_be_ddmrp_007_missing_target_semantics_returns_named_gate_and_null_target
test_be_ddmrp_007_signature_fingerprint_changes_for_runtime_or_relevant_ledger_drift
test_be_ddmrp_007_rejects_runtime_configuration_reference_mismatch
test_be_ddmrp_007_relevant_ledger_identity_ignores_global_revision_and_unrelated_facts
test_be_ddmrp_007_signature_uses_canonical_snapshot_datetime_not_raw_package_text
test_be_ddmrp_007_rejects_runtime_spike_without_accepted_threshold_authority
```

The first test asserts this complete `asdict(signature)` key set:

```python
{
    "runtime_package_id", "runtime_package_version",
    "runtime_package_fingerprint", "runtime_snapshot_id", "runtime_snapshot_at",
    "operating_model_configuration_id", "operating_model_fingerprint",
    "ddmrp_configuration_id", "target_time_semantics_id",
    "target_policy_id", "target_policy_version", "target_policy_fingerprint",
    "target_calendar_id", "target_calendar_version", "target_calendar_fingerprint",
    "planning_advice_package_id", "planning_advice_package_fingerprint",
    "plan_bom_package_id", "plan_bom_package_fingerprint",
    "material_authority_snapshot_id", "material_authority_snapshot_fingerprint",
    "capacity_calendar_snapshot_id", "capacity_calendar_snapshot_fingerprint",
    "local_planning_ledger_schema_version", "local_planning_ledger_identity",
    "local_planning_ledger_fingerprint", "scenario_label", "mapping_confidence",
    "parameter_authority_fingerprint", "signature_fingerprint",
}
```

- [ ] **Step 2: Run the exact RED selection**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_signature_freezes_runtime_config_and_all_current_authority_slots',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_public_demo_signature_is_read_only',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_missing_target_semantics_returns_named_gate_and_null_target',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_signature_fingerprint_changes_for_runtime_or_relevant_ledger_drift',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_rejects_runtime_configuration_reference_mismatch',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_relevant_ledger_identity_ignores_global_revision_and_unrelated_facts',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_signature_uses_canonical_snapshot_datetime_not_raw_package_text',
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_rejects_runtime_spike_without_accepted_threshold_authority'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-signature-red -p no:cacheprovider
```

Expected RED: 8 selected, 0 passed, 8 failed. The first seven fail on the missing module/symbols or canonical-time contract and the last fails because the adapter does not yet reject unqualified local spike calculation. Record the actual counts.

- [ ] **Step 3: Add exact immutable types and canonical projection field sets**

```python
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class DdmrpGate:
    code: str
    message: str
    blocks_operational_action: bool = True


class DdmrpReplenishmentConflict(ValueError):
    status = "DdmrpReplenishmentConflict"


@dataclass(frozen=True, slots=True)
class DdmrpRelevantPlanningLedgerIdentity:
    schema_version: str
    scope_item_locations: tuple[tuple[str, str], ...]
    identity: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class DdmrpAuthoritySignature:
    runtime_package_id: str
    runtime_package_version: str
    runtime_package_fingerprint: str
    runtime_snapshot_id: str
    runtime_snapshot_at: str
    operating_model_configuration_id: str
    operating_model_fingerprint: str
    ddmrp_configuration_id: str
    target_time_semantics_id: str | None
    target_policy_id: str | None
    target_policy_version: str | None
    target_policy_fingerprint: str | None
    target_calendar_id: str | None
    target_calendar_version: str | None
    target_calendar_fingerprint: str | None
    planning_advice_package_id: str | None
    planning_advice_package_fingerprint: str | None
    plan_bom_package_id: str | None
    plan_bom_package_fingerprint: str | None
    material_authority_snapshot_id: str | None
    material_authority_snapshot_fingerprint: str | None
    capacity_calendar_snapshot_id: str | None
    capacity_calendar_snapshot_fingerprint: str | None
    local_planning_ledger_schema_version: str
    local_planning_ledger_identity: str
    local_planning_ledger_fingerprint: str
    scenario_label: str
    mapping_confidence: str
    parameter_authority_fingerprint: str
    signature_fingerprint: str


def canonical_fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"
```

Define these exact V1 allowlists once; no whole-record `dict(row)` is legal in the relevant-ledger fingerprint:

```python
RELEVANT_DEMAND_FIELDS = (
    "DemandCommitmentID", "DemandSourceType", "SourceSystem", "SourceObjectType",
    "SourceObjectID", "SourceObjectVersion", "DemandLineID", "ItemOrProductID",
    "LocationID", "Quantity", "Uom", "RequiredAt", "DemandClass", "Status",
    "RecordVersion", "ContentFingerprint",
)
RELEVANT_BATCH_FIELDS = (
    "ReservationBatchID", "DemandCommitmentID", "DemandClass", "Status",
    "CapacityReservationIDs", "MaterialAllocationIDs", "PlanningRunID",
    "RecordVersion", "LastTransitionAt", "EventType",
)
RELEVANT_CAPACITY_FIELDS = (
    "CapacityReservationID", "ReservationBatchID", "DemandCommitmentID",
    "DemandClass", "ResourceID", "WindowStartAt", "WindowEndAt",
    "ReservedMinutes", "LatestAllowedCompletionAt", "Status", "PlanningRunID",
    "RecordVersion", "LastTransitionAt", "EventType",
)
RELEVANT_MATERIAL_FIELDS = (
    "MaterialAllocationID", "ReservationBatchID", "DemandCommitmentID",
    "RequirementLineID", "ItemID", "LocationID", "Uom", "AllocatedQty",
    "SupplySourceType", "SupplyID", "MaterialSnapshotID", "ExternalAllocationRef",
    "Status", "RecordVersion", "LastTransitionAt", "EventType",
)
RELEVANT_GRAPH_FIELDS = (
    "LogicalReplenishmentID", "RecommendationID", "ItemID", "LocationID", "Uom",
    "GraphStatus", "DemandCommitmentID", "ReservationBatchID",
    "PlannedManufacturingCandidateID", "FormalSupplyID", "RecordVersion",
)
RELEVANT_DEMAND_STATUSES = frozenset(
    {"Active", "LinkedToFormalOrder", "HeldForPlanningError", "AdjustmentRequired"}
)
RELEVANT_PLANNING_STATUSES = frozenset(
    {"ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError", "AdjustmentRequired"}
)
RELEVANT_GRAPH_STATUSES = frozenset(
    {"ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError", "AdjustmentRequired", "InExecution"}
)
```

- [ ] **Step 4: Build the dedicated relevant-ledger identity**

Use this exact interface:

```python
def build_relevant_planning_ledger_identity(
    *,
    scope_item_locations: Iterable[tuple[str, str]],
    planning_demand_commitments: Mapping[str, Mapping[str, object]],
    planning_reservation_batches: Mapping[str, Mapping[str, object]],
    ccr_capacity_reservations: Mapping[str, Mapping[str, object]],
    material_planning_allocations: Mapping[str, Mapping[str, object]],
    active_replenishment_graphs: Mapping[str, Mapping[str, object]],
) -> DdmrpRelevantPlanningLedgerIdentity:
```

The implementation must normalize `scope_item_locations` to a sorted unique non-empty tuple, select only scoped demand rows in `RELEVANT_DEMAND_STATUSES`, join batches by `DemandCommitmentID`, join capacity/material rows by both batch and demand IDs, and select scoped graphs in `RELEVANT_GRAPH_STATUSES`. For every mapping, the mapping key must equal its canonical ID; missing join targets, duplicate semantic IDs, missing allowlisted required identity/status fields, or non-JSON values raise `DdmrpReplenishmentConflict`.

Sort each exact projection by its canonical ID and fingerprint exactly:

```python
payload = {
    "SchemaVersion": "DdmrpRelevantPlanningLedgerV1",
    "ScopeItemLocations": [
        {"ItemID": item_id, "LocationID": location_id}
        for item_id, location_id in scope
    ],
    "DemandCommitments": demand_rows,
    "ReservationBatches": batch_rows,
    "CapacityReservations": capacity_rows,
    "MaterialAllocations": material_rows,
    "ActiveReplenishmentGraphs": graph_rows,
}
fingerprint = canonical_fingerprint(payload)
return DdmrpRelevantPlanningLedgerIdentity(
    schema_version="DdmrpRelevantPlanningLedgerV1",
    scope_item_locations=scope,
    identity=f"DPL-{fingerprint.removeprefix('sha256:')[:20]}",
    fingerprint=fingerprint,
)
```

No global revision, unrelated workbench collection, out-of-scope item/location, terminal record, audit event, or dictionary insertion order participates. A change to any selected allowlisted field changes both identity and fingerprint. Activation must introduce an explicit V2 before adding candidate/formal-supply fields; it may not silently widen V1.

- [ ] **Step 5: Build the complete read-only authority signature**

Use this exact signature:

```python
def build_read_only_authority_signature(
    *,
    package_record: Mapping[str, object],
    operating_model_configuration: Mapping[str, object],
    relevant_planning_ledger: DdmrpRelevantPlanningLedgerIdentity,
    evaluated_at: datetime,
) -> tuple[DdmrpAuthoritySignature, tuple[DdmrpGate, ...]]:
```

Require `evaluated_at.tzinfo is not None`, `evaluated_at.utcoffset() == timedelta(0)`, and `evaluated_at.isoformat().endswith("+00:00")`; non-canonical input raises `DdmrpReplenishmentConflict`. Re-check the package/config IDs and `canonical_operating_model_fingerprint(...)` exactly as in the prior revision. Hash the accepted package payload and parameter evidence. Set `runtime_snapshot_at=evaluated_at.isoformat()` rather than copying `RuntimeEvidenceSnapshot.SnapshotAt`. Construct `base` with all target policy/calendar, advice, BOM, material-authority, and capacity-authority fields set to `None`, and copy these three local values without consulting the store revision:

```python
"local_planning_ledger_schema_version": relevant_planning_ledger.schema_version,
"local_planning_ledger_identity": relevant_planning_ledger.identity,
"local_planning_ledger_fingerprint": relevant_planning_ledger.fingerprint,
```

Set `signature_fingerprint=canonical_fingerprint(base)`. Return the same four sorted gates from the prior revision: `DLT_TARGET_SEMANTICS_INSUFFICIENT`, `OPERATIONAL_AUTHORITY_NOT_ACCEPTED` when production classification is not accepted, `PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED`, and `PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED`. `StandardTargetReceiptAt` remains absent/null. Public-demo/reviewed rows always receive the operational-authority gate.

- [ ] **Step 6: Add the structured spike-input gate**

Add `DdmrpRuntimeAuthorityError(ValueError)` with `code` and `status="DdmrpRuntimeAuthorityError"`. In `evaluate_ddmrp_runtime_signals_from_package`, raise it with code `SPIKE_QUALIFICATION_INPUT_INSUFFICIENT` when a schema-valid row says `RequiresSDBRQualification`/`CalculatedBySDBR` but the accepted configuration provides no threshold authority. The test passes through `process_runtime_planning_input_message(...)`; it never mutates a stored accepted record.

- [ ] **Step 7: Run the matching GREEN selection and commit**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_signature_freezes_runtime_config_and_all_current_authority_slots',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_public_demo_signature_is_read_only',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_missing_target_semantics_returns_named_gate_and_null_target',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_signature_fingerprint_changes_for_runtime_or_relevant_ledger_drift',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_rejects_runtime_configuration_reference_mismatch',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_relevant_ledger_identity_ignores_global_revision_and_unrelated_facts',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_signature_uses_canonical_snapshot_datetime_not_raw_package_text',
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_rejects_runtime_spike_without_accepted_threshold_authority'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-signature-green -p no:cacheprovider
```

Expected GREEN: 8 selected, 8 passed, 0 failed. The canonical-time case uses raw `SnapshotAt` values `2026-06-30T01:00:00Z` and `2026-06-30T09:00:00+08:00` with the same supplied UTC `datetime` and proves identical `runtime_snapshot_at` and signature fingerprint. Record the actual count, then commit:

```powershell
git add sdbr/ddmrp_replenishment.py sdbr/ddsop_runtime_planning_input.py tests/test_ddmrp_replenishment.py tests/test_ddsop_runtime_planning_input.py
git commit -m "feat: freeze DDMRP authority signatures"
```

---

### Task 4: Exact Immutable Evaluation Records, Folds, And Canonical Replenishment Identity

**Files:**
- Modify: `sdbr/ddmrp_replenishment.py`
- Modify: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Produces `DdmrpEvaluationWriteSet`, `prepare_ddmrp_evaluation(...)`, `canonical_stable_id(...)`, and the exact field/fold constants below.
- Stable chain identity is independent of evaluation ID and is derived from canonical structured JSON, never delimiter concatenation.
- The request result is immutable and becomes the only processed-action authority in Task 5; there is no parallel bare processed-key set.

- [ ] **Step 1: Write every focused failing test**

Add exactly:

```text
test_be_ddmrp_007_red_yellow_create_blocked_versions_green_above_remain_monitor_rows
test_be_ddmrp_007_reevaluation_reuses_logical_chain_and_increments_version
test_be_ddmrp_007_recommendation_predecessor_and_supersession_links_are_bidirectional
test_be_ddmrp_007_active_confirmed_graph_creates_adjustment_required_not_second_actionable_version
test_be_ddmrp_007_terminal_chain_starts_next_cycle_with_new_logical_identity
test_be_ddmrp_007_same_authority_inputs_produce_deterministic_ids_and_fingerprint
test_be_ddmrp_007_logical_identity_uses_canonical_json_for_adversarial_identifiers
test_be_ddmrp_007_immutable_record_field_sets_and_nested_fingerprints_are_exact
test_be_ddmrp_007_event_types_payloads_creation_versions_and_folds_are_exact
test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_illegal_creation_and_status_transitions
test_be_ddmrp_007_issue_records_persist_full_gate_context
test_be_ddmrp_007_supply_components_use_only_authoritative_contract_fields
```

The adversarial test compares at least `("A|B", "C", 1)` with `("A", "B|C", 1)`, plus JSON-looking identifiers such as `('{"x":1}', '[x]', 2)`, and proves every structured identity and ID differs. NOW recommendations assert `AdviceType is None`, `StandardTargetReceiptAt is None`, `InitialStatus == "Blocked"`, and all four gate codes. Green/AboveGreen appear only as zero-quantity monitor rows. The issue test asserts exact severity/message/item/location/blocking content and recomputed issue fingerprints. The supply-component test proves the accepted contract fields are exact and an extra uncontracted field is rejected before fingerprinting.

- [ ] **Step 2: Run exact RED**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_red_yellow_create_blocked_versions_green_above_remain_monitor_rows',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_reevaluation_reuses_logical_chain_and_increments_version',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_recommendation_predecessor_and_supersession_links_are_bidirectional',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_active_confirmed_graph_creates_adjustment_required_not_second_actionable_version',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_terminal_chain_starts_next_cycle_with_new_logical_identity',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_same_authority_inputs_produce_deterministic_ids_and_fingerprint',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_logical_identity_uses_canonical_json_for_adversarial_identifiers',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_immutable_record_field_sets_and_nested_fingerprints_are_exact',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_types_payloads_creation_versions_and_folds_are_exact',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_illegal_creation_and_status_transitions',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_issue_records_persist_full_gate_context',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_supply_components_use_only_authoritative_contract_fields'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-builder-red -p no:cacheprovider
```

Expected RED: 12 selected, 0 passed, 12 failed because the builder, exact schemas, event/issue contracts, canonical identity, and fold helpers do not exist. Record actual counts.

- [ ] **Step 3: Define every immutable outer and nested field set exactly once**

```python
EVALUATION_SUMMARY_FIELDS = (
    "RedCount", "YellowCount", "GreenCount", "AboveGreenCount",
    "BlockedRecommendationCount", "AdjustmentRequiredCount", "IssueCount",
)
DEMAND_COMPONENT_FIELDS = (
    "DemandID", "DemandType", "DemandQty", "DemandDueAt", "IsQualifiedSpike", "Uom",
)
SUPPLY_COMPONENT_FIELDS = (
    "SupplyID", "SupplyQty", "ExpectedAt", "Status", "Uom",
)
GATE_FIELDS = ("Code", "Message", "BlocksOperationalAction")
ISSUE_RECORD_FIELDS = (
    "IssueID", "EvaluationID", "Code", "Severity", "Message", "ItemID",
    "LocationID", "BlocksOperationalAction", "IssueFingerprint",
)
ISSUE_SEVERITIES = frozenset({"Blocking", "Warning", "Information"})
EVALUATION_RUN_FIELDS = (
    "EvaluationID", "EvaluationRequestID", "EvaluationAt", "RecordedAt", "RecordedBy",
    "EvaluationMode", "RuntimePlanningInputPackageID",
    "RuntimePlanningInputPackageVersion", "RuntimeSnapshotID",
    "OperatingModelConfigurationID", "OperatingModelFingerprint",
    "DDMRPConfigurationID", "AuthoritySignature", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "Summary", "Issues", "OperationalActionAllowed", "EvaluationFingerprint",
)
EVALUATION_ROW_FIELDS = (
    "EvaluationRowID", "EvaluationID", "EvaluationAt", "RowKey", "ItemID", "LocationID", "Uom",
    "BufferProfileID", "DLTMinutes", "QualifiedOnHandQty", "PhysicalOnHandQty",
    "AuthorityAllocatedQty", "AuthorityAvailableQty", "QualityState",
    "QualifiedOpenSupplyQty", "QualifiedDemandQty", "NetFlowPosition", "TopOfRed",
    "TopOfYellow", "TopOfGreen", "PlanningStatus", "ExecutionStatus",
    "SuggestedReplenishmentQty", "RecommendedAction", "StandardTargetReceiptAt",
    "TargetStatusCode", "RecommendationID", "DemandComponents", "SupplyComponents",
    "GateCodes", "OperationalActionAllowed", "AuthoritySignatureFingerprint",
    "EvaluationRowFingerprint",
)
REPLENISHMENT_CHAIN_FIELDS = (
    "LogicalReplenishmentID", "ItemID", "LocationID", "CycleNumber",
    "OpenedAt", "OpenedByEvaluationID", "InitialStatus", "IdentityFingerprint",
    "TraceID", "ChainFingerprint",
)
RECOMMENDATION_FIELDS = (
    "RecommendationID", "LogicalReplenishmentID", "RecommendationVersion",
    "EvaluationID", "EvaluationRowID", "ItemID", "LocationID", "Uom",
    "PlanningStatus", "ExecutionStatus", "SuggestedReplenishmentQty",
    "StandardTargetReceiptAt", "AdviceType", "InitialStatus", "GateCodes",
    "PredecessorRecommendationID", "AdjustmentOfRecommendationID", "CreatedAt",
    "CreatedBy", "AuthoritySignature", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "TraceID", "RecommendationFingerprint",
)
EVENT_FIELDS = (
    "EventID", "EventType", "AggregateType", "AggregateID", "AggregateVersion",
    "EvaluationID", "LogicalReplenishmentID", "RecommendationID",
    "RelatedRecommendationID", "StatusBefore", "StatusAfter", "OccurredAt",
    "ActorID", "CausationID", "CorrelationID", "IdempotencyKey", "TraceID",
    "EventPayload", "PayloadFingerprint",
)
REQUEST_RESULT_FIELDS = (
    "EvaluationRequestID", "RequestFingerprint", "RuntimePlanningInputPackageID",
    "EvaluationID", "EvaluationRowIDs", "LogicalReplenishmentIDs",
    "CreatedLogicalReplenishmentIDs", "ReusedLogicalReplenishmentIDs",
    "RecommendationIDs", "EventIDs", "EvaluationPayloadFingerprint",
    "ResponseData", "ResponseFingerprint", "RecordedAt", "RecordedBy",
    "RequestResultFingerprint",
)
RESPONSE_DATA_FIELDS = (
    "Status", "EvaluationID", "RecommendationIDs", "OperationalActionAllowed",
)

EVENT_PAYLOAD_FIELDS_BY_TYPE = {
    "ReplenishmentChainOpened": (
        "CycleNumber", "ItemID", "LocationID", "OpenedByEvaluationID",
    ),
    "ReplenishmentChainActivated": ("DecisionID", "AdviceType", "ActiveGraphID"),
    "ReplenishmentChainAdjustmentRequired": (
        "AdjustmentRecommendationID", "AdjustmentDeltaQty", "ReasonCode",
    ),
    "ReplenishmentChainReleased": ("DecisionID", "Reason"),
    "ReplenishmentChainCancelled": ("DecisionID", "Reason"),
    "ReplenishmentChainCompleted": ("FormalSupplyID",),
    "RecommendationVersionCreated": (
        "RecommendationVersion", "SuggestedReplenishmentQty", "GateCodes",
        "PredecessorRecommendationID", "AdjustmentOfRecommendationID",
    ),
    "RecommendationSuperseded": (
        "SupersededByRecommendationID", "SupersedingEvaluationID",
    ),
    "RecommendationPendingReview": (
        "AdviceType", "AuthoritySignatureFingerprint",
    ),
    "RecommendationConfirmed": ("DecisionID", "AdviceType", "Reason"),
    "RecommendationRejected": ("DecisionID", "Reason"),
    "RecommendationIssued": ("OutputRequestID",),
    "RecommendationOutputFailed": ("OutputRequestID", "FailureCode"),
    "RecommendationERPAccepted": ("ExternalOrderRef", "FormalSupplyID"),
    "RecommendationInExecution": ("FormalSupplyID",),
    "RecommendationAdjustmentRequired": (
        "AdjustmentRecommendationID", "AdjustmentDeltaQty", "ReasonCode",
    ),
    "RecommendationReleased": ("DecisionID", "Reason"),
    "RecommendationCancelled": ("DecisionID", "Reason"),
    "RecommendationCompleted": ("FormalSupplyID", "CompletedQty"),
}
EVENT_AGGREGATE_TYPE_BY_EVENT = {
    **{
        event_type: "ReplenishmentChain"
        for event_type in EVENT_PAYLOAD_FIELDS_BY_TYPE
        if event_type.startswith("ReplenishmentChain")
    },
    **{
        event_type: "Recommendation"
        for event_type in EVENT_PAYLOAD_FIELDS_BY_TYPE
        if event_type.startswith("Recommendation")
    },
}
EVENT_TRANSITION_BY_TYPE = {
    "ReplenishmentChainActivated": (frozenset({"Open"}), "ActiveGraph"),
    "ReplenishmentChainAdjustmentRequired": (
        frozenset({"Open", "ActiveGraph"}), "AdjustmentRequired",
    ),
    "ReplenishmentChainReleased": (
        frozenset({"Open", "ActiveGraph", "AdjustmentRequired"}), "Released",
    ),
    "ReplenishmentChainCancelled": (
        frozenset({"Open", "ActiveGraph", "AdjustmentRequired"}), "Cancelled",
    ),
    "ReplenishmentChainCompleted": (
        frozenset({"Open", "ActiveGraph", "AdjustmentRequired"}), "Completed",
    ),
    "RecommendationSuperseded": (
        frozenset({"Blocked", "PendingReview", "AdjustmentRequired"}), "Superseded",
    ),
    "RecommendationPendingReview": (frozenset({"Blocked"}), "PendingReview"),
    "RecommendationConfirmed": (frozenset({"PendingReview"}), "Confirmed"),
    "RecommendationRejected": (frozenset({"PendingReview"}), "Rejected"),
    "RecommendationIssued": (
        frozenset({"Confirmed", "OutputFailed"}), "Issued",
    ),
    "RecommendationOutputFailed": (frozenset({"Issued"}), "OutputFailed"),
    "RecommendationERPAccepted": (frozenset({"Issued"}), "ERPAccepted"),
    "RecommendationInExecution": (frozenset({"ERPAccepted"}), "InExecution"),
    "RecommendationAdjustmentRequired": (
        frozenset({"Confirmed", "Issued", "OutputFailed", "ERPAccepted", "InExecution"}),
        "AdjustmentRequired",
    ),
    "RecommendationReleased": (
        frozenset({"Confirmed", "AdjustmentRequired"}), "Released",
    ),
    "RecommendationCancelled": (
        frozenset({"Confirmed", "Issued", "OutputFailed", "ERPAccepted", "InExecution", "AdjustmentRequired"}),
        "Cancelled",
    ),
    "RecommendationCompleted": (frozenset({"InExecution"}), "Completed"),
}
```

`AuthoritySignature` must have exactly Task 3's key set. `Summary`, demand/supply components, gates, issues, `ResponseData`, and each event type's payload must have exactly their named allowlists. `OpenSupplySignal` maps only `SupplyID`, `SupplyQty`, `ExpectedAt`, `Status`, and `UnitOfMeasure -> Uom`; it has no authoritative source-type field, so no such key exists in the NOW component schema. Reject missing or extra keys before fingerprinting. No record contains `Payload`, a package/config body, evidence refs, raw authority rows, or a mutable nested object borrowed from a caller.

- [ ] **Step 4: Define fingerprints, canonical IDs, and the write set**

```python
def canonical_stable_id(prefix: str, identity: Mapping[str, object]) -> str:
    digest = canonical_fingerprint(dict(identity)).removeprefix("sha256:")
    return f"{prefix}-{digest[:20]}"


@dataclass(frozen=True, slots=True)
class DdmrpEvaluationWriteSet:
    evaluation_request_id: str
    request_fingerprint: str
    payload_fingerprint: str
    evaluation_run: dict[str, object]
    evaluation_rows: tuple[dict[str, object], ...]
    chain_records: tuple[dict[str, object], ...]
    recommendation_versions: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]
    request_result: dict[str, object]
```

Construct IDs only from these canonical objects:

```python
request_identity = {
    "EvaluationRequestID": evaluation_request_id,
    "RuntimePlanningInputPackageID": authority_signature.runtime_package_id,
}
evaluation_identity = {
    "AuthoritySignatureFingerprint": authority_signature.signature_fingerprint,
    "EvaluationAt": runtime_result["EvaluatedAt"],
}
chain_identity = {
    "ItemID": item_id,
    "LocationID": location_id,
    "CycleNumber": cycle_number,
}
recommendation_identity = {
    "LogicalReplenishmentID": logical_replenishment_id,
    "RecommendationVersion": recommendation_version,
}
issue_identity = {
    "EvaluationID": evaluation_id,
    "Code": gate.code,
    "ItemID": None,
    "LocationID": None,
}
event_identity = {
    "AggregateType": aggregate_type,
    "AggregateID": aggregate_id,
    "AggregateVersion": aggregate_version,
    "EventType": event_type,
}
```

Use prefixes `DDE`, `DER`, `DRL`, `DDR`, `DRI`, and `DRE` for evaluation, row, chain, recommendation, issue, and event IDs. `RowKey` is canonical JSON for `{ItemID, LocationID}`. Every record fingerprint is `canonical_fingerprint` over its exact fields excluding only its own `*Fingerprint` field. Event `PayloadFingerprint` covers the exact `EventPayload`. Issues are immutable nested records in `EvaluationRun.Issues`: one sorted record per distinct gate code, `Severity="Blocking"` when `BlocksOperationalAction=True` (otherwise `Warning`), package-wide `ItemID=None` / `LocationID=None`, exact gate message, and no parallel code-only list. `Summary.IssueCount == len(Issues)`.

The write-set `payload_fingerprint` covers sorted `EvaluationRun` (including exact issue records), `EvaluationRows`, newly created `ChainRecords`, `RecommendationVersions`, and `Events`; it deliberately excludes `request_result` to avoid a cycle. `LogicalReplenishmentIDs` is the sorted union of disjoint sorted `CreatedLogicalReplenishmentIDs` and `ReusedLogicalReplenishmentIDs`; only the created subset appears in `ChainRecords`. `RequestResultFingerprint` covers all request-result fields except itself, and `ResponseFingerprint` covers exact `ResponseData`. `EvaluationPayloadFingerprint` in the result equals the write-set fingerprint.

- [ ] **Step 5: Implement the exact status fold and chain selection**

```python
RECOMMENDATION_ACTIVE_STATUSES = frozenset({
    "Blocked", "PendingReview", "Confirmed", "AdjustmentRequired", "Issued",
    "OutputFailed", "ERPAccepted", "InExecution",
})
RECOMMENDATION_TERMINAL_STATUSES = frozenset({
    "Rejected", "Superseded", "Released", "Cancelled", "Completed",
})
CHAIN_ACTIVE_STATUSES = frozenset({"Open", "ActiveGraph", "AdjustmentRequired"})
CHAIN_TERMINAL_STATUSES = frozenset({"Released", "Cancelled", "Completed"})


def _require_exact_fields(
    value: Mapping[str, object],
    fields: tuple[str, ...],
    *,
    context: str,
) -> None:
    actual = frozenset(value)
    expected = frozenset(fields)
    if actual != expected:
        raise DdmrpReplenishmentConflict(
            f"{context} fields differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _validate_event_contract(event: Mapping[str, object]) -> None:
    _require_exact_fields(event, EVENT_FIELDS, context="DDMRP event")
    event_type = str(event["EventType"])
    payload_fields = EVENT_PAYLOAD_FIELDS_BY_TYPE.get(event_type)
    if payload_fields is None:
        raise DdmrpReplenishmentConflict(f"Unsupported DDMRP event type: {event_type}")
    if event["AggregateType"] != EVENT_AGGREGATE_TYPE_BY_EVENT[event_type]:
        raise DdmrpReplenishmentConflict("DDMRP event aggregate type mismatch.")
    payload = event["EventPayload"]
    if not isinstance(payload, Mapping):
        raise DdmrpReplenishmentConflict("DDMRP event payload must be a mapping.")
    _require_exact_fields(payload, payload_fields, context=f"{event_type} payload")
    if event["PayloadFingerprint"] != canonical_fingerprint(dict(payload)):
        raise DdmrpReplenishmentConflict("DDMRP event payload fingerprint mismatch.")
    expected_id = canonical_stable_id(
        "DRE",
        {
            "AggregateType": event["AggregateType"],
            "AggregateID": event["AggregateID"],
            "AggregateVersion": event["AggregateVersion"],
            "EventType": event_type,
        },
    )
    if event["EventID"] != expected_id:
        raise DdmrpReplenishmentConflict("DDMRP event canonical ID mismatch.")


def _fold_status(
    *,
    aggregate_type: str,
    aggregate_id: str,
    creation_event_type: str,
    creation_status: str,
    events: Iterable[Mapping[str, object]],
    terminal_statuses: frozenset[str],
) -> str:
    selected = sorted(
        (
            event for event in events
            if event.get("AggregateType") == aggregate_type
            and event.get("AggregateID") == aggregate_id
        ),
        key=lambda event: (int(event["AggregateVersion"]), str(event["EventID"])),
    )
    if not selected:
        raise DdmrpReplenishmentConflict("DDMRP aggregate has no creation event.")
    current: str | None = None
    for expected_version, event in enumerate(selected, start=1):
        _validate_event_contract(event)
        if event["AggregateVersion"] != expected_version:
            raise DdmrpReplenishmentConflict(
                "DDMRP aggregate versions must be unique contiguous integers starting at 1."
            )
        if event["StatusBefore"] != current:
            raise DdmrpReplenishmentConflict("DDMRP event StatusBefore does not match fold.")
        event_type = str(event["EventType"])
        status_after = str(event["StatusAfter"])
        if expected_version == 1:
            if event_type != creation_event_type or status_after != creation_status:
                raise DdmrpReplenishmentConflict(
                    "DDMRP aggregate must start with its exact version-1 creation event."
                )
        else:
            if current in terminal_statuses:
                raise DdmrpReplenishmentConflict("Terminal DDMRP aggregate has a later event.")
            transition = EVENT_TRANSITION_BY_TYPE.get(event_type)
            if transition is None:
                raise DdmrpReplenishmentConflict("Creation event cannot appear after version 1.")
            allowed_before, required_after = transition
            if current not in allowed_before or status_after != required_after:
                raise DdmrpReplenishmentConflict("Illegal DDMRP event status transition.")
        current = status_after
    assert current is not None
    return current


def fold_recommendation_status(
    recommendation: Mapping[str, object],
    events: Iterable[Mapping[str, object]],
) -> str:
    return _fold_status(
        aggregate_type="Recommendation",
        aggregate_id=str(recommendation["RecommendationID"]),
        creation_event_type="RecommendationVersionCreated",
        creation_status=str(recommendation["InitialStatus"]),
        events=events,
        terminal_statuses=RECOMMENDATION_TERMINAL_STATUSES,
    )


def fold_chain_status(
    chain: Mapping[str, object],
    events: Iterable[Mapping[str, object]],
) -> str:
    return _fold_status(
        aggregate_type="ReplenishmentChain",
        aggregate_id=str(chain["LogicalReplenishmentID"]),
        creation_event_type="ReplenishmentChainOpened",
        creation_status="Open",
        events=events,
        terminal_statuses=CHAIN_TERMINAL_STATUSES,
    )
```

Before sorting, reject non-integer/boolean/zero/negative aggregate versions and duplicate `(AggregateType, AggregateID, AggregateVersion)` values so `int(...)` cannot normalize malformed data. The fold also verifies creation payload values against the immutable chain/recommendation record and verifies every transition payload's referenced IDs against the corresponding immutable records. For latest-version selection, reject duplicate recommendation versions, predecessor gaps, multiple successors, a missing reverse `RecommendationSuperseded` event, multiple non-terminal chains for one item/location, an active graph attached to a terminal chain, or a graph whose mapping key differs from `LogicalReplenishmentID`. NOW may emit only `ReplenishmentChainOpened`, `RecommendationVersionCreated`, and `RecommendationSuperseded`; the other enumerated types are validation contracts for persisted lifecycle compatibility and may be emitted only by the gated task that owns that transition.

- [ ] **Step 6: Implement the exact builder**

```text
def prepare_ddmrp_evaluation(
    *,
    evaluation_request_id: str,
    recorded_at: datetime,
    actor_id: str,
    runtime_result: Mapping[str, object],
    authority_signature: DdmrpAuthoritySignature,
    gates: tuple[DdmrpGate, ...],
    existing_chains: Mapping[str, Mapping[str, object]],
    existing_recommendations: Mapping[str, Mapping[str, object]],
    existing_events: tuple[Mapping[str, object], ...],
    active_replenishment_graphs: Mapping[str, Mapping[str, object]],
) -> DdmrpEvaluationWriteSet
```

Require timezone-aware `recorded_at`, non-empty actor/request ID, and exact runtime line/component schemas. Require `runtime_result["EvaluatedAt"] == authority_signature.runtime_snapshot_at`, require that value to be canonical UTC text ending `+00:00`, and write that exact string to the run and every row `EvaluationAt`; never copy the raw package timestamp. Build one immutable issue record for each sorted distinct gate and persist those records in the run as specified above.

Reuse the sole non-terminal chain; otherwise use `max(prior CycleNumber)+1`. `chain_records` contains only newly opened chains. Emit `ReplenishmentChainOpened` at aggregate version 1 for each new chain. Put every referenced chain in `LogicalReplenishmentIDs`, partition it into exactly one of `CreatedLogicalReplenishmentIDs` or `ReusedLogicalReplenishmentIDs`, and assert the two partitions are disjoint and their sorted union is exact. Increment the recommendation version, name its predecessor, emit `RecommendationVersionCreated` at version 1 for the new recommendation aggregate, and emit `RecommendationSuperseded` at `max(existing predecessor AggregateVersion)+1` on the predecessor aggregate without mutating either immutable recommendation. Populate every event field and its exact payload; `CausationID` is the evaluation request ID and `CorrelationID` is the evaluation ID.

If the active-graph registry contains the chain, create only `InitialStatus="AdjustmentRequired"` with `AdjustmentOfRecommendationID`; otherwise NOW Red/Yellow is `Blocked`. Freeze deep copies of the complete signature on the run and each recommendation. Produce one immutable request result with persisted `ResponseData.Status="Created"` and exact created/reused membership. Never create a recommendation for Green/AboveGreen. Run `_validate_event_contract`, both folds, exact issue validation, and request-result partition validation before returning the write set.

- [ ] **Step 7: Run matching GREEN and commit**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_red_yellow_create_blocked_versions_green_above_remain_monitor_rows',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_reevaluation_reuses_logical_chain_and_increments_version',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_recommendation_predecessor_and_supersession_links_are_bidirectional',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_active_confirmed_graph_creates_adjustment_required_not_second_actionable_version',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_terminal_chain_starts_next_cycle_with_new_logical_identity',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_same_authority_inputs_produce_deterministic_ids_and_fingerprint',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_logical_identity_uses_canonical_json_for_adversarial_identifiers',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_immutable_record_field_sets_and_nested_fingerprints_are_exact',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_types_payloads_creation_versions_and_folds_are_exact',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_illegal_creation_and_status_transitions',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_issue_records_persist_full_gate_context',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_supply_components_use_only_authoritative_contract_fields'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-builder-green -p no:cacheprovider
```

Expected GREEN: 12 selected, 12 passed, 0 failed. Record the count, then:

```powershell
git add sdbr/ddmrp_replenishment.py tests/test_ddmrp_replenishment.py
git commit -m "feat: build immutable DDMRP evaluations"
```

---

### Task 5: Immutable Request-Result Replay, Orphan Rejection, Staging, And Apply

**Files:**
- Modify: `sdbr/ddmrp_replenishment.py`
- Modify: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Produces `lookup_ddmrp_evaluation_request_result(...)`, `DdmrpEvaluationStagedState`, `stage_ddmrp_evaluation(...)`, and `apply_staged_ddmrp_evaluation(...)`.
- Replaces the prior bare `processed_ddmrp_action_keys` set with `ddmrp_evaluation_request_results: dict[str, dict[str, object]]`. One immutable result record is both the processed marker and replay proof.

- [ ] **Step 1: Write every replay/atomicity RED test**

```text
test_be_ddmrp_007_exact_evaluation_replay_validates_result_graph_and_is_duplicate
test_be_ddmrp_007_request_id_reuse_with_changed_request_fingerprint_conflicts
test_be_ddmrp_007_event_or_child_drift_fails_closed
test_be_ddmrp_007_failure_after_staging_leaves_every_live_ledger_unchanged
test_be_ddmrp_007_duplicate_open_chain_preflight_leaves_no_partial_records
test_be_ddmrp_007_duplicate_ids_inside_write_set_fail_before_any_insert
test_be_ddmrp_007_orphan_children_without_request_result_are_never_adopted
test_be_ddmrp_007_request_result_with_missing_or_extra_child_fails_closed
test_be_ddmrp_007_reused_chain_membership_partitions_created_and_reused_ids
```

- [ ] **Step 2: Run exact RED**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_exact_evaluation_replay_validates_result_graph_and_is_duplicate',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_request_id_reuse_with_changed_request_fingerprint_conflicts',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_or_child_drift_fails_closed',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_failure_after_staging_leaves_every_live_ledger_unchanged',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_duplicate_open_chain_preflight_leaves_no_partial_records',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_duplicate_ids_inside_write_set_fail_before_any_insert',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_orphan_children_without_request_result_are_never_adopted',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_request_result_with_missing_or_extra_child_fails_closed',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_reused_chain_membership_partitions_created_and_reused_ids'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-apply-red -p no:cacheprovider
```

Expected RED: 9 selected, 0 passed, 9 failed because lookup/staging/orphan and created/reused membership contracts are absent. Record actual counts.

- [ ] **Step 3: Implement immutable lookup before any rebuild**

```python
def lookup_ddmrp_evaluation_request_result(
    *,
    evaluation_request_id: str,
    request_fingerprint: str,
    request_results: Mapping[str, Mapping[str, object]],
    evaluation_runs: Mapping[str, Mapping[str, object]],
    evaluation_rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: tuple[Mapping[str, object], ...],
) -> dict[str, object] | None:
    persisted = request_results.get(evaluation_request_id)
    if persisted is None:
        return None
    if persisted.get("EvaluationRequestID") != evaluation_request_id:
        raise DdmrpReplenishmentConflict("EVALUATION_REQUEST_RESULT_KEY_MISMATCH")
    _require_exact_fields(
        persisted,
        REQUEST_RESULT_FIELDS,
        context="DDMRP evaluation request result",
    )
    fingerprint_source = {
        key: deepcopy(persisted[key])
        for key in REQUEST_RESULT_FIELDS
        if key != "RequestResultFingerprint"
    }
    if persisted["RequestResultFingerprint"] != canonical_fingerprint(fingerprint_source):
        raise DdmrpReplenishmentConflict("EVALUATION_REQUEST_RESULT_DRIFT")
    if persisted["RequestFingerprint"] != request_fingerprint:
        raise DdmrpReplenishmentConflict("EVALUATION_REQUEST_ID_REUSED")
    _validate_persisted_evaluation_result_graph(
        result=persisted,
        evaluation_runs=evaluation_runs,
        evaluation_rows=evaluation_rows,
        chains=chains,
        recommendations=recommendations,
        events=events,
    )
    response = deepcopy(persisted["ResponseData"])
    response["Status"] = "Duplicate"
    return response
```

Implement the function body in this order: get only `request_results.get(evaluation_request_id)`; return `None` immediately when absent; require mapping key equals `EvaluationRequestID`; require exact `REQUEST_RESULT_FIELDS`; recompute `RequestResultFingerprint`; compare `request_fingerprint` and raise `DdmrpReplenishmentConflict("EVALUATION_REQUEST_ID_REUSED")` on changed reuse; then call `_validate_persisted_evaluation_result_graph(...)`. No package/configuration/ledger-authority callback is accepted by this helper, so replay cannot accidentally consult current authority.

`_validate_persisted_evaluation_result_graph(...)` must prove:

- the exact evaluation, row, recommendation, and event ID sets equal the result record lists, with no missing or extra child;
- `CreatedLogicalReplenishmentIDs` and `ReusedLogicalReplenishmentIDs` are sorted, unique, disjoint, and their sorted union exactly equals `LogicalReplenishmentIDs`;
- every created chain exists, was opened by this evaluation, and is included in reconstructed `ChainRecords`; every reused chain exists, predates this evaluation, is referenced by a new recommendation, and is excluded from reconstructed `ChainRecords`;
- every mapping key equals the child's canonical ID and every child/nested fingerprint recomputes;
- each child points back to the result's evaluation/request/chain as applicable;
- the write-set payload reconstructed from persisted children equals `EvaluationPayloadFingerprint`;
- exact `ResponseData` and `ResponseFingerprint` match those IDs and `OperationalActionAllowed=False`.

The validator additionally runs exact issue validation, event payload validation, recommendation/chain folds, bidirectional predecessor/supersession checks, and verifies that no referenced chain is orphaned from its item/location/version graph. Only after all checks return a deep-copied response with `Status="Duplicate"`. Persisted `ResponseData` remains `Status="Created"`; replay never rewrites history. Any drift is a conflict, not a repair.

- [ ] **Step 4: Add the complete staging contract**

```python
@dataclass(frozen=True, slots=True)
class DdmrpEvaluationStagedState:
    evaluation_runs: dict[str, dict[str, object]]
    evaluation_rows: dict[str, dict[str, object]]
    chains: dict[str, dict[str, object]]
    recommendations: dict[str, dict[str, object]]
    events: tuple[dict[str, object], ...]
    request_results: dict[str, dict[str, object]]
    result_status: Literal["Created", "Duplicate"]
    response_data: dict[str, object]
```

`stage_ddmrp_evaluation(...)` accepts the five existing immutable collections plus `request_results`. It deep-copies all six. Before inspecting persisted state, `_assert_unique_write_set_ids(...)` rejects duplicate row, chain, recommendation, or event IDs even when duplicate content is equal; `_assert_write_set_fingerprints(...)` validates every exact field/nested field/record fingerprint, the child payload fingerprint, request result, and response.

Next call `lookup_ddmrp_evaluation_request_result(...)` against the copies. Exact replay returns a `Duplicate` staged state unchanged. Changed reuse conflicts. For an unprocessed request, any pre-existing target evaluation, row, recommendation, event, or **created-chain** ID, equal or different, is `ORPHAN_DDMRP_EVALUATION_CHILD` and fails closed; no `setdefault` adoption is allowed. A `ReusedLogicalReplenishmentID` is the sole exception: it must already exist, must be the exact non-terminal chain selected by the builder, and must pass its immutable fingerprint/fold/back-reference checks. A reused chain never appears in `write_set.chain_records` and is never reinserted. Validate chain uniqueness/folds against the combined prospective copies, insert only new children/events, and insert the immutable request result last. There is no independent processed key that can drift away from its result.

- [ ] **Step 5: Apply six live collections with rollback**

`apply_staged_ddmrp_evaluation(...)` accepts the staged state and mutable runs, rows, chains, recommendations, events, and request-results collections. Snapshot all six first, then `clear/update` or `clear/extend` from staged deep copies. A single `except BaseException` restores all six before re-raising. No validation or fingerprinting occurs after replacement starts. Return a deep copy of `(result_status, response_data)`.

- [ ] **Step 6: Run matching GREEN and commit**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_exact_evaluation_replay_validates_result_graph_and_is_duplicate',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_request_id_reuse_with_changed_request_fingerprint_conflicts',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_or_child_drift_fails_closed',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_failure_after_staging_leaves_every_live_ledger_unchanged',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_duplicate_open_chain_preflight_leaves_no_partial_records',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_duplicate_ids_inside_write_set_fail_before_any_insert',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_orphan_children_without_request_result_are_never_adopted',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_request_result_with_missing_or_extra_child_fails_closed',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_reused_chain_membership_partitions_created_and_reused_ids'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-apply-green -p no:cacheprovider
```

Expected GREEN: 9 selected, 9 passed, 0 failed. Record the count, then:

```powershell
git add sdbr/ddmrp_replenishment.py tests/test_ddmrp_replenishment.py
git commit -m "feat: apply DDMRP evaluations atomically"
```

---

### Task 6: Persist The Read-Only Evaluation Ledgers

**Files:**
- Modify: `sdbr/state_store.py`
- Modify: `tests/test_state_store.py`

**Interfaces:**
- Adds seven state collections without changing the relational schema version.

- [ ] **Step 1: Add traceability and failing round-trip tests**

Extend the test module docstring to include `BE-DDMRP-007`. Add `test_be_ddmrp_007_sqlite_round_trip_clear_health_and_complete_rollback` covering:

```python
ddmrp_evaluation_runs
ddmrp_evaluation_rows
ddmrp_replenishment_chains
ddmrp_replenishment_recommendations
ddmrp_replenishment_events
ddmrp_active_replenishment_graphs
ddmrp_evaluation_request_results
```

Verify save failure restores all seven and the revision.

- [ ] **Step 2: Run RED**

```powershell
pytest tests/test_state_store.py::test_be_ddmrp_007_sqlite_round_trip_clear_health_and_complete_rollback -q --basetemp .tmp/pytest-ddmrp-store-red -p no:cacheprovider
```

Expected RED: 1 selected, 0 passed, 1 failed because the seven DDMRP store fields/boundaries do not exist. Record the count.

- [ ] **Step 3: Add exact store fields and boundaries**

Add to `WorkbenchStateStore`:

```python
ddmrp_evaluation_runs: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_evaluation_rows: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_chains: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_recommendations: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_events: list[dict[str, object]] = field(default_factory=list)
ddmrp_active_replenishment_graphs: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_evaluation_request_results: dict[str, dict[str, object]] = field(default_factory=dict)
```

Add all seven to `_state_payloads`, `_apply_payloads`, `_clear`, `_state_counts`, complete in-memory snapshots, and restore. Validate every loaded request-result mapping key against `EvaluationRequestID`; malformed persisted identity fails load instead of being normalized. Keep `SCHEMA_VERSION = 1` because state keys remain JSON rows and absent keys load empty.

- [ ] **Step 4: Run GREEN and commit**

```powershell
pytest tests/test_state_store.py::test_be_ddmrp_007_sqlite_round_trip_clear_health_and_complete_rollback -q --basetemp .tmp/pytest-ddmrp-store-green -p no:cacheprovider
pytest tests/test_state_store.py -q -k "complete_state" --basetemp .tmp/pytest-ddmrp-store-regression -p no:cacheprovider
git add sdbr/state_store.py tests/test_state_store.py
git commit -m "feat: persist DDMRP evaluation history"
```

Expected GREEN: the exact focused selection reports 1 passed; the separate complete-state regression reports a non-zero passing count. Record both.

---

### Task 7: Safe Workbench Projection With Exact Nested Allowlists

**Files:**
- Create: `sdbr/ddmrp_replenishment_view.py`
- Create: `tests/test_ddmrp_replenishment_view.py`

**Interfaces:**
- Produces `build_ddmrp_replenishment_workbench(...) -> dict[str, object]`.
- Imports the Task 4 field/fold validators; it never passes ledger dictionaries through to the API.

- [ ] **Step 1: Write exact projection tests**

Use module docstring `"""Acceptance evidence for BE-DDMRP-007 and UI-DDMRP-003."""` and add:

```text
test_be_ddmrp_007_view_returns_latest_rows_plus_older_active_or_adjustment_chains
test_be_ddmrp_007_view_exposes_null_target_and_business_gate_codes
test_be_ddmrp_007_view_never_exposes_frozen_payload_or_evidence_rows
test_be_ddmrp_007_view_rejects_duplicate_chain_or_orphan_recommendation
test_be_ddmrp_007_view_is_deterministic_and_deep_copied
test_be_ddmrp_007_view_empty_state_shape_is_stable
test_be_ddmrp_007_view_nested_projection_allowlists_are_exact
```

- [ ] **Step 2: Run exact RED**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_returns_latest_rows_plus_older_active_or_adjustment_chains',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_exposes_null_target_and_business_gate_codes',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_never_exposes_frozen_payload_or_evidence_rows',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_rejects_duplicate_chain_or_orphan_recommendation',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_is_deterministic_and_deep_copied',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_empty_state_shape_is_stable',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_nested_projection_allowlists_are_exact'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-view-red -p no:cacheprovider
```

Expected RED: 7 selected, 0 passed, 7 failed because the view module/allowlists do not exist. Record actual counts.

- [ ] **Step 3: Implement the exact signature**

```text
def build_ddmrp_replenishment_workbench(
    *,
    evaluation_runs: Mapping[str, Mapping[str, object]],
    evaluation_rows: Mapping[str, Mapping[str, object]],
    chains: Mapping[str, Mapping[str, object]],
    recommendations: Mapping[str, Mapping[str, object]],
    events: tuple[Mapping[str, object], ...],
    active_replenishment_graphs: Mapping[str, Mapping[str, object]],
) -> dict[str, object]
```

Validate all Task 4 immutable fields/fingerprints/folds, event payloads, issue records, and created/reused chain memberships before projection. Reject duplicate canonical IDs, mapping-key mismatches, orphan recommendations/events/graphs, multiple current versions, and active graphs on terminal chains. Return a deep copy with exactly these top-level keys:

```python
WORKBENCH_FIELDS = (
    "Evaluation", "Summary", "Rows", "ActiveGraphs", "History", "Issues",
    "Boundary", "TechnicalDetails",
)
EVALUATION_VIEW_FIELDS = (
    "EvaluationID", "EvaluationAt", "RecordedAt", "RuntimePlanningInputPackageID",
    "RuntimePlanningInputPackageVersion", "OperatingModelConfigurationID",
    "DDMRPConfigurationID", "OperationalActionAllowed",
)
SUMMARY_VIEW_FIELDS = (
    "RedCount", "YellowCount", "GreenCount", "AboveGreenCount",
    "BlockedRecommendationCount", "PendingReviewCount",
    "AdjustmentRequiredCount", "ActiveGraphCount",
)
ROW_VIEW_FIELDS = (
    "RowKey", "ItemID", "LocationID", "Uom", "PlanningStatus", "ExecutionStatus",
    "BufferPercent", "QualifiedOnHandQty", "PhysicalOnHandQty",
    "AuthorityAllocatedQty", "AuthorityAvailableQty", "QualifiedOpenSupplyQty",
    "QualifiedDemandQty", "NetFlowPosition", "TopOfRed", "TopOfYellow",
    "TopOfGreen", "SuggestedReplenishmentQty", "StandardTargetReceiptAt",
    "TargetStatusCode", "RecommendedAction", "RecommendationID",
    "RecommendationVersion", "RecommendationStatus", "GateCodes",
    "DemandComponents", "SupplyComponents", "OperationalActionAllowed",
)
ACTIVE_GRAPH_VIEW_FIELDS = (
    "LogicalReplenishmentID", "RecommendationID", "RecommendationVersion",
    "ItemID", "LocationID", "Uom", "GraphStatus", "CandidateStatus",
    "PlannedSupplyQty", "PlanningRunID", "FormalOrderRef",
    "AdjustmentRequired", "LastEventAt",
)
HISTORY_VIEW_FIELDS = (
    "LogicalReplenishmentID", "RecommendationID", "RecommendationVersion",
    "PredecessorRecommendationID", "SupersededByRecommendationID",
    "AdjustmentOfRecommendationID", "InitialStatus", "CurrentStatus",
    "SuggestedReplenishmentQty", "StandardTargetReceiptAt", "EvaluationID",
    "EvaluationAt", "LastEventAt", "Events",
)
HISTORY_EVENT_FIELDS = (
    "EventID", "EventType", "OccurredAt", "ActorID",
    "RelatedRecommendationID", "StatusBefore", "StatusAfter",
)
ISSUE_VIEW_FIELDS = (
    "Severity", "Code", "Message", "ItemID", "LocationID",
    "BlocksOperationalAction",
)
TECHNICAL_DETAILS_FIELDS = (
    "EvaluationID", "EvaluationFingerprint", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "RuntimeSnapshotID", "ParameterAuthorityFingerprint",
    "RecommendationFingerprints",
)
RECOMMENDATION_FINGERPRINT_FIELDS = (
    "RecommendationID", "RecommendationFingerprint",
)
```

`DemandComponents`, `SupplyComponents`, and gate dictionaries use Task 4's exact nested fields. Build `Issues` only by projecting the latest immutable `EvaluationRun.Issues` records through `ISSUE_VIEW_FIELDS`; never synthesize messages/severity from `GateCodes`, and verify each row gate code resolves to exactly one applicable package-wide or item/location issue. `Rows` sort by `(PlanningStatus rank, BufferPercent, ItemID, LocationID)`; `ActiveGraphs` by `(ItemID, LocationID, LogicalReplenishmentID)`; `History` by `(ItemID, LocationID, RecommendationVersion, RecommendationID)`; nested events by `(AggregateVersion, EventID)`; issues by `(Severity, Code, ItemID or "", LocationID or "")`. Empty state returns the same eight top-level keys, `Evaluation=None`, zeroed exact summary, empty lists, the exact boundary, and an empty exact technical object.

The boundary is exactly `Read-only SDBR planning evaluation; no ERP order, inventory authority, or operational reservation write.` No projection may contain `Payload`, `AuthoritySignature`, evidence refs, capacity/material ledger rows, request results, event payloads, or an unallowlisted nested key. IDs/fingerprints appear only in the named business links or `TechnicalDetails`.

- [ ] **Step 4: Run matching GREEN and commit**

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_returns_latest_rows_plus_older_active_or_adjustment_chains',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_exposes_null_target_and_business_gate_codes',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_never_exposes_frozen_payload_or_evidence_rows',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_rejects_duplicate_chain_or_orphan_recommendation',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_is_deterministic_and_deep_copied',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_empty_state_shape_is_stable',
  'tests/test_ddmrp_replenishment_view.py::test_be_ddmrp_007_view_nested_projection_allowlists_are_exact'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-view-green -p no:cacheprovider
```

Expected GREEN: 7 selected, 7 passed, 0 failed. Record the count, then:

```powershell
git add sdbr/ddmrp_replenishment_view.py tests/test_ddmrp_replenishment_view.py
git commit -m "feat: project safe DDMRP workbench rows"
```

---

### Task 8: Strict Server-Built Evaluation API, Snapshot Time, And Replay-First Orchestration

**Files:**
- Modify: `sdbr/api.py` near imports, DDMRP payloads/routes, authorization, `create_app`, and `persist_successful_writes`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces `POST /planner/workbench/ddmrp/evaluations` and `GET /planner/workbench/ddmrp/workbench`.
- Uses `{Endpoint, StatusCode, Data}` and `X-Workbench-Revision` exactly.
- Accepts only request ID and stored package ID; no advice, target, BOM, capacity, material, actor, or timestamp override.

- [ ] **Step 1: Add the strict model and aware-datetime adapter**

Change the Pydantic import and define the model exactly:

```python
from datetime import timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

_AWARE_DATETIME_ADAPTER = TypeAdapter(AwareDatetime)


class DdmrpEvaluationCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    EvaluationRequestID: str = Field(min_length=1)
    RuntimePlanningInputPackageID: str = Field(min_length=1)
```

There are no mutable defaults or client actor/time fields. Extra `AdviceType`, `TargetReceiptAt`, `CapacityRequests`, `MaterialRequests`, package rows, or evidence fields fail FastAPI/Pydantic validation with 422 before route code runs.

- [ ] **Step 2: Write all exact API RED tests and traceability comments**

Add `# BE-DDMRP-007` to each test, add `# UI-DDMRP-003 / BE-DDMRP-007` to the workbench shape test, and add `# BE-DDMRP-007 / BE-OPS-001` to the RBAC test:

```text
test_be_ddmrp_007_evaluation_api_references_stored_validated_package_only
test_be_ddmrp_007_evaluation_api_rejects_raw_authority_fields_with_422
test_be_ddmrp_007_evaluation_api_uses_server_actor_and_server_time
test_be_ddmrp_007_evaluation_api_lost_response_retry_returns_duplicate_after_save
test_be_ddmrp_007_evaluation_api_request_id_reuse_with_different_package_returns_409
test_be_ddmrp_007_evaluation_api_canonicalizes_z_and_offset_snapshot_at_for_signature_evaluation_and_rows
test_be_ddmrp_007_evaluation_api_rejects_naive_or_invalid_snapshot_at
test_be_ddmrp_007_evaluation_api_public_demo_is_read_only
test_be_ddmrp_007_workbench_api_uses_standard_wrapper_and_safe_shape
test_be_ddmrp_007_write_revision_and_save_failure_restore_every_ledger
test_be_ddmrp_007_ddmrp_routes_enforce_viewer_planner_admin_rbac
test_be_ddmrp_007_unrelated_workbench_write_does_not_change_relevant_ledger_identity
```

The lost-response test performs a successful POST, discards that response, proves the store saved once, then repeats the identical body after that mutation and expects `Data.Status == "Duplicate"`, the same IDs/result, and unchanged DDMRP child/request-result counts. It must not reuse a stale `If-Match`; the separate NOW revision test owns stale-revision behavior. The changed-package test reuses the same request ID and expects 409 before any package calculation.

Parameterize the canonical-time test with three equivalent instants: `2026-06-30T01:00:00Z`, `2026-06-30T09:00:00+08:00`, and `2026-06-29T20:00:00-05:00`; all must persist exactly `2026-06-30T01:00:00+00:00` in the signature, evaluation run, every row, IDs, and fingerprints. Parameterize the rejection test with `2026-06-30T01:00:00` and `not-a-timestamp`; both return structured 409 before evaluation construction.

- [ ] **Step 3: Run exact RED**

```powershell
$tests = @(
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_references_stored_validated_package_only',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_rejects_raw_authority_fields_with_422',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_uses_server_actor_and_server_time',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_lost_response_retry_returns_duplicate_after_save',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_request_id_reuse_with_different_package_returns_409',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_canonicalizes_z_and_offset_snapshot_at_for_signature_evaluation_and_rows',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_rejects_naive_or_invalid_snapshot_at',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_public_demo_is_read_only',
  'tests/test_api.py::test_be_ddmrp_007_workbench_api_uses_standard_wrapper_and_safe_shape',
  'tests/test_api.py::test_be_ddmrp_007_write_revision_and_save_failure_restore_every_ledger',
  'tests/test_api.py::test_be_ddmrp_007_ddmrp_routes_enforce_viewer_planner_admin_rbac',
  'tests/test_api.py::test_be_ddmrp_007_unrelated_workbench_write_does_not_change_relevant_ledger_identity'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-api-red -p no:cacheprovider
```

Expected RED: 15 selected, 0 passed, 15 failed because routes/model/bindings and canonical timestamp persistence do not exist (the three valid and two invalid timestamp parameters count as five cases). Record actual counts.

- [ ] **Step 4: Extend authorization and bind all seven NOW ledgers**

Add `/planner/workbench/ddmrp` to the authenticated middleware prefix. In `_planning_run_authorization_error`, a DDMRP GET permits `Viewer`, `Planner`, `Admin`; DDMRP writes permit `Planner`, `Admin`; Worker is denied. Missing identity is 401. Existing Planning Run/reservation role behavior is unchanged. Bind runs, rows, chains, recommendations, events, active graphs, and evaluation request results from `active_store` in `create_app`.

- [ ] **Step 5: Perform immutable request-result lookup before authority rebuild**

The POST route starts with only the strict body and persisted DDMRP ledgers:

```python
request_fingerprint = canonical_fingerprint(
    {
        "EvaluationRequestID": payload.EvaluationRequestID,
        "RuntimePlanningInputPackageID": payload.RuntimePlanningInputPackageID,
    }
)
replayed = lookup_ddmrp_evaluation_request_result(
    evaluation_request_id=payload.EvaluationRequestID,
    request_fingerprint=request_fingerprint,
    request_results=ddmrp_evaluation_request_results,
    evaluation_runs=ddmrp_evaluation_runs,
    evaluation_rows=ddmrp_evaluation_rows,
    chains=ddmrp_replenishment_chains,
    recommendations=ddmrp_replenishment_recommendations,
    events=tuple(ddmrp_replenishment_events),
)
if replayed is not None:
    return {
        "Endpoint": endpoint,
        "StatusCode": 200,
        "Data": {
            **replayed,
            "Workbench": build_ddmrp_replenishment_workbench(
                evaluation_runs=ddmrp_evaluation_runs,
                evaluation_rows=ddmrp_evaluation_rows,
                chains=ddmrp_replenishment_chains,
                recommendations=ddmrp_replenishment_recommendations,
                events=tuple(ddmrp_replenishment_events),
                active_replenishment_graphs=ddmrp_active_replenishment_graphs,
            ),
        },
    }
```

This branch does not look up/re-hash the runtime package, configuration, relevant planning ledger, or server time. Persisted graph/result validation occurs inside lookup. Changed request reuse conflicts. This ordering is mandatory for lost-response correctness.

- [ ] **Step 6: Parse authoritative `SnapshotAt` once and show every route argument**

For an unprocessed request, look up `payload.RuntimePlanningInputPackageID` in `ddsop_runtime_planning_input_packages`, require stored `ProcessingStatus == "Accepted"`, resolve `package_record["OperatingModelConfigurationID"]` in `operating_model_configurations`, and reject missing references with 404. Do not process request-body rows.

Parse the stored nested timestamp exactly once and normalize that parsed object once:

```python
package_payload = package_record.get("Payload")
runtime_snapshot = (
    package_payload.get("RuntimeEvidenceSnapshot")
    if isinstance(package_payload, Mapping)
    else None
)
try:
    parsed_snapshot_at = _AWARE_DATETIME_ADAPTER.validate_python(
        runtime_snapshot["SnapshotAt"]
    )
except (KeyError, TypeError, ValidationError) as error:
    raise DdmrpReplenishmentConflict(
        "RUNTIME_SNAPSHOT_AT_INVALID: stored SnapshotAt must be timezone-aware."
    ) from error
evaluated_at = parsed_snapshot_at.astimezone(timezone.utc)
canonical_snapshot_at = evaluated_at.isoformat()
if not canonical_snapshot_at.endswith("+00:00"):
    raise DdmrpReplenishmentConflict("RUNTIME_SNAPSHOT_AT_NOT_CANONICAL_UTC")
```

Then call every domain interface with these exact arguments and sources:

```python
scope_item_locations = ddmrp_evaluation_scope_item_locations(
    package_record=package_record,
    operating_model_configuration=operating_model_configuration,
)
relevant_ledger = build_relevant_planning_ledger_identity(
    scope_item_locations=scope_item_locations,
    planning_demand_commitments=planning_demand_commitments,
    planning_reservation_batches=planning_reservation_batches,
    ccr_capacity_reservations=ccr_capacity_reservations,
    material_planning_allocations=material_planning_allocations,
    active_replenishment_graphs=ddmrp_active_replenishment_graphs,
)
runtime_result = evaluate_ddmrp_runtime_signals_from_package(
    package_record,
    operating_model_configuration,
    evaluated_at=evaluated_at,
)
authority_signature, gates = build_read_only_authority_signature(
    package_record=package_record,
    operating_model_configuration=operating_model_configuration,
    relevant_planning_ledger=relevant_ledger,
    evaluated_at=evaluated_at,
)
recorded_at = server_utc_now()
actor_id = _effective_actor_id(request, "local-planner")
write_set = prepare_ddmrp_evaluation(
    evaluation_request_id=payload.EvaluationRequestID,
    recorded_at=recorded_at,
    actor_id=actor_id,
    runtime_result=runtime_result,
    authority_signature=authority_signature,
    gates=gates,
    existing_chains=ddmrp_replenishment_chains,
    existing_recommendations=ddmrp_replenishment_recommendations,
    existing_events=tuple(ddmrp_replenishment_events),
    active_replenishment_graphs=ddmrp_active_replenishment_graphs,
)
staged = stage_ddmrp_evaluation(
    write_set=write_set,
    evaluation_runs=ddmrp_evaluation_runs,
    evaluation_rows=ddmrp_evaluation_rows,
    chains=ddmrp_replenishment_chains,
    recommendations=ddmrp_replenishment_recommendations,
    events=tuple(ddmrp_replenishment_events),
    request_results=ddmrp_evaluation_request_results,
)
status, response_data = apply_staged_ddmrp_evaluation(
    staged=staged,
    evaluation_runs=ddmrp_evaluation_runs,
    evaluation_rows=ddmrp_evaluation_rows,
    chains=ddmrp_replenishment_chains,
    recommendations=ddmrp_replenishment_recommendations,
    events=ddmrp_replenishment_events,
    request_results=ddmrp_evaluation_request_results,
)
```

Assert `runtime_result["EvaluatedAt"]`, `authority_signature.runtime_snapshot_at`, evaluation `EvaluationAt`, and every row `EvaluationAt` all equal the one `canonical_snapshot_at` value; `EvaluationAt` is part of each row's exact schema and fingerprint. Only `RecordedAt` uses server time. The route never uses server time for overdue/today/spike/open-supply qualification. Let middleware own admission, save, and complete state rollback.

- [ ] **Step 7: Return exact wrappers and errors**

POST `Data` is exactly `Status`, `EvaluationID`, `RecommendationIDs`, `OperationalActionAllowed=False`, and `Workbench`. GET is exactly:

```python
{
    "Endpoint": "/planner/workbench/ddmrp/workbench",
    "StatusCode": 200,
    "Data": build_ddmrp_replenishment_workbench(
        evaluation_runs=ddmrp_evaluation_runs,
        evaluation_rows=ddmrp_evaluation_rows,
        chains=ddmrp_replenishment_chains,
        recommendations=ddmrp_replenishment_recommendations,
        events=tuple(ddmrp_replenishment_events),
        active_replenishment_graphs=ddmrp_active_replenishment_graphs,
    ),
}
```

Unknown package/config is 404; invalid stored snapshot, authority/signature/domain, changed request reuse, orphan, or graph drift is structured 409; request extras are 422; RBAC is 401/403. Every response retains `X-Workbench-Revision`.

- [ ] **Step 8: Run matching GREEN, regressions, and commit**

```powershell
$tests = @(
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_references_stored_validated_package_only',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_rejects_raw_authority_fields_with_422',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_uses_server_actor_and_server_time',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_lost_response_retry_returns_duplicate_after_save',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_request_id_reuse_with_different_package_returns_409',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_canonicalizes_z_and_offset_snapshot_at_for_signature_evaluation_and_rows',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_rejects_naive_or_invalid_snapshot_at',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_public_demo_is_read_only',
  'tests/test_api.py::test_be_ddmrp_007_workbench_api_uses_standard_wrapper_and_safe_shape',
  'tests/test_api.py::test_be_ddmrp_007_write_revision_and_save_failure_restore_every_ledger',
  'tests/test_api.py::test_be_ddmrp_007_ddmrp_routes_enforce_viewer_planner_admin_rbac',
  'tests/test_api.py::test_be_ddmrp_007_unrelated_workbench_write_does_not_change_relevant_ledger_identity'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-api-green -p no:cacheprovider
pytest tests/test_api.py tests/test_ddmrp_replenishment.py tests/test_ddmrp_replenishment_view.py tests/test_state_store.py -q -k "be_ddmrp_007" --basetemp .tmp/pytest-ddmrp-api-regression -p no:cacheprovider
python -m compileall -q sdbr
```

Expected GREEN: exact selection 15 passed; regression selection has a non-zero recorded passing count; compile exits 0. Then:

```powershell
git add sdbr/api.py tests/test_api.py
git commit -m "feat: expose read-only DDMRP evaluations"
```

---

### Task 9: Reproducible Controlled Read-Only Acceptance Seed

**Files:**
- Modify: `sdbr/test_data.py`
- Modify: `tests/test_test_data.py`

**Interfaces:**
- Adds `TST-DDMRP-REPLENISHMENT-READONLY-20260711` to the existing test reset path.
- The seed is explicitly `TestFixtureOnly` and cannot authorize writes.
- Adds the same case ID once to `test_case_catalog_payload()["DdmrpRuntimeCases"]`; acceptance verifies the catalog entry and the resulting workbench independently of reset-summary stdout.

- [ ] **Step 1: Write the failing seed/catalog/workbench test**

Add `test_be_ddmrp_007_seeded_read_only_replenishment_workbench_is_reproducible` with module traceability `BE-DDMRP-007 / UI-DDMRP-003`. Reset a temporary SQLite DB and create the app from a newly opened `SQLiteWorkbenchStateStore`. GET `/planner/workbench/test-data/cases` and require exactly one `DdmrpRuntimeCases` entry whose `CaseID` is `TST-DDMRP-REPLENISHMENT-READONLY-20260711`, whose covered IDs are exactly `BE-DDMRP-007` and `UI-DDMRP-003`, and whose expected summary is Red/Yellow/Green/AboveGreen `1/1/1/1`, blocked `2`, pending `0`, active graphs `0`.

Then GET `/planner/workbench/ddmrp/workbench` and assert the same exact summary, exactly these four sorted item/location pairs, and no others:

```python
[
    ("TST-DDMRP-RO-ABOVE-GREEN", "TST-MAIN"),
    ("TST-DDMRP-RO-GREEN", "TST-MAIN"),
    ("TST-DDMRP-RO-RED", "TST-MAIN"),
    ("TST-DDMRP-RO-YELLOW", "TST-MAIN"),
]
```

Red/Yellow are blocked recommendation rows; Green/AboveGreen are zero-quantity monitor rows. Every row has the canonical seeded `EvaluationAt`, null target, exact four gate-backed issues, `OperationalActionAllowed=False`, `PendingReviewCount == 0`, and no active graph or operational control.

- [ ] **Step 2: Run the exact seed node in RED before changing the seed**

```powershell
pytest tests/test_test_data.py::test_be_ddmrp_007_seeded_read_only_replenishment_workbench_is_reproducible -q --basetemp .tmp/pytest-ddmrp-seed-red -p no:cacheprovider
```

Expected RED: 1 selected, 0 passed, 1 failed because the case is absent from `Data.DdmrpRuntimeCases` and the reset store has no versioned read-only evaluation. Record the actual selected/failed count.

- [ ] **Step 3: Extend the existing seed, not a new hidden data path**

Define constants for the case ID and four item IDs above. Add one versioned `DdmrpRuntimeCases` catalog entry with the exact expected summary/covered IDs. Seed the new ledgers using the public DDMRP domain builders and the canonical UTC evaluation instant `2026-07-11T01:00:00+00:00`. Its authority signature has all activation-only refs `None`, `scenario_label="DemoFixture"`, `mapping_confidence="PublicDemoOnly"`, and all four gates. Do not add fields to `TestDataResetSummary`, and do not seed a fake accepted advice/BOM/production package.

- [ ] **Step 4: Run the identical node in GREEN, then a separate broad regression**

```powershell
pytest tests/test_test_data.py::test_be_ddmrp_007_seeded_read_only_replenishment_workbench_is_reproducible -q --basetemp .tmp/pytest-ddmrp-seed-green -p no:cacheprovider
pytest tests/test_test_data.py tests/test_api.py -q -k "seeded_read_only_replenishment or be_ddmrp_007_workbench" --basetemp .tmp/pytest-ddmrp-seed -p no:cacheprovider
```

Expected GREEN: the identical exact node reports 1 selected, 1 passed, 0 failed. The separate broad command selects a non-zero count and passes; record its selected/pass count independently.

- [ ] **Step 5: Commit**

```powershell
git add sdbr/test_data.py tests/test_test_data.py
git commit -m "test: seed gated DDMRP workbench state"
```

---

### Task 10: UI-DDMRP-003 Read-Only Versioned Workbench

**Files:**
- Modify: `sdbr/web/planner-workbench.html` at `#material-planning-view`
- Modify: `sdbr/web/planner-workbench.js` at state declarations, `materialPlanningRows`, render/load functions, and startup listeners
- Modify: `sdbr/web/planner-workbench.css` at `.material-*` and the `max-width: 900px` breakpoint
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes exact GET wrapper `body.Data` and `X-Workbench-Revision`.
- Uses existing `showNotification(...)`, `setStatusChip(...)`, and current `fetch`/wrapper parsing style.
- Produces no confirmation button in this acceptance unit.

- [ ] **Step 1: Write one specifically named RED static-contract test**

Add exactly:

```python
def test_ui_ddmrp_003_renders_versioned_gated_workbench_without_operational_actions() -> None:
    # UI-DDMRP-003 / BE-DDMRP-007
    client = TestClient(create_app())
    html = client.get("/planner/workbench").text
    script = client.get("/planner/assets/planner-workbench.js").text

    assert 'id="material-planning-evaluation"' in html
    assert 'data-material-summary="BlockedRecommendationCount"' in html
    assert 'data-i18n="standardTargetStatus"' in html
    assert 'id="material-planning-active-graphs"' in html
    assert 'id="material-planning-history"' in html
    assert 'id="material-planning-technical-details"' in html
    assert "/planner/workbench/ddmrp/workbench" in script
    assert "payload.Data" in script
    assert 'response.headers.get("X-Workbench-Revision")' in script
    assert "showNotification(" in script
    assert "/planner/workbench/ddmrp/recommendations/" not in script
    assert 'id="confirm-material-recommendation"' not in html
    assert 'id="ddmrp-buffer-profile-editor"' not in html
    assert 'id="ddmrp-adjustment-factor-editor"' not in html
```

Assert IDs for evaluation freshness, blocked count, target/gate columns, active/history sections, and technical `<details>`. Assert script contains `/planner/workbench/ddmrp/workbench`, `payload.Data`, `X-Workbench-Revision`, and `showNotification`. Assert it does not contain a confirm endpoint, ERP-order button, raw JSON viewer, client target calculation, `notify(`, or DDMRP parameter controls.

- [ ] **Step 2: Run RED with a selector that selects the test**

```powershell
pytest tests/test_api.py -q -k "test_ui_ddmrp_003_renders_versioned_gated_workbench_without_operational_actions" --basetemp .tmp/pytest-ui-ddmrp-003-red -p no:cacheprovider
```

Expected: one selected failing test, not zero selected tests.

- [ ] **Step 3: Implement exact wrapper-aware loading**

Declare:

```javascript
let materialPlanningData = null;
let materialPlanningRevision = null;
```

Replace the load body with:

```javascript
async function loadMaterialPlanning() {
  try {
    const response = await fetch("/planner/workbench/ddmrp/workbench", {
      headers: { Accept: "application/json" }
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.Data?.Message || String(response.status));
    materialPlanningRevision = response.headers.get("X-Workbench-Revision");
    renderMaterialPlanning(payload.Data);
  } catch (error) {
    materialPlanningRevision = null;
    renderMaterialPlanning(null);
    showNotification(error.message || translate("materialPlanningLoadFailed"), "error");
  }
}
```

Render from `Data.Rows`; do not recalculate `BufferPercent`, target, recommendation identity, advice, active graph, or gate state in JavaScript. Use `RecommendationID || RowKey` from the server. Keep technical IDs/fingerprints inside collapsed details.

- [ ] **Step 4: Implement restrained markup and responsive CSS**

Add summary cells for blocked, adjustment-required, and active graphs; columns for target status and recommendation status; detail sections for authority freshness, business gates, active/history links, and technical details. Remove the existing nested `.material-detail-card` framing in the touched detail area and use unframed subsections. At `max-width: 900px`, stack detail metadata/actions and keep page-level `scrollWidth === clientWidth`; the table remains inside `.table-scroll`.

- [ ] **Step 5: Run static/UI checks and commit**

```powershell
node --check sdbr/web/planner-workbench.js
pytest tests/test_api.py tests/test_ddmrp_replenishment_view.py -q -k "ui_ddmrp_003 or be_ddmrp_007_view or be_ddmrp_007_workbench" --basetemp .tmp/pytest-ui-ddmrp-003-green -p no:cacheprovider
git add sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_api.py
git commit -m "feat: show gated DDMRP evaluation history"
```

---

### Task 11: Executable Browser Acceptance Fixture And Mode Contracts

**Files:**
- Create: `tests/ddmrp_browser_acceptance_app.py`
- Create: `tests/test_ddmrp_browser_acceptance_app.py`

**Interfaces:**
- Produces `create_ddmrp_browser_acceptance_app(state_store: WorkbenchStateStore) -> FastAPI` for tests and `create_runtime_app() -> FastAPI` for `uvicorn --factory`.
- Provides exactly `seeded`, `empty`, `error`, `403`, and `409` modes through acceptance-only `PUT /__ddmrp_acceptance__/mode/{mode}`.
- Never changes or imports from production `sdbr.api:app`; it wraps `create_app(state_store=...)` only inside the test module.

- [ ] **Step 1: Write the exact fixture RED tests**

Start `tests/test_ddmrp_browser_acceptance_app.py` with `"""Acceptance evidence for BE-DDMRP-007 and UI-DDMRP-003."""` and add:

```text
test_ui_ddmrp_003_browser_acceptance_fixture_modes_are_exact
test_ui_ddmrp_003_browser_acceptance_fixture_is_absent_from_production_app
```

Parameterize the first test over five modes. Seeded delegates to the real seeded SQLite-backed workbench and returns the exact Task 9 case. Empty returns the exact eight-key empty projection from `build_ddmrp_replenishment_workbench(...)`. Error/403/409 return status 500/403/409 with exact `{Endpoint, StatusCode, Data: {Status, Message}}`, and every response has `X-Workbench-Revision`. Assert switching mode mutates no workbench ledger and invalid mode returns 422. The production app must return 404 for the mode route.

- [ ] **Step 2: Run exact RED**

```powershell
$tests = @(
  'tests/test_ddmrp_browser_acceptance_app.py::test_ui_ddmrp_003_browser_acceptance_fixture_modes_are_exact',
  'tests/test_ddmrp_browser_acceptance_app.py::test_ui_ddmrp_003_browser_acceptance_fixture_is_absent_from_production_app'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-browser-fixture-red -p no:cacheprovider
```

Expected RED: 6 selected, 0 passed, 6 failed (five mode parameters plus one production-isolation case) because the acceptance app does not exist. Record the counts.

- [ ] **Step 3: Implement the acceptance-only app exactly**

Define:

```python
DDMRP_ACCEPTANCE_MODES = frozenset({"seeded", "empty", "error", "403", "409"})
DDMRP_WORKBENCH_ENDPOINT = "/planner/workbench/ddmrp/workbench"


def create_ddmrp_browser_acceptance_app(
    state_store: WorkbenchStateStore,
) -> FastAPI:
    production_app = create_app(state_store=state_store)
    app = FastAPI()
    app.state.ddmrp_acceptance_mode = "seeded"

    @app.put("/__ddmrp_acceptance__/mode/{mode}")
    def set_mode(mode: str) -> dict[str, object]:
        if mode not in DDMRP_ACCEPTANCE_MODES:
            raise HTTPException(status_code=422, detail="Unsupported DDMRP acceptance mode.")
        app.state.ddmrp_acceptance_mode = mode
        return {"Mode": mode}

    @app.middleware("http")
    async def fixture_mode(request: Request, call_next):
        if request.method != "GET" or request.url.path != DDMRP_WORKBENCH_ENDPOINT:
            return await call_next(request)
        mode = str(app.state.ddmrp_acceptance_mode)
        if mode == "seeded":
            return await call_next(request)
        revision = str(state_store.current_revision())
        if mode == "empty":
            data = build_ddmrp_replenishment_workbench(
                evaluation_runs={},
                evaluation_rows={},
                chains={},
                recommendations={},
                events=(),
                active_replenishment_graphs={},
            )
            return JSONResponse(
                status_code=200,
                content={"Endpoint": DDMRP_WORKBENCH_ENDPOINT, "StatusCode": 200, "Data": data},
                headers={"X-Workbench-Revision": revision},
            )
        status_code = {"error": 500, "403": 403, "409": 409}[mode]
        status = {"error": "FixtureError", "403": "Forbidden", "409": "Conflict"}[mode]
        return JSONResponse(
            status_code=status_code,
            content={
                "Endpoint": DDMRP_WORKBENCH_ENDPOINT,
                "StatusCode": status_code,
                "Data": {"Status": status, "Message": f"DDMRP acceptance fixture mode: {mode}"},
            },
            headers={"X-Workbench-Revision": revision},
        )

    app.mount("/", production_app)
    return app
```

`create_runtime_app()` requires `SDBR_ENVIRONMENT=test` and `SDBR_WORKBENCH_DB_PATH`, opens `SQLiteWorkbenchStateStore` at that exact path, and returns `create_ddmrp_browser_acceptance_app(store)`. Missing/non-test environment fails startup. No fixture symbol is imported by `sdbr/api.py` or packaged into a production entry point.

- [ ] **Step 4: Run identical GREEN selection and commit**

```powershell
$tests = @(
  'tests/test_ddmrp_browser_acceptance_app.py::test_ui_ddmrp_003_browser_acceptance_fixture_modes_are_exact',
  'tests/test_ddmrp_browser_acceptance_app.py::test_ui_ddmrp_003_browser_acceptance_fixture_is_absent_from_production_app'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-browser-fixture-green -p no:cacheprovider
```

Expected GREEN: 6 selected, 6 passed, 0 failed. Then:

```powershell
git add tests/ddmrp_browser_acceptance_app.py tests/test_ddmrp_browser_acceptance_app.py
git commit -m "test: add DDMRP browser acceptance modes"
```

---

### Task 12: NOW Verification, Spec Evidence, Browser Matrix, And Stop

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`
- Optional ignored local evidence: `.tmp/ddmrp-ui-acceptance/`

- [ ] **Step 1: Run focused and full automated verification**

```powershell
python -m compileall -q sdbr
node --check sdbr/web/planner-workbench.js
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_ddmrp_replenishment.py tests/test_ddmrp_replenishment_view.py tests/test_state_store.py tests/test_test_data.py tests/test_api.py tests/test_ddmrp_browser_acceptance_app.py -q --basetemp .tmp/pytest-ddmrp-readonly-focused -p no:cacheprovider
pytest -q --basetemp .tmp/pytest-ddmrp-readonly-full -p no:cacheprovider
git diff --check
```

Record actual pass counts/warnings; do not prefill them.

- [ ] **Step 2: Build the deterministic browser database**

```powershell
$env:SDBR_ENVIRONMENT = 'test'
$env:SDBR_WORKBENCH_DB_PATH = (Join-Path (Get-Location) '.tmp\ddmrp-ui-acceptance\workbench-state.db')
New-Item -ItemType Directory -Force -Path '.tmp\ddmrp-ui-acceptance' | Out-Null
sdbr-reset-test-data --database-path $env:SDBR_WORKBENCH_DB_PATH
```

Expected: reset summary names the temporary DB. Do not claim that stdout contains the DDMRP case ID; Step 3 verifies the catalog and workbench endpoints directly.

- [ ] **Step 3: Preflight the port, start the fixture app, bound health retries, and verify the exact seed**

Run the following in a PTY so it pauses at `Read-Host` while browser checks execute. It performs no unbounded polling and owns shutdown in `finally`:

```powershell
$env:SDBR_ENVIRONMENT = 'test'
$env:SDBR_WORKBENCH_DB_PATH = (Join-Path (Get-Location) '.tmp\ddmrp-ui-acceptance\workbench-state.db')
$port = 8011
$listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
if ($null -ne $listener) { throw "Port $port is already in use." }
$server = $null
try {
  $server = Start-Process python -ArgumentList '-m','uvicorn','tests.ddmrp_browser_acceptance_app:create_runtime_app','--factory','--host','127.0.0.1','--port',"$port" -PassThru -WindowStyle Hidden
  $health = $null
  for ($attempt = 1; $attempt -le 40; $attempt++) {
    if ($server.HasExited) { throw "DDMRP acceptance server exited during startup." }
    try {
      $health = Invoke-RestMethod "http://127.0.0.1:$port/planner/workbench/state-store/health" -TimeoutSec 1
      break
    } catch {
      Start-Sleep -Milliseconds 250
    }
  }
  if ($null -eq $health) { throw "DDMRP acceptance server was not healthy within 10 seconds." }

  $catalog = Invoke-RestMethod "http://127.0.0.1:$port/planner/workbench/test-data/cases" -TimeoutSec 2
  $catalogCases = @($catalog.Data.DdmrpRuntimeCases | Where-Object { $_.CaseID -eq 'TST-DDMRP-REPLENISHMENT-READONLY-20260711' })
  if ($catalogCases.Count -ne 1) { throw "Exact DDMRP acceptance catalog case was not found once." }
  $workbench = Invoke-RestMethod "http://127.0.0.1:$port/planner/workbench/ddmrp/workbench" -TimeoutSec 2
  $summary = $workbench.Data.Summary
  if ($summary.RedCount -ne 1 -or $summary.YellowCount -ne 1 -or $summary.GreenCount -ne 1 -or $summary.AboveGreenCount -ne 1 -or $summary.BlockedRecommendationCount -ne 2 -or $summary.PendingReviewCount -ne 0 -or $summary.ActiveGraphCount -ne 0) {
    throw "Seeded DDMRP workbench summary differs from the catalog contract."
  }
  $actualKeys = @($workbench.Data.Rows | ForEach-Object { "$($_.ItemID)@$($_.LocationID)" } | Sort-Object)
  $expectedKeys = @('TST-DDMRP-RO-ABOVE-GREEN@TST-MAIN','TST-DDMRP-RO-GREEN@TST-MAIN','TST-DDMRP-RO-RED@TST-MAIN','TST-DDMRP-RO-YELLOW@TST-MAIN')
  if (Compare-Object $expectedKeys $actualKeys) { throw "Seeded DDMRP workbench row set differs from the exact case." }
  Write-Output 'DDMRP_BROWSER_READY'
  Read-Host 'Press Enter only after every browser mode and evidence file is complete'
} finally {
  if ($null -ne $server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    Wait-Process -Id $server.Id -Timeout 10 -ErrorAction SilentlyContinue
  }
}
```

Use the in-app browser at `http://127.0.0.1:8011/planner/workbench#material-planning`. Capture:

```text
.tmp/ddmrp-ui-acceptance/browser-report.md
.tmp/ddmrp-ui-acceptance/seeded-1280x720.png
.tmp/ddmrp-ui-acceptance/seeded-1920x1080.png
.tmp/ddmrp-ui-acceptance/seeded-390x844.png
.tmp/ddmrp-ui-acceptance/empty-1280x720.png
.tmp/ddmrp-ui-acceptance/error-1280x720.png
.tmp/ddmrp-ui-acceptance/403-1280x720.png
.tmp/ddmrp-ui-acceptance/409-1280x720.png
```

For each mode, run `Invoke-RestMethod -Method Put "http://127.0.0.1:8011/__ddmrp_acceptance__/mode/$mode"`, reload the page, and record expected/observed status plus screenshot path in `browser-report.md`. At all three seeded widths verify wrapper-loaded exact case data, Red/Yellow blocked rows, Green/Above monitor rows, null target with immutable business gate text, collapsed technical details, search/filter/sort/history, Chinese/English, keyboard focus, and no page-level horizontal overflow. At 1280 verify empty, error, 403, and 409 rendering/notification separately. Verify there is no confirm control in any mode.

After all files exist and the report names the exact catalog/workbench checks, send one newline to the waiting PTY. The `finally` block must report process exit; independently prove the port is free:

```powershell
if (Get-NetTCPConnection -State Listen -LocalPort 8011 -ErrorAction SilentlyContinue) { throw 'Port 8011 remained in use after acceptance shutdown.' }
```

- [ ] **Step 4: Record exact 2.81 / 5.36 evidence**

Set backend header/changelog to `2.81 / 2026-07-11`; mark only `BE-DDMRP-007` `[VERIFIED]` with exact `C/A/T/R` evidence and actual counts. Keep `BE-DDMRP-008`/`009` `[NOT-STARTED]` and name the gate.

Set UI header/changelog to `5.36 / 2026-07-11`; mark only `UI-DDMRP-003` `已验证待用户确认` with `.tmp/ddmrp-ui-acceptance/browser-report.md`, all seven named screenshot paths, and actual automated/browser counts. Keep `UI-DDMRP-004` `未开始`.

- [ ] **Step 5: Commit evidence and stop**

```powershell
git add docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: verify read-only DDMRP workbench"
```

Report `UI-DDMRP-003`, URL, tests, browser evidence, and commit. Ask for explicit user confirmation. Do not mark it `用户已确认`, do not start `UI-DDMRP-004`, and do not cross the contract gate.

---

## CONTRACT-GATE-DDMRP-ACTIVATION-001

**Current status: CLOSED. Contract Agent-owned. No SDBR operational activation work may begin.**

The SDBR implementation owner must submit a backlog input with proposed path:

```text
D:\Documents\DDAE_INTERFACE_CONTRACT\reviews\SDBR-DDMRP-OPERATIONAL-REPLENISHMENT-ACTIVATION-BACKLOG-INPUT.md
```

This is a proposed backlog document name, not an accepted contract/envelope ID. It requests Contract Agent resolution of these exact gaps:

1. A versioned, validated ERP/MRP replenishment advice source that authorizes `Buy` or `Make` server-side and has package ID/version/fingerprint, idempotency, source/observed time, supersession, and accepted authority classification.
2. A versioned Plan BOM/feasibility source with BOM version/effectivity, component quantity/UOM, source type, decoupling-stop semantics, routing/version, operation/resource load, CCR classification, calendar/capacity snapshot, and traceable evidence refs.
3. Accepted DLT target-time semantics: elapsed or business time, timezone, receipt calendar ID/version/fingerprint, closures/shift/DST behavior, and target-date policy ID/version. The accepted contract, not this plan, must choose the rule.
4. Source-authoritative material/inventory evidence and current snapshot identity/fingerprint. Reviewed fixtures with `SourceAuthoritativeUsable=False` do not qualify.
5. Source-authoritative capacity/calendar/routing evidence and current identity/fingerprint. Public-demo adapter calendars do not qualify.
6. An execution-authority decision that maps allowed `ScenarioLabel`, `MappingConfidence`, and row-level authority classifications to operational SDBR writes. `PublicDemoOnly`, `ReviewedEvidence`, fixture-seeded, and unresolved candidate evidence must remain denied.
7. Consumer contract tests, intake acceptance, implementation-readiness acceptance, and an implementation-dispatch record that names the accepted contract IDs/versions/schema fingerprints and authorized fixtures.

The gate opens only when all seven items are present in Contract Agent acceptance/dispatch evidence and the user has confirmed `UI-DDMRP-003`. A draft schema, reviewed fixture, source string, example payload, or SDBR request body cannot open it.

While the gate is closed:

- no `POST .../confirm` route;
- no client or API advice override;
- no `StandardTargetReceiptAt` calculation;
- no demand commitment, candidate, CCR reservation, or material allocation;
- no `[PARTIAL]` or `[VERIFIED]` claim for `BE-DDMRP-008`/`009` based only on interfaces or fixtures.

---

## BLOCKED-ACTIVATION Blueprint

This section preserves the approved eventual business behavior and fixes the architecture now, but it is **not executable** until the gate is open. At reopening, first replace contract-mapping statements with the exact accepted consumer symbols and re-run `superpowers:writing-plans`; do not invent those mappings from this blueprint.

### Activation Task A1: Accepted Authority Adapter And Full Freshness Context

**Review/commit boundary:** contract consumer only.

**Files after gate:** accepted consumer module named by Contract Agent, `sdbr/ddmrp_replenishment.py`, `tests/test_ddmrp_replenishment.py`, contract-consumer tests.

Internal SDBR interface (independent of external field names):

```python
@dataclass(frozen=True, slots=True)
class DdmrpConfirmationFreshnessContext:
    frozen: DdmrpAuthoritySignature
    current: DdmrpAuthoritySignature


def assert_ddmrp_confirmation_fresh(
    context: DdmrpConfirmationFreshnessContext,
) -> None:
    if context.frozen != context.current:
        raise DdmrpReplenishmentConflict(
            "CURRENT_AUTHORITY_SIGNATURE_CHANGED: reevaluation required."
        )
```

The accepted adapter must populate every currently-null pair in `DdmrpAuthoritySignature`; it may not accept request-body rows. Add one RED/GREEN test for drift of each source:

```text
test_be_ddmrp_008_rejects_current_runtime_package_drift
test_be_ddmrp_008_rejects_current_operating_configuration_drift
test_be_ddmrp_008_rejects_current_advice_package_drift
test_be_ddmrp_008_rejects_current_plan_bom_package_drift
test_be_ddmrp_008_rejects_current_material_authority_snapshot_drift
test_be_ddmrp_008_rejects_current_capacity_calendar_snapshot_drift
test_be_ddmrp_008_rejects_current_local_planning_ledger_drift
test_be_ddmrp_008_public_demo_and_reviewed_evidence_never_become_actionable
```

The target policy comes only from the accepted consumer. Test timezone, closure, shift, holiday, and DST examples supplied by that contract. No fallback branch is allowed.

Commit after the gate-specific tests pass:

```powershell
git commit -m "feat: consume accepted DDMRP activation authority"
```

### Activation Task A2: Plan BOM Explosion And Material/CCR Feasibility Preview

**Review/commit boundary:** pure read-only feasibility; no writes.

**Files after gate:** create `sdbr/ddmrp_feasibility.py`, create `tests/test_ddmrp_feasibility.py`.

Internal interfaces:

```text
def explode_plan_bom_preview(
    *,
    top_item_id: str,
    location_id: str,
    quantity: float,
    accepted_bom_snapshot: Mapping[str, object],
    decoupling_points: frozenset[tuple[str, str]],
) -> dict[str, object]


def build_ddmrp_make_feasibility_preview(
    *,
    recommendation: Mapping[str, object],
    authority_signature: DdmrpAuthoritySignature,
    bom_preview: Mapping[str, object],
    accepted_material_snapshot: Mapping[str, object],
    accepted_capacity_calendar_snapshot: Mapping[str, object],
    active_capacity_reservations: Mapping[str, dict[str, object]],
    active_material_allocations: Mapping[str, dict[str, object]],
) -> dict[str, object]
```

Required tests cite `BE-DDMRP-009`, `BE-SDBR-008`, and `BE-SDBR-009`: BOM cycle, missing/expired BOM version, missing UOM/conversion authority, invalid quantity, decoupling stop, non-decoupled Make recursion, Buy child advice, required-vs-allocated quantity, `uncommitted_supply_qty(...)`, duplicate supply prevention, CCR role/calendar/window validity, `reservation_load_by_bucket(...)`, over-capacity, shortage, `AwaitingMaterial`, non-release, and recalculated feasible completion/capacity window. Preview records freeze all authority IDs/fingerprints and remain read-only.

Commit:

```powershell
git commit -m "feat: preview DDMRP Make feasibility"
```

### Activation Task A3: Immutable Decision And Active-Graph Governance

**Review/commit boundary:** recommendation/decision lifecycle; no shared apply.

**Files after gate:** `sdbr/ddmrp_replenishment.py`, accepted formal-supply adapter named by A1, and `tests/test_ddmrp_replenishment.py`.

Recommendation core records remain immutable; events derive state through Task 4's exact event contracts. Exact states:

```text
Blocked -> PendingReview -> Confirmed
PendingReview -> Rejected | Superseded
Confirmed -> AdjustmentRequired | Issued | Released | Cancelled
Issued -> ERPAccepted | OutputFailed | AdjustmentRequired
ERPAccepted -> InExecution -> Completed
```

Only `PendingReview` can be confirmed. Add `DdmrpRelevantPlanningLedgerV2` before activation; V2 retains every V1 projection and adds exact candidate and normalized formal-supply projections:

```python
RELEVANT_CANDIDATE_FIELDS = (
    "PlannedManufacturingCandidateID", "LogicalReplenishmentID", "ItemID",
    "LocationID", "Uom", "PlannedSupplyQty", "Status", "FormalSupplyID",
    "RecordVersion", "LastTransitionAt",
)
RELEVANT_FORMAL_SUPPLY_FIELDS = (
    "FormalSupplyID", "LogicalReplenishmentID", "ItemID", "LocationID", "Uom",
    "RemainingOpenQty", "Status", "AuthorityPackageID", "AuthorityFingerprint",
)
CANDIDATE_COUNTED_STATUSES = frozenset({
    "AwaitingMaterial", "AwaitingPlanningRun", "FrozenIntoPlanningRun",
    "Scheduled", "HeldForPlanningError", "AdjustmentRequired",
})
CANDIDATE_HANDOFF_STATUSES = frozenset({"LinkedToFormalOrder", "InExecution"})
CANDIDATE_TERMINAL_STATUSES = frozenset({"Released", "Cancelled", "Completed"})
FORMAL_SUPPLY_COUNTED_STATUSES = frozenset({
    "Open", "Firm", "ReleasedToExecution", "InExecution",
})
FORMAL_SUPPLY_TERMINAL_STATUSES = frozenset({"Cancelled", "Completed", "Closed"})
ACTIVE_GRAPH_SUPPLY_STATUSES = frozenset({
    "ActivePlanReservation", "LinkedToFormalOrder", "HeldForPlanningError",
    "AdjustmentRequired", "InExecution",
})
TERMINAL_GRAPH_STATUSES = frozenset({"Released", "Cancelled", "Completed"})


@dataclass(frozen=True, slots=True)
class DdmrpExecutionFactAdjustment:
    logical_replenishment_id: str
    gross_replenishment_need_qty: float
    matched_runtime_supply_qty: float
    counted_active_supply_qty: float
    residual_need_qty: float
    adjustment_delta_qty: float
    adjustment_direction: Literal["Increase", "None", "Decrease"]
    counted_candidate_id: str | None
    counted_formal_supply_id: str | None


def adapt_ddmrp_active_execution_facts(
    *,
    evaluation_row: Mapping[str, object],
    active_graph: Mapping[str, object],
    planned_manufacturing_candidates: Mapping[str, Mapping[str, object]],
    normalized_formal_supplies: Mapping[str, Mapping[str, object]],
    material_planning_allocations: Mapping[str, Mapping[str, object]],
) -> DdmrpExecutionFactAdjustment:
```

The A1 adapter is solely responsible for mapping accepted external formal-supply statuses into the normalized allowlists; unknown statuses fail closed. The function requires exact item/location/UOM and canonical-ID matches. A graph in a terminal status contributes no active supply and must have a terminal chain fold before a new cycle. For an active graph, select exactly one supply fact:

- A candidate in `CANDIDATE_COUNTED_STATUSES` contributes `PlannedSupplyQty` and must not have a formal-supply link.
- A candidate in `CANDIDATE_HANDOFF_STATUSES` contributes zero itself and must link to exactly one normalized formal supply; only that formal supply's `RemainingOpenQty` is counted.
- A candidate/formal supply in a terminal status contributes zero. A cancelled formal supply leaves the graph `AdjustmentRequired`; it does not auto-release the graph or create a second graph. Explicit chain/graph release or cancellation is the only action that ends the cycle.
- More than one countable candidate, more than one formal supply, a countable candidate plus a countable formal supply outside the handoff rule, duplicate semantic IDs, negative quantities, UOM drift, or a missing handoff target raises `DdmrpReplenishmentConflict`.
- Material allocations are validated as child coverage of the selected candidate only. `AllocatedQty` never becomes demand, never reduces top-level demand, and never contributes supply.

Match the selected formal supply to `evaluation_row["SupplyComponents"]` by exact `SupplyID`. Require the summed matched runtime quantity to equal normalized `RemainingOpenQty`; mismatch is authority drift. Then calculate exactly:

```python
raw_signed_need_qty = float(evaluation_row["TopOfGreen"]) - float(
    evaluation_row["NetFlowPosition"]
)
gross_replenishment_need_qty = raw_signed_need_qty + matched_runtime_supply_qty
adjustment_delta_qty = gross_replenishment_need_qty - counted_active_supply_qty
residual_need_qty = max(adjustment_delta_qty, 0.0)
adjustment_direction = (
    "Increase" if adjustment_delta_qty > 0.0
    else "Decrease" if adjustment_delta_qty < 0.0
    else "None"
)
```

This adds back only the matched formal supply already present in net flow and then subtracts the selected execution fact once. Other runtime open supply remains in net flow. Positive delta creates an immutable `AdjustmentRequired` version carrying positive `AdjustmentDeltaQty` and `ResidualNeedQty`; zero delta produces `CoveredByActiveSupply` with no new recommendation version; negative delta creates immutable `AdjustmentRequired` with the signed negative delta and zero residual. No branch automatically changes, releases, cancels, or confirms the active graph. The active-graph guard always prevents a second confirmable graph.

The stable shared demand identity is:

```python
create_demand_commitment(
    demand_source_type="MTAReplenishment",
    source_system="SDBR",
    source_object_type="DdmrpLogicalReplenishment",
    source_object_id=recommendation["LogicalReplenishmentID"],
    source_object_version=str(recommendation["RecommendationVersion"]),
    demand_line_id=f"{recommendation['ItemID']}@{recommendation['LocationID']}",
    item_or_product_id=str(recommendation["ItemID"]),
    location_id=str(recommendation["LocationID"]),
    quantity=float(recommendation["SuggestedReplenishmentQty"]),
    uom=str(recommendation["Uom"]),
    required_at=datetime.fromisoformat(
        str(recommendation["StandardTargetReceiptAt"])
    ),
    demand_class="MTA",
    trace_id=str(recommendation["TraceID"]),
)
```

Add end-to-end domain tests:

```text
test_be_ddmrp_008_evaluate_confirm_reevaluate_cannot_create_second_active_graph
test_be_ddmrp_008_adjustment_version_links_old_recommendation_and_active_graph
test_be_ddmrp_008_release_then_new_cycle_uses_new_logical_replenishment_id
test_be_ddmrp_008_buy_decision_has_no_shared_ledger_side_effect
test_be_ddmrp_008_partial_candidate_coverage_has_positive_residual_and_delta
test_be_ddmrp_008_full_candidate_coverage_has_zero_delta_and_no_adjustment_version
test_be_ddmrp_008_candidate_overcoverage_has_negative_delta_without_auto_change
test_be_ddmrp_008_candidate_to_formal_supply_handoff_counts_once_with_runtime_supply
test_be_ddmrp_008_cancelled_formal_supply_returns_positive_delta_until_explicit_release
test_be_ddmrp_008_released_graph_excludes_old_supply_and_starts_new_cycle
test_be_ddmrp_008_material_allocations_never_become_demand_or_supply
```

Run these eleven exact nodes RED before adding V2/adapter behavior and GREEN afterward; expected RED is 11 selected/11 failed and expected GREEN is 11 selected/11 passed. The partial/full/over cases use base need `100` with active supply `40/100/120`, asserting deltas `+60/0/-20` and residuals `60/0/0`. The handoff case includes the same formal supply in runtime components and proves it is counted exactly once. Record both counts.

Commit:

```powershell
git commit -m "feat: govern DDMRP recommendation decisions"
```

### Activation Task A4: Candidate-Aware Shared Reservation Write Set

**Review/commit boundary:** shared write-set compatibility only.

Extend `PlanningReservationWriteSet` with optional `manufacturing_candidate` and add an optional candidate ledger to `apply_reservation_write_set`. Include candidate content in business fingerprint/result only when non-`None`; keep the current no-candidate fingerprint exactly:

```text
sha256:9d5b69614f983a66d6ee4121ba187a081bdb7286d4b40cc0844fc14d5d301533
```

Candidate initial status is `AwaitingMaterial` when any accepted requirement is short, otherwise `AwaitingPlanningRun`. Positive available portions create material allocations; shortages remain immutable feasibility lines and generate only server-authorized Buy/Make dependent recommendations in the composite DDMRP write. Every top-level and dependent recommendation must satisfy `AdviceType in {"Buy", "Make"}` before staging. Caller-supplied `OrderID`, candidate ID, status, authority boundary, or reservation identity is rejected/overwritten by generated values.

Define the candidate event contract exactly:

```python
CANDIDATE_EVENT_FIELDS = (
    "CandidateEventID", "EventType", "PlannedManufacturingCandidateID",
    "CandidateVersion", "StatusBefore", "StatusAfter", "OccurredAt", "ActorID",
    "CausationID", "CorrelationID", "EventPayload", "PayloadFingerprint",
)
CANDIDATE_EVENT_PAYLOAD_FIELDS_BY_TYPE = {
    "ManufacturingCandidateCreated": (
        "LogicalReplenishmentID", "PlannedSupplyQty", "Uom", "ReservationBatchID",
    ),
    "ManufacturingCandidateStatusChanged": (
        "ReasonCode", "PlanningRunID", "FormalSupplyID",
    ),
}
```

`ManufacturingCandidateCreated` is mandatory version 1 with `StatusBefore=None` and `StatusAfter` equal to the immutable candidate initial status. `ManufacturingCandidateStatusChanged` uses contiguous versions, exact lifecycle transitions from A6, and exact payload keys; terminal statuses reject later events. Candidate event ID is canonical JSON over candidate ID/version/type, and payload fingerprint covers only exact payload fields. Unknown type, extra key, version gap/duplicate, illegal transition, or record/event status mismatch fails before shared apply.

Tests cite `BE-DDMRP-009` and `BE-SDBR-006` through `009`; split candidate construction, exact candidate event payload/fold, candidate replay, dependent Buy/Make allowlist, and legacy fingerprint into separate RED/GREEN commits.

### Activation Task A5: Exact Copy-On-Write Composite Confirmation

**Review/commit boundary:** pure-domain atomic composition.

Replace every bare DDMRP processed key with one immutable request-result record keyed by `ActionRequestID`. Define exact contracts first:

```python
CONFIRMATION_PLANNING_OBJECT_FIELDS = (
    "PlannedManufacturingCandidateID", "ReservationBatchID",
    "CapacityReservationIDs", "MaterialAllocationIDs", "DependentRecommendationIDs",
)
CONFIRMATION_RESPONSE_DATA_FIELDS = (
    "Status", "RecommendationID", "ConfirmedAction", "DecisionID",
    "PlanningObjects", "ExternalOrderCreated",
)
CONFIRMATION_REQUEST_RESULT_FIELDS = (
    "ActionRequestID", "RequestFingerprint", "RecommendationID",
    "LogicalReplenishmentID", "DecisionID", "RecommendationEventIDs",
    "ActiveGraphLogicalReplenishmentID", "DependentRecommendationIDs",
    "PlannedManufacturingCandidateID", "CandidateEventIDs", "DemandCommitmentID",
    "ReservationBatchID", "CapacityReservationIDs", "MaterialAllocationIDs",
    "PlanningEventIDs", "PlanningIdempotencyKey", "ResponseData",
    "ResponseFingerprint", "RecordedAt", "RecordedBy", "RequestResultFingerprint",
)


@dataclass(frozen=True, slots=True)
class DdmrpConfirmationWriteSet:
    action_request_id: str
    request_fingerprint: str
    recommendation_id: str
    logical_replenishment_id: str
    reservation_write_set: PlanningReservationWriteSet | None
    decision: dict[str, object]
    recommendation_events: tuple[dict[str, object], ...]
    active_graph: dict[str, object] | None
    dependent_recommendations: tuple[dict[str, object], ...]
    candidate_events: tuple[dict[str, object], ...]
    request_result: dict[str, object]


@dataclass(slots=True)
class DdmrpCompositeLedgers:
    recommendations: dict[str, dict[str, object]]
    recommendation_events: list[dict[str, object]]
    decisions: dict[str, dict[str, object]]
    active_graphs: dict[str, dict[str, object]]
    candidates: dict[str, dict[str, object]]
    candidate_events: list[dict[str, object]]
    commitments: dict[str, dict[str, object]]
    batches: dict[str, dict[str, object]]
    capacities: dict[str, dict[str, object]]
    materials: dict[str, dict[str, object]]
    planning_events: list[dict[str, object]]
    confirmation_results: dict[str, dict[str, object]]
    planning_keys: set[str]


@dataclass(frozen=True, slots=True)
class DdmrpConfirmationStagedState:
    recommendations: dict[str, dict[str, object]]
    recommendation_events: tuple[dict[str, object], ...]
    decisions: dict[str, dict[str, object]]
    active_graphs: dict[str, dict[str, object]]
    candidates: dict[str, dict[str, object]]
    candidate_events: tuple[dict[str, object], ...]
    commitments: dict[str, dict[str, object]]
    batches: dict[str, dict[str, object]]
    capacities: dict[str, dict[str, object]]
    materials: dict[str, dict[str, object]]
    planning_events: tuple[dict[str, object], ...]
    confirmation_results: dict[str, dict[str, object]]
    planning_keys: frozenset[str]
    result: dict[str, object]
```

The request fingerprint is canonical JSON over exactly `ActionRequestID`, route `RecommendationID`, exact `Reason`, and authenticated server `ActorID`. `If-Match`, server time, current authority, and rebuilt child content are excluded. Persisted `ResponseData.Status` is `Confirmed`; replay returns a deep copy with only `Status` changed to `Duplicate`. `PlanningObjects` is `None` for Buy and an exact `CONFIRMATION_PLANNING_OBJECT_FIELDS` mapping for Make. Every ID list is sorted and unique. Buy requires all shared/candidate IDs and `PlanningIdempotencyKey` null/empty; Make requires exact non-null IDs. `ExternalOrderCreated` is always `False`.

Implement replay lookup as an independent first operation:

```python
def lookup_ddmrp_confirmation_request_result(
    *,
    action_request_id: str,
    request_fingerprint: str,
    ledgers: DdmrpCompositeLedgers,
) -> dict[str, object] | None:
    persisted = ledgers.confirmation_results.get(action_request_id)
    if persisted is None:
        return None
    if persisted.get("ActionRequestID") != action_request_id:
        raise DdmrpReplenishmentConflict("CONFIRMATION_REQUEST_RESULT_KEY_MISMATCH")
    _require_exact_fields(
        persisted,
        CONFIRMATION_REQUEST_RESULT_FIELDS,
        context="DDMRP confirmation request result",
    )
    fingerprint_source = {
        key: deepcopy(persisted[key])
        for key in CONFIRMATION_REQUEST_RESULT_FIELDS
        if key != "RequestResultFingerprint"
    }
    if persisted["RequestResultFingerprint"] != canonical_fingerprint(fingerprint_source):
        raise DdmrpReplenishmentConflict("CONFIRMATION_REQUEST_RESULT_DRIFT")
    if persisted["RequestFingerprint"] != request_fingerprint:
        raise DdmrpReplenishmentConflict("ACTION_REQUEST_ID_REUSED")
    _validate_persisted_confirmation_result_graph(result=persisted, ledgers=ledgers)
    response = deepcopy(persisted["ResponseData"])
    response["Status"] = "Duplicate"
    return response
```

`_validate_persisted_confirmation_result_graph(...)` recomputes exact response/result fingerprints and proves all listed child IDs exist with matching mapping keys, immutable record/event payload fingerprints, canonical event versions/folds, and back-references to the recommendation/logical chain/decision/action request. It proves exact membership for decision, recommendation events, optional active graph, dependent recommendations, optional candidate and candidate events, demand, batch, capacity, material, and planning events. For Make it also proves the shared replay result and `PlanningIdempotencyKey` membership; for Buy it proves those child sets are empty. Missing, extra, duplicated, orphaned, or drifted membership conflicts. It validates only the persisted completed graph and accepts no current-authority, clock, freshness, or write-set-builder callback.

Only an unprocessed action may enter staging:

```python
def stage_ddmrp_confirmation_unprocessed(
    *,
    write_set: DdmrpConfirmationWriteSet,
    freshness: DdmrpConfirmationFreshnessContext,
    ledgers: DdmrpCompositeLedgers,
) -> DdmrpConfirmationStagedState:
    if write_set.action_request_id in ledgers.confirmation_results:
        raise DdmrpReplenishmentConflict("CONFIRMATION_REPLAY_LOOKUP_REQUIRED")
    assert_ddmrp_confirmation_fresh(freshness)
    copied = deepcopy(ledgers)
    if write_set.logical_replenishment_id in copied.active_graphs:
        raise DdmrpReplenishmentConflict(
            "Logical replenishment already has an active planning graph."
        )
    if write_set.reservation_write_set is not None:
        apply_reservation_write_set(
            write_set=write_set.reservation_write_set,
            commitments=copied.commitments,
            batches=copied.batches,
            planned_manufacturing_candidates=copied.candidates,
            capacity_reservations=copied.capacities,
            material_allocations=copied.materials,
            events=copied.planning_events,
            processed_event_keys=copied.planning_keys,
        )
    _insert_immutable_record(copied.decisions, "DecisionID", write_set.decision)
    if write_set.active_graph is not None:
        _insert_immutable_record(
            copied.active_graphs,
            "LogicalReplenishmentID",
            write_set.active_graph,
        )
    for recommendation in write_set.dependent_recommendations:
        if recommendation.get("AdviceType") not in {"Buy", "Make"}:
            raise DdmrpReplenishmentConflict("UNSUPPORTED_ACTIVATION_ADVICE_TYPE")
        _insert_immutable_record(
            copied.recommendations,
            "RecommendationID",
            recommendation,
        )
    _append_immutable_events(copied.recommendation_events, write_set.recommendation_events)
    _append_immutable_events(copied.candidate_events, write_set.candidate_events)
    _assert_complete_composite_graph(write_set=write_set, ledgers=copied)
    _insert_immutable_record(
        copied.confirmation_results,
        "ActionRequestID",
        write_set.request_result,
    )
    _validate_persisted_confirmation_result_graph(
        result=write_set.request_result,
        ledgers=copied,
    )
    return DdmrpConfirmationStagedState(
        recommendations=deepcopy(copied.recommendations),
        recommendation_events=tuple(deepcopy(copied.recommendation_events)),
        decisions=deepcopy(copied.decisions),
        active_graphs=deepcopy(copied.active_graphs),
        candidates=deepcopy(copied.candidates),
        candidate_events=tuple(deepcopy(copied.candidate_events)),
        commitments=deepcopy(copied.commitments),
        batches=deepcopy(copied.batches),
        capacities=deepcopy(copied.capacities),
        materials=deepcopy(copied.materials),
        planning_events=tuple(deepcopy(copied.planning_events)),
        confirmation_results=deepcopy(copied.confirmation_results),
        planning_keys=frozenset(copied.planning_keys),
        result=deepcopy(write_set.request_result["ResponseData"]),
    )
```

`_insert_immutable_record` always rejects a pre-existing ID for an unprocessed action, even when content matches. `_append_immutable_events` rejects duplicate event IDs/content. `_assert_complete_composite_graph` validates exact field sets, all event payload/fold contracts, accepted Buy/Make advice, shared business fingerprint/result, and child membership before the immutable result is inserted last.

`apply_ddmrp_confirmation_staged_state(...)` takes the staged state plus the same thirteen live collections. It deep-copies all thirteen first, then uses `clear/update` or `clear/extend` to publish every staged collection. A single `except BaseException` restores all thirteen snapshots before re-raising. It performs no validation after replacement starts. The state-store transaction remains a second rollback layer.

Add and run these exact domain tests RED, then GREEN:

```text
test_be_ddmrp_008_confirmation_lost_response_replay_precedes_freshness_time_and_build
test_be_ddmrp_008_confirmation_request_id_changed_reuse_conflicts_before_authority
test_be_ddmrp_008_unprocessed_confirmation_requires_current_freshness
test_be_ddmrp_008_confirmation_result_graph_drift_fails_closed
test_be_ddmrp_009_confirmation_result_lists_exact_make_child_ids
test_be_ddmrp_008_buy_confirmation_result_has_no_shared_child_ids
test_be_ddmrp_009_confirmation_failure_boundaries_restore_thirteen_ledgers
test_be_ddmrp_009_live_replacement_failure_restores_thirteen_ledgers
```

Run before implementation and repeat the identical `$tests` array after implementation with `pytest-ddmrp-confirmation-domain-green`:

```powershell
$tests = @(
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_008_confirmation_lost_response_replay_precedes_freshness_time_and_build',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_008_confirmation_request_id_changed_reuse_conflicts_before_authority',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_008_unprocessed_confirmation_requires_current_freshness',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_008_confirmation_result_graph_drift_fails_closed',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_009_confirmation_result_lists_exact_make_child_ids',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_008_buy_confirmation_result_has_no_shared_child_ids',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_009_confirmation_failure_boundaries_restore_thirteen_ledgers',
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_009_live_replacement_failure_restores_thirteen_ledgers'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-confirmation-domain-red -p no:cacheprovider
```

Expected RED: 8 selected, 0 passed, 8 failed. Expected GREEN: 8 selected, 8 passed. The lost-response test confirms once, then changes current authority and configures clock/write-set/freshness callbacks to fail if called; exact lookup still returns the original IDs as `Duplicate` with all thirteen collections byte-for-byte unchanged. The changed-reuse case varies reason and recommendation independently and gets conflict. The unprocessed case proves freshness runs and drift prevents every insert. Failure injection covers before shared staging, inside shared apply, after shared copy staging, before result insert, during live replacement, and during `store.save()`.

Commit:

```powershell
git commit -m "feat: atomically confirm DDMRP Make advice"
```

### Activation Task A6: Complete Candidate Planning Run Bridge

**Review/commit boundary:** candidate freeze/transition compatibility.

Extend both public bridge signatures with `planned_manufacturing_candidates`. Add candidate IDs/records to graph metadata, identity fingerprint, drift comparison, and returned transition collections.

Lifecycle:

```text
AwaitingMaterial
  -> AwaitingPlanningRun
  -> FrozenIntoPlanningRun
  -> Scheduled
  -> LinkedToFormalOrder
  -> InExecution
  -> Completed

side states: HeldForPlanningError, AdjustmentRequired, Released, Cancelled
```

- `AwaitingMaterial` is not selectable/freeze-eligible.
- Planning Run creation freezes only `AwaitingPlanningRun` and atomically transitions it to `FrozenIntoPlanningRun` with `PlanningRunID`.
- Completed with exact scheduled occupancy transitions candidate to `Scheduled`, capacity to `ConvertedToScheduledOccupancy`, and leaves material protected until authority handoff.
- Failed/DeadLetter transitions candidate/batch/capacity/material to the existing held behavior without releasing protection.
- MTO/no-candidate graphs and historical graph migration behavior remain compatible.

Tests cite `BE-DDMRP-009` and `BE-RUN-011`, including no-candidate compatibility, candidate drift, missing candidate, AwaitingMaterial rejection, exact schedule conversion, failure hold, recovery, and SQLite restart.

Commit:

```powershell
git commit -m "feat: bridge Make candidates into Planning Runs"
```

### Activation Task A6P: Persist And Bind The Thirteen-Ledger Confirmation Graph

**Review/commit boundary:** activation persistence and app binding only; this task must complete before A7.

**Files after gate:** `sdbr/state_store.py`, `sdbr/api.py`, `tests/test_state_store.py`, and `tests/test_api.py`.

Use exactly these thirteen live `WorkbenchStateStore` fields; reuse existing fields where already present and add only the missing activation fields:

```text
1.  ddmrp_replenishment_recommendations
2.  ddmrp_replenishment_events
3.  ddmrp_confirmation_decisions
4.  ddmrp_active_replenishment_graphs
5.  planned_manufacturing_candidates
6.  planned_manufacturing_candidate_events
7.  planning_demand_commitments
8.  planning_reservation_batches
9.  ccr_capacity_reservations
10. material_planning_allocations
11. planning_reservation_events
12. ddmrp_confirmation_request_results
13. processed_planning_event_keys
```

There is no DDMRP processed-key set. Add all thirteen, with their native dict/list/set type, to `_state_payloads`, SQLite JSON serialization/load, `_apply_payloads`, `_clear`, `_state_counts`, `_snapshot_complete_state`, `_restore_complete_state`, and every save-failure/rollback snapshot. Mapping keys must equal `RecommendationID`, `DecisionID`, `LogicalReplenishmentID`, `PlannedManufacturingCandidateID`, shared canonical IDs, or `ActionRequestID` as applicable. List event IDs must be unique; set values must be strings. Malformed identity or type fails load without normalization.

Keep `SCHEMA_VERSION = 1`: older memory/SQLite payloads with absent activation keys load those collections empty, while existing keys preserve behavior. A save followed by construction of a new `SQLiteWorkbenchStateStore` must restore all thirteen exactly, including tuple/list normalization required by each exact validator.

In `create_app`, bind local variables with those exact thirteen field names and pass the same live objects to confirmation lookup, staging, apply, workbench projection, and Planning Run bridge. No route-local fallback collection is permitted.

Add a lock-owning state-store operation so confirmation replay can precede stale revision rejection without bypassing rollback:

```python
def atomic_replayable_update(
    self,
    *,
    replay_lookup: Callable[[], MutationResult | None],
    mutation: Callable[[], MutationResult],
    expected_revision: int | None = None,
) -> tuple[MutationResult, StateStoreSaveOutcome | None, bool]:
    with self._request_write_lock:
        replayed = replay_lookup()
        if replayed is not None:
            return replayed, None, True
        current_revision = self.current_revision()
        if expected_revision is not None and expected_revision != current_revision:
            raise StateStoreRevisionConflict(
                expected_revision=expected_revision,
                current_revision=current_revision,
            )
        snapshot = self.snapshot_state()
        try:
            result = mutation()
            outcome = self.save()
        except BaseException:
            self.restore_state(snapshot)
            raise
        return result, outcome, False
```

The replay callable may perform only A5 persisted-result lookup/graph validation. On duplicate there is no save, revision increment, clock call, freshness call, or mutation. On an unprocessed action revision is checked before `mutation`, and any `BaseException`, including save failure, restores the complete state.

`SQLiteWorkbenchStateStore` must override that method just as it already overrides `atomic_update`; inheriting the in-memory implementation is forbidden. The override is exact:

```python
def atomic_replayable_update(
    self,
    *,
    replay_lookup: Callable[[], MutationResult | None],
    mutation: Callable[[], MutationResult],
    expected_revision: int | None = None,
) -> tuple[MutationResult, StateStoreSaveOutcome | None, bool]:
    with self._request_write_lock:
        pre_transaction_snapshot = self.snapshot_state()
        authoritative_snapshot: dict[str, object] | None = None
        current_revision = self._revision
        with self._lock:
            connection = sqlite3.connect(self.database_path)
            try:
                connection.execute("BEGIN IMMEDIATE")
                payloads, metadata = self._read_connection_state(connection)
                self._replace_loaded_state(payloads, metadata)
                authoritative_snapshot = self.snapshot_state()
                current_revision = self._revision

                replayed = replay_lookup()
                if replayed is not None:
                    connection.commit()
                    return replayed, None, True

                if (
                    expected_revision is not None
                    and expected_revision != current_revision
                ):
                    raise StateStoreRevisionConflict(
                        expected_revision=expected_revision,
                        current_revision=current_revision,
                    )

                result = mutation()
                saved_at = datetime.now(timezone.utc).isoformat()
                next_revision = current_revision + 1
                self._write_connection_state(
                    connection,
                    saved_at=saved_at,
                    next_revision=next_revision,
                )
                connection.commit()
            except BaseException as error:
                if isinstance(error, StateStoreManagedRequestRejected):
                    error.capture_current_revision(current_revision)
                connection.rollback()
                self.restore_state(
                    authoritative_snapshot or pre_transaction_snapshot
                )
                raise
            finally:
                connection.close()

        outcome = self._committed_outcome(
            saved_at=saved_at,
            next_revision=next_revision,
        )
        return result, outcome, False
```

Thus the SQLite request lock and `BEGIN IMMEDIATE` cover authoritative payload/metadata reload, persisted replay lookup, `If-Match`, mutation, and the write. Exact replay commits the read transaction without calling `_write_connection_state` or `_committed_outcome`; changed request reuse raised by `replay_lookup` is based on the reloaded persisted result and occurs before stale revision comparison. Every exceptional path rolls back SQLite and restores the authoritative in-memory snapshot (or the pre-transaction snapshot if authoritative load itself failed).

Add these exact RED/GREEN tests:

```text
test_be_ddmrp_009_activation_store_memory_snapshot_restore_covers_thirteen_ledgers
test_be_ddmrp_009_activation_store_sqlite_round_trip_covers_thirteen_ledgers
test_be_ddmrp_009_activation_store_loads_legacy_payload_with_absent_activation_keys
test_be_ddmrp_008_confirmation_replay_survives_sqlite_restart
test_be_ddmrp_009_activation_store_rejects_malformed_confirmation_identity
test_be_ddmrp_009_activation_store_save_failure_restores_thirteen_ledgers
test_be_ddmrp_009_create_app_binds_same_thirteen_live_ledgers
test_be_ddmrp_008_atomic_replayable_update_checks_replay_before_if_match_and_save
```

Run all eight exact nodes before implementation: expected RED 8 selected/8 failed. Run the identical nodes after implementation: expected GREEN 8 selected/8 passed. The restart replay test opens a new app/store, retries the same `ActionRequestID`, and asserts exact duplicate IDs with no count/revision change. The malformed test covers decision, candidate, event, and request-result identities. The save-failure and API rollback tests compare all thirteen collections byte-for-byte.

Commit:

```powershell
git commit -m "feat: persist DDMRP confirmation graphs"
```

### Activation Task A7: Planner Confirmation API, RBAC, Audit, And Retry

**Review/commit boundary:** API only.

Exact request model:

```python
class DdmrpRecommendationConfirmPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ActionRequestID: str = Field(min_length=1)
    Reason: str = Field(min_length=1, max_length=500)
```

No action type, actor, confirmation time, target, BOM, capacity, or material override is accepted. Authentication supplies actor through `_effective_actor_id(request, "local-planner")` for request fingerprinting. Only an unprocessed action later reads advice from the accepted recommendation and captures time through `server_utc_now()`.

Mark only `POST /planner/workbench/ddmrp/recommendations/{recommendation_id}/confirm` as store-managed in `persist_successful_writes`, using an exact method plus full-path-shape predicate rather than a DDMRP prefix exemption. All neighboring DDMRP writes remain under generic middleware admission, `If-Match`, save, and rollback. The confirmation route must call `active_store.atomic_replayable_update(...)`; every success, duplicate, controlled 409, and revision-conflict return sets `request.state.store_managed_revision` from the returned outcome or store-boundary exception before middleware emits `X-Workbench-Revision`. Compute authenticated actor and this request fingerprint without reading current authority or capturing time:

```python
request_fingerprint = canonical_fingerprint(
    {
        "ActionRequestID": payload.ActionRequestID,
        "RecommendationID": recommendation_id,
        "Reason": payload.Reason,
        "ActorID": actor_id,
    }
)
```

The `replay_lookup` callback performs only:

```python
return lookup_ddmrp_confirmation_request_result(
    action_request_id=payload.ActionRequestID,
    request_fingerprint=request_fingerprint,
    ledgers=ddmrp_composite_ledgers,
)
```

If an immutable result exists, changed request reuse returns 409; exact graph validation returns `Duplicate` before `If-Match`, current recommendation/authority lookup, `server_utc_now()`, write-set build, or freshness comparison. The duplicate branch performs no save and returns the current revision header. Only when lookup returns `None` may `atomic_replayable_update` validate `If-Match` and invoke `mutation`.

The route invocation is exactly:

```python
result, outcome, replayed = active_store.atomic_replayable_update(
    replay_lookup=replay_lookup,
    mutation=mutation,
    expected_revision=_client_revision_from_if_match(
        request.headers.get("if-match")
    ),
)
request.state.store_managed_revision = (
    active_store.current_revision() if replayed else outcome.revision
)
```

`outcome` is non-null when `replayed` is false. Catch `_StoreManagedRequestRejected` and `StateStoreRevisionConflict` outside this call, set `request.state.store_managed_revision = error.current_revision`, and return the existing structured 409 mapping. Middleware never performs a second save for this exact route and never exempts another method or path.

The unprocessed `mutation` order is exact: (1) load the current immutable recommendation and require `AdviceType in {"Buy", "Make"}` plus `PendingReview`; (2) load current accepted runtime/config/advice/BOM/material/capacity and V2 local-ledger authority; (3) capture one server UTC time; (4) build current signature, feasibility, decision, exact confirmation result, and composite write set; (5) call `assert_ddmrp_confirmation_fresh`; (6) stage/apply all thirteen collections; (7) let `atomic_replayable_update` save. Any authority drift conflicts before mutation, and complete rollback covers staging/apply/save failure.

Exact response wrapper:

```python
{
    "Endpoint": endpoint,
    "StatusCode": 200,
    "Data": {
        "Status": "Confirmed" | "Duplicate",
        "RecommendationID": recommendation_id,
        "ConfirmedAction": server_recommendation["AdviceType"],
        "DecisionID": decision_id,
        "PlanningObjects": None | {
            "PlannedManufacturingCandidateID": candidate_id,
            "ReservationBatchID": batch_id,
            "CapacityReservationIDs": capacity_ids,
            "MaterialAllocationIDs": material_ids,
            "DependentRecommendationIDs": dependent_ids,
        },
        "ExternalOrderCreated": False,
        "Workbench": workbench,
    },
}
```

Tests cover Viewer/Worker denial, Planner/Admin success, server actor/time, stable action replay after lost response, `If-Match`, every authority drift, active-graph conflict, save rollback, and public-demo denial.

Add these specifically named API RED tests before the route and run the identical selection GREEN afterward:

```text
test_be_ddmrp_008_confirmation_api_lost_response_retry_replays_before_stale_if_match
test_be_ddmrp_008_confirmation_api_lost_response_retry_skips_authority_time_build_and_freshness
test_be_ddmrp_008_confirmation_api_changed_action_request_reuse_returns_409_first
test_be_ddmrp_008_confirmation_api_unprocessed_action_enforces_if_match_and_freshness
test_be_ddmrp_008_confirmation_api_exact_response_and_buy_make_only_action
test_be_ddmrp_008_confirmation_api_uses_server_actor_time_and_reason
test_be_ddmrp_008_confirmation_api_viewer_worker_denied_planner_admin_allowed
test_be_ddmrp_008_confirmation_api_public_demo_denied_without_mutation
test_be_ddmrp_009_confirmation_api_make_returns_exact_child_ids
test_be_ddmrp_009_confirmation_api_save_failure_restores_thirteen_ledgers
test_be_ddmrp_008_confirmation_api_sqlite_two_store_stale_duplicate_precedes_if_match_without_revision_increase
test_be_ddmrp_008_confirmation_api_sqlite_two_store_changed_reuse_returns_409_from_authoritative_result
```

Use this exact selection before implementation, then repeat it with basetemp `pytest-ddmrp-confirmation-api-green` after implementation:

```powershell
$tests = @(
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_lost_response_retry_replays_before_stale_if_match',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_lost_response_retry_skips_authority_time_build_and_freshness',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_changed_action_request_reuse_returns_409_first',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_unprocessed_action_enforces_if_match_and_freshness',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_exact_response_and_buy_make_only_action',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_uses_server_actor_time_and_reason',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_viewer_worker_denied_planner_admin_allowed',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_public_demo_denied_without_mutation',
  'tests/test_api.py::test_be_ddmrp_009_confirmation_api_make_returns_exact_child_ids',
  'tests/test_api.py::test_be_ddmrp_009_confirmation_api_save_failure_restores_thirteen_ledgers',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_sqlite_two_store_stale_duplicate_precedes_if_match_without_revision_increase',
  'tests/test_api.py::test_be_ddmrp_008_confirmation_api_sqlite_two_store_changed_reuse_returns_409_from_authoritative_result'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-confirmation-api-red -p no:cacheprovider
```

Expected RED: 12 selected, 0 passed, 12 failed. Expected GREEN: 12 selected, 12 passed. The first test sends the original `If-Match` again after the successful response is discarded and requires 200 `Duplicate`, identical decision/planning IDs, unchanged thirteen-ledger counts, and no revision increment. The second uses raising spies for authority, clock, build, and freshness. Changed reuse varies reason/actor/recommendation and requires 409 before those same spies.

The two SQLite tests each create `first_store` and `stale_store` from the same database before the first client confirms. The stale client then sends the original pre-commit `If-Match`: the exact-request case must return 200 `Duplicate` from the authoritative persisted result, preserve the committed revision and all thirteen persisted counts, and prove its mutation callback was not entered; the changed-`Reason` case must return structured 409 `ACTION_REQUEST_ID_REUSED` from that authoritative result before stale `If-Match`, with no write or revision increase. Both tests reconstruct a third store afterward to assert the database revision and graph are unchanged. Record exact selected/pass counts and run the activation state-store/domain regression separately. The existing exact-response test also asserts only the confirmation POST matches the store-managed middleware predicate and that an adjacent DDMRP write still uses generic persistence.

Commit:

```powershell
git commit -m "feat: confirm authorized DDMRP recommendations"
```

### Activation Task A8: UI-DDMRP-004 Confirmation Unit

**Review/commit boundary:** read rendering and action handling are separate commits.

Use existing `showNotification`, `confirmAction`, and `{Endpoint, StatusCode, Data}` parsing. Declare one retained request object:

```javascript
let pendingMaterialConfirmation = null;
let materialConfirmationInFlight = false;
```

The client never sends `ActionType`, actor, or time. Generate `crypto.randomUUID()` once per selected recommendation and retain it across network retry until success or authoritative reconciliation. Send only `ActionRequestID` and planner-entered `Reason`, with `If-Match: materialPlanningRevision`. Disable duplicate submission while pending.

The confirmation dialog must display server-returned quantity/UOM, `StandardTargetReceiptAt`, advice, candidate status, CCR minutes/windows, material coverage/shortage, and the explicit no-external-order boundary. It performs no calculations. Blocked, superseded, adjustment-required, confirmed, or stale rows have no active confirm button.

Add a specifically named `test_ui_ddmrp_004_...` selector, `node --check`, API contract tests parsing real wrappers, and browser checks at 1280x720, 1920x1080, and 390x844. After verification, update the then-current UI spec, mark `UI-DDMRP-004` `已验证待用户确认`, and stop for explicit confirmation.

---

## Exact Per-Test Traceability

| Test file | Required module-level evidence text |
| --- | --- |
| `tests/test_ddmrp.py` | `BE-DDMRP-003, BE-DDMRP-004, BE-DDMRP-005, BE-DDMRP-007` |
| `tests/test_ddsop_runtime_planning_input.py` | `BE-DDMRP-007, BE-INT-008` |
| `tests/test_ddmrp_replenishment.py` | NOW: `BE-DDMRP-007`; activation sections: `BE-DDMRP-008, BE-DDMRP-009` |
| `tests/test_ddmrp_replenishment_view.py` | `BE-DDMRP-007, UI-DDMRP-003`; later add `BE-DDMRP-008, BE-DDMRP-009, UI-DDMRP-004` |
| `tests/test_state_store.py` | NOW additions: `BE-DDMRP-007`; candidate additions: `BE-DDMRP-009, BE-RUN-011` |
| `tests/test_test_data.py` | `BE-DDMRP-007, UI-DDMRP-003` |
| `tests/test_ddmrp_browser_acceptance_app.py` | `BE-DDMRP-007, UI-DDMRP-003` |
| `tests/test_ddmrp_feasibility.py` | `BE-DDMRP-009, BE-SDBR-008, BE-SDBR-009` for BOM/material/CCR preview and dependent Buy/Make cases. |
| `tests/test_api.py` | Each NOW test comments `BE-DDMRP-007` and/or `UI-DDMRP-003`; activation tests comment `BE-DDMRP-008`, `BE-DDMRP-009`, `BE-SDBR-006` through `009`, `BE-RUN-011`, `UI-DDMRP-004`, and RBAC `BE-OPS-001` as applicable. |
| `tests/test_planning_commitments.py` | `BE-SDBR-006, BE-DDMRP-008` for stable MTA source identity cases. |
| `tests/test_planning_reservations.py` | `BE-SDBR-007, BE-SDBR-008, BE-SDBR-009, BE-DDMRP-009` for candidate/composite cases. |
| `tests/test_planning_reservation_view.py` | `BE-SDBR-008, BE-SDBR-009, BE-DDMRP-009` for feasibility projections. |
| `tests/test_planning_run_reservation_bridge.py` | `BE-RUN-011, BE-DDMRP-009` for candidate freeze/transition cases. |

Do not rely on a global plan statement in place of these edits.

## Final Verification Matrix

| Capability/invariant | NOW evidence | Activation evidence required later | Claim after NOW |
| --- | --- | --- | --- |
| Authority inventory quantity | Contract-validated tests consume `AvailableQty` for all valid quality states. | Source-authoritative material snapshot for writes. | Verified read-only consumption only. |
| DLT target | Null target plus `DLT_TARGET_SEMANTICS_INSUFFICIENT`. | Accepted policy/calendar/time tests. | Explicitly blocked. |
| Runtime/config freshness | Complete IDs/fingerprints in immutable signature. | Confirmation compares runtime/config plus advice/BOM/material/capacity/local ledger current signatures. | Evaluation traceability only. |
| Advice/BOM authority | Null authority slots and contract gates; API rejects raw authority extras. | Contract Agent-accepted consumers and dispatch. | Explicitly blocked. |
| Stable replenishment identity | Chain/cycle/version/supersession/adjustment tests. | Evaluate-confirm-reevaluate-confirm end-to-end guard. | Versioned read model, no active graph. |
| Public demo isolation | Public-demo package remains read-only and `OperationalActionAllowed=False`. | Same negative test on confirmation route/composite apply. | No operational mutation. |
| Evaluation atomicity | Copy staging, exact replay, state-store rollback. | Composite copy staging across DDMRP/shared ledgers. | Evaluation writes only. |
| Candidate/reservations | No records/endpoints/UI controls. | BOM/material/CCR preview, candidate write set, Planning Run bridge. | Not started. |
| RBAC/audit/retry | Evaluation POST uses Planner/Admin, server actor/time, stable request replay. | Confirmation repeats these rules with retained UUID and impact confirmation. | Read-only/evaluation action only. |
| UI | Wrapper-accurate gated workbench at 1280, 1920, 390; explicit user gate. | Separate `UI-DDMRP-004` acceptance and confirmation stop. | UI-DDMRP-003 only. |
| Regression | Focused and full pytest, compile, Node, diff checks. | Same plus shared reservation/bridge and browser action tests. | No closure claim. |

## Explicit Non-Claims

After the NOW tranche, the implementation must state all of the following:

- DDMRP runtime replenishment closure is **not complete**.
- `BE-DDMRP-008`, `BE-DDMRP-009`, and `UI-DDMRP-004` are not implemented or verified.
- No accepted ERP/MRP Buy/Make advice contract is consumed.
- No accepted Plan BOM/multilevel feasibility contract is consumed.
- `StandardTargetReceiptAt` is not calculated.
- No planner confirmation, formal purchase/production/transfer order, external delivery, ACK, retry, or dead-letter flow exists.
- No planned manufacturing candidate, CCR reservation, or material planning allocation is created by DDMRP.
- Public-demo/reviewed fixtures never affect operational shared ledgers.
- No DDAE parameter governance, Buffer Profile editing, adjustment-factor approval, substitute/batch/lot/expiry logic, automatic schedule/release change, Gurobi execution, or expanded Simio behavior is added.
- The remaining external gate is exactly `CONTRACT-GATE-DDMRP-ACTIVATION-001` as defined above.

## Plan Self-Review Commands

Before handing this plan to an executing agent, run:

```powershell
$planPath = 'docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md'
rg -n "lookup_ddmrp_confirmation_request_result|atomic_replayable_update|assert_ddmrp_confirmation_fresh|ACTION_REQUEST_ID_REUSED|ddmrp_confirmation_request_results" $planPath
rg -n "CANDIDATE_COUNTED_STATUSES|FORMAL_SUPPLY_COUNTED_STATUSES|gross_replenishment_need_qty|adjustment_delta_qty|material allocations" $planPath
rg -n "EVENT_PAYLOAD_FIELDS_BY_TYPE|ISSUE_RECORD_FIELDS|CreatedLogicalReplenishmentIDs|ReusedLogicalReplenishmentIDs|EvaluationAt" $planPath
rg -n "test_be_ddmrp_007_seeded_read_only_replenishment_workbench_is_reproducible|seeded|empty|error|403|409|browser-report\.md|test_ddmrp_feasibility" $planPath
$forbiddenPatterns = @(
  ('ddmrp' + '_keys'),
  ('Issue' + 'Codes'),
  ('"Source' + 'Type"'),
  ('stage_ddmrp_confirmation' + '\(')
)
foreach ($pattern in $forbiddenPatterns) {
  if (Select-String -LiteralPath $planPath -Pattern $pattern) { throw "Forbidden legacy plan pattern: $pattern" }
}
$lines = Get-Content -LiteralPath $planPath
$activationStart = [Array]::IndexOf($lines, '## BLOCKED-ACTIVATION Blueprint')
$traceabilityStart = [Array]::IndexOf($lines, '## Exact Per-Test Traceability')
$deferredActionPattern = '(?i)' + ('trans' + 'fer')
if (($lines[$activationStart..($traceabilityStart - 1)] -join "`n") -match $deferredActionPattern) { throw 'Deferred action leaked into activation implementation.' }
$fenceCount = (Select-String -LiteralPath $planPath -Pattern '^```').Count
if (($fenceCount % 2) -ne 0) { throw "Unbalanced Markdown fences: $fenceCount" }
rg -n "InspectionHold|notify\(|ConfirmedBy:|ConfirmedAt:|PlanningAdviceLines" $planPath
git diff --check
```

Expected: required-contract scans are non-empty; forbidden legacy key/code/source-field/confirmation-entry patterns and request/body scans are empty; the activation-range deferred-action check and even-fence check do not throw; diff check exits 0.
