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
| M3 browser reproducibility | Task 11 fixes the seed, database, port, hidden process, health check, shutdown, evidence paths, and 1280/1920/390 viewports. |
| M4 spec versions/date | `2.80 -> 2.81` and `5.35 -> 5.36`, all dated `2026-07-11`, are exact and justified. |
| M5 global-only traceability | The per-test table at the end requires module/test-level BE/UI edits in every touched test file. |
| Round-2 I1 NOW replay/global revision | Task 3 replaces the global store revision with a canonical DDMRP-relevant planning-ledger identity. Tasks 4/5 persist an immutable request-result record, and Task 8 performs exact lookup/graph validation before rebuilding. |
| Round-2 I2 strict model/runtime time | Task 8 imports `ConfigDict`/`TypeAdapter`, forbids request extras, parses `RuntimeEvidenceSnapshot.SnapshotAt` as `AwareDatetime`, and passes that same value to calculation and immutable records. |
| Round-2 I3 activation freshness/replay | The signature includes target-policy ID/version/fingerprint and calendar version. A5 verifies exact persisted replay before freshness; freshness remains mandatory for an unprocessed action. |
| Round-2 I4 identity/execution facts | Task 4 hashes canonical structured JSON and tests delimiter-shaped identifiers. Gated A3 defines candidate/formal-supply handoff, cancellation, allocation, residual, and signed adjustment-delta semantics while preserving the active-graph guard. |
| Round-2 I5 exact lifecycle/projections/persistence | Tasks 4/5 define immutable field sets, fingerprints, folds, terminal/active sets, and orphan rejection; Task 7 fixes every nested allowlist; gated A6 persists and binds every composite ledger before any confirmation API. |
| Round-2 I6 RED/GREEN evidence | Every NOW task that adds tests has matching exact-node RED/GREEN commands, an expected RED reason, and explicit selected/pass counts. |
| Round-2 M1 browser reproducibility | Tasks 9/11 add tested acceptance-only seeded/empty/error/403/409 modes, exact case lookup, a port check, bounded health polling, and `try/finally` shutdown. |
| Round-2 M2 traceability | The final table includes `tests/test_ddmrp_feasibility.py`, per-test API comments, and NOW/activation RBAC coverage of `BE-OPS-001`. |
| Round-2 M3 Transfer boundary | Transfer is explicitly deferred in Task 1, the closed gate, A2/A8, the traceability matrix, and the non-claims; no accepted Transfer authority is implied. |

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
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_rejects_runtime_spike_without_accepted_threshold_authority'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-signature-red -p no:cacheprovider
```

Expected RED: 7 selected, 0 passed, 7 failed. The first six fail on the missing module/symbols and the last fails because the adapter does not yet reject unqualified local spike calculation. Record the actual counts.

- [ ] **Step 3: Add exact immutable types and canonical projection field sets**

```python
from copy import deepcopy
from dataclasses import dataclass
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
) -> tuple[DdmrpAuthoritySignature, tuple[DdmrpGate, ...]]:
```

Re-check the package/config IDs and `canonical_operating_model_fingerprint(...)` exactly as in the prior revision. Hash the accepted package payload and parameter evidence. Construct `base` with all target policy/calendar, advice, BOM, material-authority, and capacity-authority fields set to `None`, and copy these three local values without consulting the store revision:

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
  'tests/test_ddsop_runtime_planning_input.py::test_be_ddmrp_007_rejects_runtime_spike_without_accepted_threshold_authority'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-signature-green -p no:cacheprovider
```

Expected GREEN: 7 selected, 7 passed, 0 failed. Record the actual count, then commit:

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
test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_and_illegal_status_transitions
```

The adversarial test compares at least `("A|B", "C", 1)` with `("A", "B|C", 1)`, plus JSON-looking identifiers such as `('{"x":1}', '[x]', 2)`, and proves every structured identity and ID differs. NOW recommendations assert `AdviceType is None`, `StandardTargetReceiptAt is None`, `InitialStatus == "Blocked"`, and all four gate codes. Green/AboveGreen appear only as zero-quantity monitor rows.

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
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_and_illegal_status_transitions'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-builder-red -p no:cacheprovider
```

Expected RED: 9 selected, 0 passed, 9 failed because the builder, exact schemas, canonical identity, and fold helpers do not exist. Record actual counts.

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
    "SupplyID", "SupplyQty", "ExpectedAt", "Status", "Uom", "SourceType",
)
GATE_FIELDS = ("Code", "Message", "BlocksOperationalAction")
EVALUATION_RUN_FIELDS = (
    "EvaluationID", "EvaluationRequestID", "EvaluationAt", "RecordedAt", "RecordedBy",
    "EvaluationMode", "RuntimePlanningInputPackageID",
    "RuntimePlanningInputPackageVersion", "RuntimeSnapshotID",
    "OperatingModelConfigurationID", "OperatingModelFingerprint",
    "DDMRPConfigurationID", "AuthoritySignature", "AuthoritySignatureFingerprint",
    "RelevantPlanningLedgerIdentity", "RelevantPlanningLedgerFingerprint",
    "Summary", "IssueCodes", "OperationalActionAllowed", "EvaluationFingerprint",
)
EVALUATION_ROW_FIELDS = (
    "EvaluationRowID", "EvaluationID", "RowKey", "ItemID", "LocationID", "Uom",
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
    "RecommendationIDs", "EventIDs", "EvaluationPayloadFingerprint",
    "ResponseData", "ResponseFingerprint", "RecordedAt", "RecordedBy",
    "RequestResultFingerprint",
)
RESPONSE_DATA_FIELDS = (
    "Status", "EvaluationID", "RecommendationIDs", "OperationalActionAllowed",
)
```

`AuthoritySignature` must have exactly Task 3's key set. `Summary`, demand/supply components, gates, `ResponseData`, and each event type's payload must have exactly their named allowlists. Reject missing or extra keys before fingerprinting. No record contains `Payload`, a package/config body, evidence refs, raw authority rows, or a mutable nested object borrowed from a caller.

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
```

Use prefixes `DDE`, `DER`, `DRL`, `DDR`, and `DRE` for evaluation, row, chain, recommendation, and event IDs. `RowKey` is canonical JSON for `{ItemID, LocationID}`. Every record fingerprint is `canonical_fingerprint` over its exact fields excluding only its own `*Fingerprint` field. Event `PayloadFingerprint` covers the exact `EventPayload`. The write-set `payload_fingerprint` covers sorted `EvaluationRun`, `EvaluationRows`, `ChainRecords`, `RecommendationVersions`, and `Events`; it deliberately excludes `request_result` to avoid a cycle. `RequestResultFingerprint` covers all request-result fields except itself, and `ResponseFingerprint` covers exact `ResponseData`. `EvaluationPayloadFingerprint` in the result equals the write-set fingerprint.

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
RECOMMENDATION_TRANSITIONS = {
    "Blocked": frozenset({"PendingReview", "Superseded"}),
    "PendingReview": frozenset({"Confirmed", "Rejected", "Superseded"}),
    "Confirmed": frozenset({"AdjustmentRequired", "Issued", "Released", "Cancelled"}),
    "Issued": frozenset({"ERPAccepted", "OutputFailed", "AdjustmentRequired", "Cancelled"}),
    "OutputFailed": frozenset({"Issued", "AdjustmentRequired", "Cancelled"}),
    "ERPAccepted": frozenset({"InExecution", "AdjustmentRequired", "Cancelled"}),
    "InExecution": frozenset({"Completed", "AdjustmentRequired", "Cancelled"}),
    "AdjustmentRequired": frozenset({"Released", "Cancelled"}),
}
```

`fold_recommendation_status(...)` groups events by `AggregateID`, sorts by positive integer `AggregateVersion`, requires versions `1..N` without gaps or duplicates, requires event `StatusBefore` to equal the current fold, and applies only `RECOMMENDATION_TRANSITIONS`. `fold_chain_status(...)` applies the same rules to `Open -> ActiveGraph | AdjustmentRequired | Released | Cancelled | Completed`, `ActiveGraph -> AdjustmentRequired | Released | Cancelled | Completed`, and `AdjustmentRequired -> Released | Cancelled | Completed`. Terminal states accept no later transition. For latest-version selection, reject duplicate versions, predecessor gaps, multiple successors, a missing reverse supersession event, multiple non-terminal chains for one item/location, an active graph attached to a terminal chain, or a graph whose mapping key differs from `LogicalReplenishmentID`.

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

Require timezone-aware `recorded_at`, non-empty actor/request ID, `runtime_result["EvaluatedAt"] == authority_signature.runtime_snapshot_at`, and exact runtime line/component schemas. Reuse the sole non-terminal chain; otherwise use `max(prior CycleNumber)+1`. Increment the recommendation version, name its predecessor, and emit reciprocal `RecommendationSuperseded`/`RecommendationVersionCreated` events without mutating old records. If the active-graph registry contains the chain, create only `InitialStatus="AdjustmentRequired"` with `AdjustmentOfRecommendationID`; otherwise NOW Red/Yellow is `Blocked`. Freeze deep copies of the complete signature on the run and each recommendation. Produce one immutable request result with `ResponseData.Status="Created"`. Never create a recommendation for Green/AboveGreen.

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
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_event_fold_rejects_gaps_duplicates_and_illegal_status_transitions'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-builder-green -p no:cacheprovider
```

Expected GREEN: 9 selected, 9 passed, 0 failed. Record the count, then:

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
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_request_result_with_missing_or_extra_child_fails_closed'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-apply-red -p no:cacheprovider
```

Expected RED: 8 selected, 0 passed, 8 failed because lookup/staging/orphan contracts are absent. Record actual counts.

- [ ] **Step 3: Implement immutable lookup before any rebuild**

```text
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
) -> dict[str, object] | None
```

If no mapping exists, return `None` without reading current authority or building an evaluation. If a mapping exists, require its mapping key and exact `REQUEST_RESULT_FIELDS`, recompute `RequestResultFingerprint`, compare `request_fingerprint` first, and return 409 conflict on changed request reuse. Then `_validate_persisted_evaluation_result_graph(...)` must prove:

- the exact evaluation, row, chain, recommendation, and event ID sets equal the result record lists, with no missing or extra child;
- every mapping key equals the child's canonical ID and every child/nested fingerprint recomputes;
- each child points back to the result's evaluation/request/chain as applicable;
- the write-set payload reconstructed from persisted children equals `EvaluationPayloadFingerprint`;
- exact `ResponseData` and `ResponseFingerprint` match those IDs and `OperationalActionAllowed=False`.

Only after all checks return a deep-copied response with `Status="Duplicate"`. Persisted `ResponseData` remains `Status="Created"`; replay never rewrites history. Any drift is a conflict, not a repair.

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

Next call `lookup_ddmrp_evaluation_request_result(...)` against the copies. Exact replay returns a `Duplicate` staged state unchanged. Changed reuse conflicts. For an unprocessed request, **any** pre-existing target child/event ID, equal or different, is `ORPHAN_DDMRP_EVALUATION_CHILD` and fails closed; no `setdefault` adoption is allowed. Validate chain uniqueness/folds against the combined prospective copies, insert all children/events, and insert the immutable request result last. There is no independent processed key that can drift away from its result.

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
  'tests/test_ddmrp_replenishment.py::test_be_ddmrp_007_request_result_with_missing_or_extra_child_fails_closed'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-evaluation-apply-green -p no:cacheprovider
```

Expected GREEN: 8 selected, 8 passed, 0 failed. Record the count, then:

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

Validate all Task 4 immutable fields/fingerprints/folds before projection. Reject duplicate canonical IDs, mapping-key mismatches, orphan recommendations/events/graphs, multiple current versions, and active graphs on terminal chains. Return a deep copy with exactly these top-level keys:

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

`DemandComponents`, `SupplyComponents`, and gate dictionaries use Task 4's exact nested fields. `Rows` sort by `(PlanningStatus rank, BufferPercent, ItemID, LocationID)`; `ActiveGraphs` by `(ItemID, LocationID, LogicalReplenishmentID)`; `History` by `(ItemID, LocationID, RecommendationVersion, RecommendationID)`; nested events by `(AggregateVersion, EventID)`; issues by `(Severity, Code, ItemID or "", LocationID or "")`. Empty state returns the same eight top-level keys, `Evaluation=None`, zeroed exact summary, empty lists, the exact boundary, and an empty exact technical object.

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
test_be_ddmrp_007_evaluation_api_uses_snapshot_at_for_calculation_and_evaluation_record
test_be_ddmrp_007_evaluation_api_rejects_naive_or_invalid_snapshot_at
test_be_ddmrp_007_evaluation_api_public_demo_is_read_only
test_be_ddmrp_007_workbench_api_uses_standard_wrapper_and_safe_shape
test_be_ddmrp_007_write_revision_and_save_failure_restore_every_ledger
test_be_ddmrp_007_ddmrp_routes_enforce_viewer_planner_admin_rbac
test_be_ddmrp_007_unrelated_workbench_write_does_not_change_relevant_ledger_identity
```

The lost-response test performs a successful POST, discards that response, proves the store saved once, then repeats the identical body after that mutation and expects `Data.Status == "Duplicate"`, the same IDs/result, and unchanged DDMRP child/request-result counts. It must not reuse a stale `If-Match`; the separate revision test owns stale-revision behavior. The changed-package test reuses the same request ID and expects 409 before any package calculation.

- [ ] **Step 3: Run exact RED**

```powershell
$tests = @(
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_references_stored_validated_package_only',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_rejects_raw_authority_fields_with_422',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_uses_server_actor_and_server_time',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_lost_response_retry_returns_duplicate_after_save',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_request_id_reuse_with_different_package_returns_409',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_uses_snapshot_at_for_calculation_and_evaluation_record',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_rejects_naive_or_invalid_snapshot_at',
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_public_demo_is_read_only',
  'tests/test_api.py::test_be_ddmrp_007_workbench_api_uses_standard_wrapper_and_safe_shape',
  'tests/test_api.py::test_be_ddmrp_007_write_revision_and_save_failure_restore_every_ledger',
  'tests/test_api.py::test_be_ddmrp_007_ddmrp_routes_enforce_viewer_planner_admin_rbac',
  'tests/test_api.py::test_be_ddmrp_007_unrelated_workbench_write_does_not_change_relevant_ledger_identity'
)
pytest @tests -q --basetemp .tmp/pytest-ddmrp-api-red -p no:cacheprovider
```

Expected RED: 12 selected, 0 passed, 12 failed because routes/model/bindings do not exist. Record actual counts.

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
            "Workbench": build_ddmrp_replenishment_workbench(...),
        },
    }
```

The actual call supplies the same six view arguments shown in Step 7; the ellipsis above is only to avoid duplicating that already exact call. This branch does not look up/re-hash the runtime package, configuration, relevant planning ledger, or server time. Persisted graph/result validation occurs inside lookup. Changed request reuse conflicts. This ordering is mandatory for lost-response correctness.

- [ ] **Step 6: Parse authoritative `SnapshotAt` once and show every route argument**

For an unprocessed request, look up `payload.RuntimePlanningInputPackageID` in `ddsop_runtime_planning_input_packages`, require stored `ProcessingStatus == "Accepted"`, resolve `package_record["OperatingModelConfigurationID"]` in `operating_model_configurations`, and reject missing references with 404. Do not process request-body rows.

Parse the stored nested timestamp exactly once:

```python
package_payload = package_record.get("Payload")
runtime_snapshot = (
    package_payload.get("RuntimeEvidenceSnapshot")
    if isinstance(package_payload, Mapping)
    else None
)
try:
    evaluated_at = _AWARE_DATETIME_ADAPTER.validate_python(
        runtime_snapshot["SnapshotAt"]
    )
except (KeyError, TypeError, ValidationError) as error:
    raise DdmrpReplenishmentConflict(
        "RUNTIME_SNAPSHOT_AT_INVALID: stored SnapshotAt must be timezone-aware."
    ) from error
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

Assert `runtime_result["EvaluatedAt"]`, `authority_signature.runtime_snapshot_at`, evaluation `EvaluationAt`, and every row's evaluation time all equal `evaluated_at.isoformat()`; only `RecordedAt` uses server time. The route never uses server time for overdue/today/spike/open-supply qualification. Let middleware own admission, save, and complete state rollback.

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
  'tests/test_api.py::test_be_ddmrp_007_evaluation_api_uses_snapshot_at_for_calculation_and_evaluation_record',
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

Expected GREEN: exact selection 12 passed; regression selection has a non-zero recorded passing count; compile exits 0. Then:

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

- [ ] **Step 1: Write failing seed/API test**

Add `test_be_ddmrp_007_seeded_read_only_replenishment_workbench_is_reproducible` with module traceability `BE-DDMRP-007 / UI-DDMRP-003`. Reset a temporary SQLite DB, call GET workbench, and assert Red/Yellow blocked rows, Green/Above monitor rows, null target, `PendingReviewCount == 0`, and no active graph.

- [ ] **Step 2: Extend the existing seed, not a new hidden data path**

Add a versioned case catalog entry and seed the new ledgers using the public DDMRP domain builders. Its authority signature has all activation-only refs `None`, `scenario_label="DemoFixture"`, `mapping_confidence="PublicDemoOnly"`, and all four gates. Do not seed a fake accepted advice/BOM/production package.

- [ ] **Step 3: Run and commit**

```powershell
pytest tests/test_test_data.py tests/test_api.py -q -k "seeded_read_only_replenishment or be_ddmrp_007_workbench" --basetemp .tmp/pytest-ddmrp-seed -p no:cacheprovider
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

### Task 11: NOW Verification, Spec Evidence, Browser Matrix, And Stop

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`
- Optional ignored local evidence: `.tmp/ddmrp-ui-acceptance/`

- [ ] **Step 1: Run focused and full automated verification**

```powershell
python -m compileall -q sdbr
node --check sdbr/web/planner-workbench.js
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_ddmrp_replenishment.py tests/test_ddmrp_replenishment_view.py tests/test_state_store.py tests/test_test_data.py tests/test_api.py -q --basetemp .tmp/pytest-ddmrp-readonly-focused -p no:cacheprovider
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

Expected: reset summary names the temporary DB and includes `TST-DDMRP-REPLENISHMENT-READONLY-20260711`.

- [ ] **Step 3: Start/health-check the app reproducibly**

```powershell
$server = Start-Process python -ArgumentList '-m','uvicorn','sdbr.api:app','--host','127.0.0.1','--port','8011' -PassThru -WindowStyle Hidden
Invoke-RestMethod 'http://127.0.0.1:8011/planner/workbench/state-store/health'
```

Use the in-app browser at `http://127.0.0.1:8011/planner/workbench#material-planning`. Capture:

```text
.tmp/ddmrp-ui-acceptance/1280x720.png
.tmp/ddmrp-ui-acceptance/1920x1080.png
.tmp/ddmrp-ui-acceptance/390x844.png
```

At all three widths verify wrapper-loaded data, Red/Yellow blocked rows, Green/Above monitor rows, null target with business gate text, collapsed technical details, search/filter/sort/history, Chinese/English, loading/empty/error/403/409 states, keyboard focus, and no page-level horizontal overflow. Verify there is no confirm control.

Stop the exact process:

```powershell
Stop-Process -Id $server.Id
```

- [ ] **Step 4: Record exact 2.81 / 5.36 evidence**

Set backend header/changelog to `2.81 / 2026-07-11`; mark only `BE-DDMRP-007` `[VERIFIED]` with exact `C/A/T/R` evidence and actual counts. Keep `BE-DDMRP-008`/`009` `[NOT-STARTED]` and name the gate.

Set UI header/changelog to `5.36 / 2026-07-11`; mark only `UI-DDMRP-003` `已验证待用户确认` with all three viewport evidence paths and actual test counts. Keep `UI-DDMRP-004` `未开始`.

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

Required tests cite `BE-DDMRP-009`, `BE-SDBR-008`, and `BE-SDBR-009`: BOM cycle, missing/expired BOM version, missing UOM/conversion authority, invalid quantity, decoupling stop, non-decoupled Make recursion, Buy/Transfer child advice, required-vs-allocated quantity, `uncommitted_supply_qty(...)`, duplicate supply prevention, CCR role/calendar/window validity, `reservation_load_by_bucket(...)`, over-capacity, shortage, `AwaitingMaterial`, non-release, and recalculated feasible completion/capacity window. Preview records freeze all authority IDs/fingerprints and remain read-only.

Commit:

```powershell
git commit -m "feat: preview DDMRP Make feasibility"
```

### Activation Task A3: Immutable Decision And Active-Graph Governance

**Review/commit boundary:** recommendation/decision lifecycle; no shared apply.

Recommendation core records remain immutable; events derive state. Exact states:

```text
Blocked -> PendingReview -> Confirmed
PendingReview -> Rejected | Superseded
Confirmed -> AdjustmentRequired | Issued | Released | Cancelled
Issued -> ERPAccepted | OutputFailed | AdjustmentRequired
ERPAccepted -> InExecution -> Completed
```

Only `PendingReview` can be confirmed. An active graph forces reevaluation output to `AdjustmentRequired`; it never creates a second confirmable graph. The stable shared demand identity is:

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
```

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

Candidate initial status is `AwaitingMaterial` when any accepted requirement is short, otherwise `AwaitingPlanningRun`. Positive available portions create material allocations; shortages remain immutable feasibility lines and generate dependent recommendations in the composite DDMRP write. Caller-supplied `OrderID`, candidate ID, status, authority boundary, or reservation identity is rejected/overwritten by generated values.

Tests cite `BE-DDMRP-009` and `BE-SDBR-006` through `009`; split candidate construction, candidate replay, and legacy fingerprint into separate RED/GREEN commits.

### Activation Task A5: Exact Copy-On-Write Composite Confirmation

**Review/commit boundary:** pure-domain atomic composition.

Use this mechanism; do not duplicate private reservation preflight logic:

```python
@dataclass(frozen=True, slots=True)
class DdmrpConfirmationWriteSet:
    idempotency_key: str
    recommendation_id: str
    logical_replenishment_id: str
    reservation_write_set: PlanningReservationWriteSet | None
    decision: dict[str, object]
    recommendation_events: tuple[dict[str, object], ...]
    active_graph: dict[str, object] | None
    dependent_recommendations: tuple[dict[str, object], ...]
    candidate_events: tuple[dict[str, object], ...]
    result: dict[str, object]


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
    ddmrp_keys: set[str]
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
    ddmrp_keys: frozenset[str]
    planning_keys: frozenset[str]
    result: dict[str, object]


def stage_ddmrp_confirmation(
    *,
    write_set: DdmrpConfirmationWriteSet,
    freshness: DdmrpConfirmationFreshnessContext,
    ledgers: DdmrpCompositeLedgers,
) -> DdmrpConfirmationStagedState:
    copied = deepcopy(ledgers)
    assert_ddmrp_confirmation_fresh(freshness)
    if write_set.idempotency_key in copied.ddmrp_keys:
        _assert_ddmrp_confirmation_replay(
            write_set=write_set,
            ledgers=copied,
        )
    else:
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
        _insert_immutable_record(
            copied.decisions,
            "DecisionID",
            write_set.decision,
        )
        if write_set.active_graph is not None:
            _insert_immutable_record(
                copied.active_graphs,
                "LogicalReplenishmentID",
                write_set.active_graph,
            )
        for recommendation in write_set.dependent_recommendations:
            _insert_immutable_record(
                copied.recommendations,
                "RecommendationID",
                recommendation,
            )
        _append_immutable_events(
            copied.recommendation_events,
            write_set.recommendation_events,
        )
        _append_immutable_events(
            copied.candidate_events,
            write_set.candidate_events,
        )
        _assert_complete_composite_graph(
            write_set=write_set,
            ledgers=copied,
        )
        copied.ddmrp_keys.add(write_set.idempotency_key)
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
        ddmrp_keys=frozenset(copied.ddmrp_keys),
        planning_keys=frozenset(copied.planning_keys),
        result=deepcopy(write_set.result),
    )
```

`_insert_immutable_record` rejects an existing ID with different content; `_append_immutable_events` rejects duplicate event IDs/content; `_assert_ddmrp_confirmation_replay` verifies the decision, all DDMRP events, active graph, dependent recommendations, and the shared replay result. These are mandatory named helpers with public-behavior tests.

`apply_ddmrp_confirmation_staged_state(...)` takes the staged state plus the same thirteen live collections. It deep-copies all live collections first, then uses `clear/update` or `clear/extend` to publish every staged collection. A single `except BaseException` restores all thirteen snapshots before re-raising. It performs no validation after replacement starts. The state-store middleware/SQLite transaction remains a second rollback layer.

Required tests inject failure (1) before shared staging, (2) inside shared apply, (3) after shared copy staging but before DDMRP copy staging, (4) during live replacement, and (5) during `store.save()`. Every test compares all DDMRP/shared collections byte-for-byte. Exact replay validates the immutable recommendation, decision event/result, candidate, demand, batch, capacities, materials, dependent recommendations, and both processed-key ledgers.

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

### Activation Task A7: Planner Confirmation API, RBAC, Audit, And Retry

**Review/commit boundary:** API only.

Exact request model:

```python
class DdmrpRecommendationConfirmPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ActionRequestID: str = Field(min_length=1)
    Reason: str = Field(min_length=1, max_length=500)
```

No action type, actor, confirmation time, target, BOM, capacity, or material override is accepted. The server reads advice from the accepted recommendation, actor from `_effective_actor_id(request, "local-planner")`, and time from `server_utc_now()`.

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
rg -n "AvailableQty|DLT_TARGET_SEMANTICS_INSUFFICIENT|DdmrpAuthoritySignature|LogicalReplenishmentID|CONTRACT-GATE-DDMRP-ACTIVATION-001|stage_ddmrp_confirmation|showNotification|1280x720|1920x1080|390x844|2\.80|2\.81|5\.35|5\.36" docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md
rg -n "InspectionHold|notify\(|ConfirmedBy:|ConfirmedAt:|PlanningAdviceLines" docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md
git diff --check
```

Expected: the first command finds every required correction; the second finds no executable request/body use of forbidden constructs; diff check exits 0.
