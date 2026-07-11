# DDMRP Runtime Replenishment Closure Staged Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First deliver an authority-correct, immutable DDMRP runtime evaluation and read-only replenishment workbench; preserve planner-confirmed Buy/Make and atomic Make candidate/CCR/material activation as an explicitly blocked second tranche that cannot execute until Contract Agent-accepted target-time, ERP/MRP advice, Plan BOM/feasibility, and production-authority evidence exists.

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
- Every changed/new test file has an exact module docstring naming its applicable `BE-*`/`UI-*` acceptance IDs.
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
| `BE-DDMRP-008` | 契约授权的 Buy/Make 建议与计划员确认治理 | `[NOT-STARTED]` | `D` approved design and staged implementation plan | 仅在 `CONTRACT-GATE-DDMRP-ACTIVATION-001` 关闭项全部验收后启动；建议类型由服务端已验收契约证据决定，计划员逐条确认，身份/时间由服务端记录，当前不得新增调用方自报 advice envelope。 |
| `BE-DDMRP-009` | Make 可行性、计划制造候选和共享 CCR/物料预留 | `[NOT-STARTED]` | `D` approved DDMRP and shared-reservation designs | 仅在已验收 Plan BOM、目标日期、物料/CCR 日历可行性和生产权威证据存在后启动；确认 Make 必须原子创建候选、CCR 预留和下级物料分配，并进入完整 Planning Run 生命周期。 |
```

Do not change `BE-SDBR-006` through `BE-SDBR-009` or `BE-RUN-011` from `[PARTIAL]`.

- [ ] **Step 3: Add two ordered UI units under version 5.35**

Set the UI header to `5.35`, date `2026-07-11`, and append:

```markdown
| 5.35 | 2026-07-11 | 新增 `UI-DDMRP-003` 版本化只读补货评估与契约门控工作台，以及后续 `UI-DDMRP-004` Buy/Make 人工确认单元；两单元分开验收，当前不暴露确认动作或外部订单创建 |
```

Define `UI-DDMRP-003` as the safe read-only evaluation/workbench unit and `UI-DDMRP-004` as the contract-gated confirmation unit. Add section 16 rows in this order:

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
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py -q -k "be_ddmrp_007" --basetemp .tmp/pytest-ddmrp-available-red -p no:cacheprovider
```

Expected: failures show the adapter still uses `OnHandQty` and source/context fields are missing.

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
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_api.py -q -k "ddmrp" --basetemp .tmp/pytest-ddmrp-available-green -p no:cacheprovider
python -m compileall -q sdbr
```

Expected: selected tests pass; Green/AboveGreen remain zero; no target timestamp appears.

- [ ] **Step 7: Commit**

```powershell
git add sdbr/ddmrp.py sdbr/ddsop_runtime_planning_input.py tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py
git commit -m "fix: consume authoritative DDMRP availability"
```

---

### Task 3: Complete Read-Only Authority Signature And Target Gate

**Files:**
- Create: `sdbr/ddmrp_replenishment.py`
- Create: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Produces `DdmrpAuthoritySignature`, `DdmrpGate`, `canonical_fingerprint(...)`, and `build_read_only_authority_signature(...)`.
- Every advice/BOM/material/capacity ID has a paired fingerprint field; absence is explicit `None`, not omission.

- [ ] **Step 1: Write the module traceability and failing tests**

Start the test file with:

```python
"""Acceptance evidence for BE-DDMRP-007; activation-only cases also trace BE-DDMRP-008 and BE-DDMRP-009."""
```

Add these exact test names:

```text
test_be_ddmrp_007_signature_freezes_runtime_config_and_all_current_authority_slots
test_be_ddmrp_007_public_demo_signature_is_read_only
test_be_ddmrp_007_missing_target_semantics_returns_named_gate_and_null_target
test_be_ddmrp_007_signature_fingerprint_changes_for_runtime_or_local_ledger_drift
test_be_ddmrp_007_rejects_runtime_configuration_reference_mismatch
```

The first test asserts this complete key set after `asdict(signature)`:

```python
{
    "runtime_package_id",
    "runtime_package_version",
    "runtime_package_fingerprint",
    "runtime_snapshot_id",
    "runtime_snapshot_at",
    "operating_model_configuration_id",
    "operating_model_fingerprint",
    "ddmrp_configuration_id",
    "target_time_semantics_id",
    "target_calendar_id",
    "target_calendar_fingerprint",
    "planning_advice_package_id",
    "planning_advice_package_fingerprint",
    "plan_bom_package_id",
    "plan_bom_package_fingerprint",
    "material_authority_snapshot_id",
    "material_authority_snapshot_fingerprint",
    "capacity_calendar_snapshot_id",
    "capacity_calendar_snapshot_fingerprint",
    "local_planning_ledger_revision",
    "local_planning_ledger_fingerprint",
    "scenario_label",
    "mapping_confidence",
    "parameter_authority_fingerprint",
    "signature_fingerprint",
}
```

- [ ] **Step 2: Run RED**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "signature or target_semantics or public_demo" --basetemp .tmp/pytest-ddmrp-signature-red -p no:cacheprovider
```

Expected: import failure because the new module does not exist.

- [ ] **Step 3: Implement exact internal signature types**

Create:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping

from sdbr.ddsop_contracts import canonical_operating_model_fingerprint


@dataclass(frozen=True, slots=True)
class DdmrpGate:
    code: str
    message: str
    blocks_operational_action: bool = True


class DdmrpReplenishmentConflict(ValueError):
    status = "DdmrpReplenishmentConflict"


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
    target_calendar_id: str | None
    target_calendar_fingerprint: str | None
    planning_advice_package_id: str | None
    planning_advice_package_fingerprint: str | None
    plan_bom_package_id: str | None
    plan_bom_package_fingerprint: str | None
    material_authority_snapshot_id: str | None
    material_authority_snapshot_fingerprint: str | None
    capacity_calendar_snapshot_id: str | None
    capacity_calendar_snapshot_fingerprint: str | None
    local_planning_ledger_revision: int
    local_planning_ledger_fingerprint: str
    scenario_label: str
    mapping_confidence: str
    parameter_authority_fingerprint: str
    signature_fingerprint: str


def canonical_fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"
```

Use this public signature:

```python
def build_read_only_authority_signature(
    *,
    package_record: Mapping[str, object],
    operating_model_configuration: Mapping[str, object],
    local_planning_ledger_revision: int,
    active_capacity_reservations: Mapping[str, Mapping[str, object]],
    active_material_allocations: Mapping[str, Mapping[str, object]],
) -> tuple[DdmrpAuthoritySignature, tuple[DdmrpGate, ...]]:
    package_payload = package_record.get("Payload")
    config_payload = operating_model_configuration.get(
        "Payload", operating_model_configuration
    )
    if not isinstance(package_payload, Mapping) or not isinstance(
        config_payload, Mapping
    ):
        raise DdmrpReplenishmentConflict("Validated authority payload is unavailable.")
    identity = package_payload.get("PackageIdentity")
    frozen = package_payload.get("FrozenDdsopConfiguration")
    runtime = package_payload.get("RuntimeEvidenceSnapshot")
    parameter_evidence = package_payload.get("ParameterAuthorityEvidence")
    if not all(
        isinstance(value, Mapping)
        for value in (identity, frozen, runtime, parameter_evidence)
    ):
        raise DdmrpReplenishmentConflict("Validated authority sections are incomplete.")

    expected_configuration_fingerprint = canonical_operating_model_fingerprint(
        config_payload
    )
    expected_configuration_id = str(
        config_payload["OperatingModelConfigurationID"]
    )
    expected_ddmrp_id = str(
        config_payload["DDMRPConfiguration"]["DDMRPConfigurationID"]
    )
    if (
        frozen["OperatingModelConfigurationID"] != expected_configuration_id
        or frozen["OperatingModelFingerprint"]
        != expected_configuration_fingerprint
        or frozen["DDMRPConfigurationID"] != expected_ddmrp_id
    ):
        raise DdmrpReplenishmentConflict(
            "Runtime package/configuration authority references do not match."
        )
    if (
        isinstance(local_planning_ledger_revision, bool)
        or not isinstance(local_planning_ledger_revision, int)
        or local_planning_ledger_revision < 0
    ):
        raise DdmrpReplenishmentConflict(
            "Local planning ledger revision must be a non-negative integer."
        )

    active_statuses = {
        "ActivePlanReservation",
        "LinkedToFormalOrder",
        "HeldForPlanningError",
    }
    ledger_payload = {
        "CapacityReservations": sorted(
            (
                dict(row)
                for row in active_capacity_reservations.values()
                if row.get("Status") in active_statuses
            ),
            key=lambda row: str(row.get("CapacityReservationID")),
        ),
        "MaterialAllocations": sorted(
            (
                dict(row)
                for row in active_material_allocations.values()
                if row.get("Status") in active_statuses
            ),
            key=lambda row: str(row.get("MaterialAllocationID")),
        ),
    }
    base = {
        "runtime_package_id": str(identity["RuntimePlanningInputPackageID"]),
        "runtime_package_version": str(identity["PackageVersion"]),
        "runtime_package_fingerprint": canonical_fingerprint(package_payload),
        "runtime_snapshot_id": str(runtime["OperationalStateSnapshotID"]),
        "runtime_snapshot_at": str(runtime["SnapshotAt"]),
        "operating_model_configuration_id": expected_configuration_id,
        "operating_model_fingerprint": expected_configuration_fingerprint,
        "ddmrp_configuration_id": expected_ddmrp_id,
        "target_time_semantics_id": None,
        "target_calendar_id": None,
        "target_calendar_fingerprint": None,
        "planning_advice_package_id": None,
        "planning_advice_package_fingerprint": None,
        "plan_bom_package_id": None,
        "plan_bom_package_fingerprint": None,
        "material_authority_snapshot_id": None,
        "material_authority_snapshot_fingerprint": None,
        "capacity_calendar_snapshot_id": None,
        "capacity_calendar_snapshot_fingerprint": None,
        "local_planning_ledger_revision": local_planning_ledger_revision,
        "local_planning_ledger_fingerprint": canonical_fingerprint(ledger_payload),
        "scenario_label": str(identity["ScenarioLabel"]),
        "mapping_confidence": str(identity["MappingConfidence"]),
        "parameter_authority_fingerprint": canonical_fingerprint(
            parameter_evidence
        ),
    }
    signature = DdmrpAuthoritySignature(
        **base,
        signature_fingerprint=canonical_fingerprint(base),
    )

    refs = parameter_evidence.get("ParameterEvidenceRefs", [])
    accepted_operational_authority = (
        identity["ScenarioLabel"] == "ProductionCandidate"
        and identity["MappingConfidence"] == "ProductionAccepted"
        and all(
            row.get("ProductionAuthorityStatus") == "Accepted"
            for row in refs
            if row.get("Applicability") == "Applicable"
        )
    )
    gates = [
        DdmrpGate(
            "DLT_TARGET_SEMANTICS_INSUFFICIENT",
            "The accepted contract does not define target-calendar/business-time semantics for DLT.",
        ),
        DdmrpGate(
            "PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
            "No Contract Agent-accepted ERP/MRP replenishment advice consumer is available.",
        ),
        DdmrpGate(
            "PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
            "No accepted Plan BOM/material/CCR feasibility authority bundle is available.",
        ),
    ]
    if not accepted_operational_authority:
        gates.append(
            DdmrpGate(
                "OPERATIONAL_AUTHORITY_NOT_ACCEPTED",
                "The current scenario, mapping, and evidence authority do not permit operational reservation writes.",
            )
        )
    return signature, tuple(sorted(gates, key=lambda gate: gate.code))
```

The body must re-check package/config IDs and canonical configuration fingerprint, hash the accepted package payload and parameter evidence, hash sorted active local capacity/material rows, and construct the full signature. It sets all target/advice/BOM/material-authority/capacity-authority fields to `None` because no accepted consumer can populate them today. Compute `signature_fingerprint` over all other fields, then return these exact gates in sorted-code order:

```python
(
    DdmrpGate(
        "DLT_TARGET_SEMANTICS_INSUFFICIENT",
        "The accepted contract does not define target-calendar/business-time semantics for DLT.",
    ),
    DdmrpGate(
        "PLANNING_ADVICE_CONTRACT_NOT_ACCEPTED",
        "No Contract Agent-accepted ERP/MRP replenishment advice consumer is available.",
    ),
    DdmrpGate(
        "PLAN_BOM_FEASIBILITY_CONTRACT_NOT_ACCEPTED",
        "No accepted Plan BOM/material/CCR feasibility authority bundle is available.",
    ),
    DdmrpGate(
        "OPERATIONAL_AUTHORITY_NOT_ACCEPTED",
        "The current scenario, mapping, and evidence authority do not permit operational reservation writes.",
    ),
)
```

The last gate is mandatory unless package `ScenarioLabel`, `MappingConfidence`, and every applicable parameter evidence row meet the accepted production classification defined by the current schema. Public demo/reviewed rows always receive it.

- [ ] **Step 4: Add a structured spike-input gate**

Add `DdmrpRuntimeAuthorityError(ValueError)` with `code` and `status="DdmrpRuntimeAuthorityError"`. In `evaluate_ddmrp_runtime_signals_from_package`, raise it with code `SPIKE_QUALIFICATION_INPUT_INSUFFICIENT` when the validated row says `RequiresSDBRQualification`/`CalculatedBySDBR` but the accepted configuration provides no threshold authority. Add a schema-valid test that passes through `process_runtime_planning_input_message(...)`; do not mutate a stored accepted record.

- [ ] **Step 5: Run GREEN and commit**

```powershell
pytest tests/test_ddmrp_replenishment.py tests/test_ddsop_runtime_planning_input.py -q -k "signature or target_semantics or public_demo or spike_qualification" --basetemp .tmp/pytest-ddmrp-signature-green -p no:cacheprovider
git add sdbr/ddmrp_replenishment.py sdbr/ddsop_runtime_planning_input.py tests/test_ddmrp_replenishment.py tests/test_ddsop_runtime_planning_input.py
git commit -m "feat: freeze DDMRP authority signatures"
```

---

### Task 4: Immutable Evaluation Builder And Stable Replenishment Chains

**Files:**
- Modify: `sdbr/ddmrp_replenishment.py`
- Modify: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Produces `DdmrpEvaluationWriteSet` and `prepare_ddmrp_evaluation(...)`.
- Stable chain identity is independent of evaluation ID; recommendation versions are bidirectional.

- [ ] **Step 1: Write focused failing tests**

Add exact names:

```text
test_be_ddmrp_007_red_yellow_create_blocked_versions_green_above_remain_monitor_rows
test_be_ddmrp_007_reevaluation_reuses_logical_chain_and_increments_version
test_be_ddmrp_007_recommendation_predecessor_and_supersession_links_are_bidirectional
test_be_ddmrp_007_active_confirmed_graph_creates_adjustment_required_not_second_actionable_version
test_be_ddmrp_007_terminal_chain_starts_next_cycle_with_new_logical_identity
test_be_ddmrp_007_same_authority_inputs_produce_deterministic_ids_and_fingerprint
```

Assert NOW recommendations have `AdviceType is None`, `StandardTargetReceiptAt is None`, `InitialStatus == "Blocked"`, and all four gate codes. Assert Green/AboveGreen appear only in evaluation rows.

- [ ] **Step 2: Run RED**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "chain or recommendation or adjustment_required" --basetemp .tmp/pytest-ddmrp-evaluation-builder-red -p no:cacheprovider
```

- [ ] **Step 3: Add exact records and signature**

```python
@dataclass(frozen=True, slots=True)
class DdmrpEvaluationWriteSet:
    idempotency_key: str
    payload_fingerprint: str
    evaluation_run: dict[str, object]
    evaluation_rows: tuple[dict[str, object], ...]
    chain_records: tuple[dict[str, object], ...]
    recommendation_versions: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]
```

Public signature:

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

The implementation is complete only when every canonical rule below is represented by a named helper and its public-behavior test; no unlisted fallback branch is allowed:

- `EvaluationAt` equals the authoritative runtime `SnapshotAt`; `RecordedAt` is server time.
- `EvaluationID = "DDE-" + sha256(authority_signature.signature_fingerprint + "|" + local_planning_ledger_fingerprint)[:20]`.
- `LogicalReplenishmentID = "DRL-" + sha256(f"{ItemID}|{LocationID}|{CycleNumber}")[:20]`.
- Reuse the only non-terminal chain for item/location; reject duplicate open chains. If none exists, `CycleNumber = max(prior cycles)+1`.
- `RecommendationVersion = max(version in chain)+1` and `RecommendationID = "DDR-" + sha256(f"{LogicalReplenishmentID}|{RecommendationVersion}")[:20]`.
- New versions name `PredecessorRecommendationID`; supersession events name both old and new recommendation IDs.
- Unconfirmed prior versions receive immutable `RecommendationSuperseded` events; their records are never edited.
- If `active_replenishment_graphs` contains the logical chain, create an immutable version with `InitialStatus="AdjustmentRequired"`, `AdjustmentOfRecommendationID`, and no confirmable action.
- Freeze the complete authority signature dictionary/fingerprint on both evaluation and recommendation.
- Never store raw package/config payloads in the evaluation ledger.

- [ ] **Step 4: Run GREEN and commit**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "chain or recommendation or adjustment_required" --basetemp .tmp/pytest-ddmrp-evaluation-builder-green -p no:cacheprovider
git add sdbr/ddmrp_replenishment.py tests/test_ddmrp_replenishment.py
git commit -m "feat: build immutable DDMRP evaluations"
```

---

### Task 5: Evaluation Replay, Staging, And Immutable Apply

**Files:**
- Modify: `sdbr/ddmrp_replenishment.py`
- Modify: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Produces `DdmrpEvaluationStagedState`, `stage_ddmrp_evaluation(...)`, and `apply_staged_ddmrp_evaluation(...)`.

- [ ] **Step 1: Write failing replay/atomicity tests**

Add exact names:

```text
test_be_ddmrp_007_exact_evaluation_replay_is_duplicate
test_be_ddmrp_007_request_id_reuse_with_changed_fingerprint_conflicts
test_be_ddmrp_007_event_or_child_drift_fails_closed
test_be_ddmrp_007_failure_after_staging_leaves_every_live_ledger_unchanged
test_be_ddmrp_007_duplicate_open_chain_preflight_leaves_no_partial_records
```

- [ ] **Step 2: Add the complete staging boundary**

```python
@dataclass(frozen=True, slots=True)
class DdmrpEvaluationStagedState:
    evaluation_runs: dict[str, dict[str, object]]
    evaluation_rows: dict[str, dict[str, object]]
    chains: dict[str, dict[str, object]]
    recommendations: dict[str, dict[str, object]]
    events: tuple[dict[str, object], ...]
    processed_action_keys: frozenset[str]
    result_status: Literal["Created", "Duplicate"]


def stage_ddmrp_evaluation(
    *,
    write_set: DdmrpEvaluationWriteSet,
    evaluation_runs: Mapping[str, dict[str, object]],
    evaluation_rows: Mapping[str, dict[str, object]],
    chains: Mapping[str, dict[str, object]],
    recommendations: Mapping[str, dict[str, object]],
    events: tuple[dict[str, object], ...],
    processed_action_keys: frozenset[str],
) -> DdmrpEvaluationStagedState:
    runs_copy = deepcopy(dict(evaluation_runs))
    rows_copy = deepcopy(dict(evaluation_rows))
    chains_copy = deepcopy(dict(chains))
    recommendations_copy = deepcopy(dict(recommendations))
    events_copy = [deepcopy(event) for event in events]
    keys_copy = set(processed_action_keys)

    business_payload = {
        "EvaluationRun": write_set.evaluation_run,
        "EvaluationRows": list(write_set.evaluation_rows),
        "ChainRecords": list(write_set.chain_records),
        "RecommendationVersions": list(write_set.recommendation_versions),
        "Events": list(write_set.events),
    }
    if canonical_fingerprint(business_payload) != write_set.payload_fingerprint:
        raise DdmrpReplenishmentConflict(
            "Evaluation write-set fingerprint does not match its immutable content."
        )

    targets = (
        (runs_copy, "EvaluationID", (write_set.evaluation_run,)),
        (rows_copy, "EvaluationRowID", write_set.evaluation_rows),
        (chains_copy, "LogicalReplenishmentID", write_set.chain_records),
        (
            recommendations_copy,
            "RecommendationID",
            write_set.recommendation_versions,
        ),
    )
    event_by_id = {str(event["EventID"]): event for event in events_copy}
    if len(event_by_id) != len(events_copy):
        raise DdmrpReplenishmentConflict(
            "Persisted DDMRP event IDs are not unique."
        )

    if write_set.idempotency_key in keys_copy:
        replay_events = [
            event
            for event in events_copy
            if event.get("IdempotencyKey") == write_set.idempotency_key
        ]
        if len(replay_events) != 1 or replay_events[0].get(
            "PayloadFingerprint"
        ) != write_set.payload_fingerprint:
            raise DdmrpReplenishmentConflict(
                "Processed evaluation key has no unique matching replay event."
            )
        for target, id_field, records in targets:
            for record in records:
                record_id = str(record[id_field])
                if target.get(record_id) != record:
                    raise DdmrpReplenishmentConflict(
                        f"Persisted evaluation replay child {record_id} drifted."
                    )
        for event in write_set.events:
            if event_by_id.get(str(event["EventID"])) != event:
                raise DdmrpReplenishmentConflict(
                    "Persisted evaluation replay event drifted."
                )
        return DdmrpEvaluationStagedState(
            evaluation_runs=runs_copy,
            evaluation_rows=rows_copy,
            chains=chains_copy,
            recommendations=recommendations_copy,
            events=tuple(events_copy),
            processed_action_keys=frozenset(keys_copy),
            result_status="Duplicate",
        )

    for target, id_field, records in targets:
        for record in records:
            record_id = str(record[id_field])
            existing = target.get(record_id)
            if existing is not None and existing != record:
                raise DdmrpReplenishmentConflict(
                    f"Evaluation target {record_id} already has different content."
                )
    for event in write_set.events:
        event_id = str(event["EventID"])
        existing = event_by_id.get(event_id)
        if existing is not None and existing != event:
            raise DdmrpReplenishmentConflict(
                f"Evaluation event {event_id} already has different content."
            )

    for target, id_field, records in targets:
        for record in records:
            target.setdefault(str(record[id_field]), deepcopy(record))
    for event in write_set.events:
        event_id = str(event["EventID"])
        if event_id not in event_by_id:
            events_copy.append(deepcopy(event))
            event_by_id[event_id] = event
    keys_copy.add(write_set.idempotency_key)
    return DdmrpEvaluationStagedState(
        evaluation_runs=runs_copy,
        evaluation_rows=rows_copy,
        chains=chains_copy,
        recommendations=recommendations_copy,
        events=tuple(events_copy),
        processed_action_keys=frozenset(keys_copy),
        result_status="Created",
    )


def apply_staged_ddmrp_evaluation(
    *,
    staged: DdmrpEvaluationStagedState,
    evaluation_runs: MutableMapping[str, dict[str, object]],
    evaluation_rows: MutableMapping[str, dict[str, object]],
    chains: MutableMapping[str, dict[str, object]],
    recommendations: MutableMapping[str, dict[str, object]],
    events: MutableSequence[dict[str, object]],
    processed_action_keys: MutableSet[str],
) -> Literal["Created", "Duplicate"]:
    snapshots = (
        deepcopy(dict(evaluation_runs)),
        deepcopy(dict(evaluation_rows)),
        deepcopy(dict(chains)),
        deepcopy(dict(recommendations)),
        deepcopy(list(events)),
        deepcopy(set(processed_action_keys)),
    )
    try:
        evaluation_runs.clear()
        evaluation_runs.update(deepcopy(staged.evaluation_runs))
        evaluation_rows.clear()
        evaluation_rows.update(deepcopy(staged.evaluation_rows))
        chains.clear()
        chains.update(deepcopy(staged.chains))
        recommendations.clear()
        recommendations.update(deepcopy(staged.recommendations))
        events.clear()
        events.extend(deepcopy(staged.events))
        processed_action_keys.clear()
        processed_action_keys.update(staged.processed_action_keys)
    except BaseException:
        evaluation_runs.clear()
        evaluation_runs.update(snapshots[0])
        evaluation_rows.clear()
        evaluation_rows.update(snapshots[1])
        chains.clear()
        chains.update(snapshots[2])
        recommendations.clear()
        recommendations.update(snapshots[3])
        events.clear()
        events.extend(snapshots[4])
        processed_action_keys.clear()
        processed_action_keys.update(snapshots[5])
        raise
    return staged.result_status
```

`stage_ddmrp_evaluation` deep-copies inputs, validates all target IDs/events/fingerprints, performs exact replay verification, and adds the processed key last on copies. `apply_staged_ddmrp_evaluation` snapshots all live collections, replaces them from staged copies, and restores every snapshot on any exception. No business validation occurs after live replacement begins.

- [ ] **Step 3: Run tests and commit**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "replay or staging or partial_records" --basetemp .tmp/pytest-ddmrp-evaluation-apply -p no:cacheprovider
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
processed_ddmrp_action_keys
```

Verify save failure restores all seven and the revision.

- [ ] **Step 2: Run RED**

```powershell
pytest tests/test_state_store.py -q -k "be_ddmrp_007" --basetemp .tmp/pytest-ddmrp-store-red -p no:cacheprovider
```

- [ ] **Step 3: Add exact store fields and boundaries**

Add to `WorkbenchStateStore`:

```python
ddmrp_evaluation_runs: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_evaluation_rows: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_chains: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_recommendations: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_events: list[dict[str, object]] = field(default_factory=list)
ddmrp_active_replenishment_graphs: dict[str, dict[str, object]] = field(default_factory=dict)
processed_ddmrp_action_keys: set[str] = field(default_factory=set)
```

Add them to `_state_payloads`, `_apply_payloads`, `_clear`, and `_state_counts`; serialize the set sorted. Keep `SCHEMA_VERSION = 1` because state keys remain JSON rows and absent keys load empty.

- [ ] **Step 4: Run GREEN and commit**

```powershell
pytest tests/test_state_store.py -q -k "be_ddmrp_007 or complete_state" --basetemp .tmp/pytest-ddmrp-store-green -p no:cacheprovider
git add sdbr/state_store.py tests/test_state_store.py
git commit -m "feat: persist DDMRP evaluation history"
```

---

### Task 7: Safe Workbench Projection With Active/History Visibility

**Files:**
- Create: `sdbr/ddmrp_replenishment_view.py`
- Create: `tests/test_ddmrp_replenishment_view.py`

**Interfaces:**
- Produces `build_ddmrp_replenishment_workbench(...) -> dict[str, object]`.

- [ ] **Step 1: Write exact projection tests**

Use module docstring:

```python
"""Acceptance evidence for BE-DDMRP-007 and UI-DDMRP-003."""
```

Add exact names:

```text
test_be_ddmrp_007_view_returns_latest_rows_plus_older_active_or_adjustment_chains
test_be_ddmrp_007_view_exposes_null_target_and_business_gate_codes
test_be_ddmrp_007_view_never_exposes_frozen_payload_or_evidence_rows
test_be_ddmrp_007_view_rejects_duplicate_chain_or_orphan_recommendation
test_be_ddmrp_007_view_is_deterministic_and_deep_copied
test_be_ddmrp_007_view_empty_state_shape_is_stable
```

- [ ] **Step 2: Implement the exact signature and response shape**

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

Return exactly these top-level keys and types:

| Key | Exact type/content |
| --- | --- |
| `Evaluation` | `None` for empty state; otherwise an object with exactly `EvaluationID`, `EvaluationAt`, `RecordedAt`, `RuntimePlanningInputPackageID`, `RuntimePlanningInputPackageVersion`, `OperatingModelConfigurationID`, `OperatingModelFingerprint`, `DDMRPConfigurationID`, `AuthoritySignatureFingerprint`, and `OperationalActionAllowed=False`. |
| `Summary` | Object with exactly `RedCount`, `YellowCount`, `GreenCount`, `AboveGreenCount`, `BlockedRecommendationCount`, `PendingReviewCount=0`, `AdjustmentRequiredCount`, and `ActiveGraphCount`. |
| `Rows` | Deterministically sorted copied business-row list for the latest evaluation. |
| `ActiveGraphs` | Deterministically sorted copied active-graph summaries, including older confirmed/adjustment chains. |
| `History` | Deterministically sorted copied recommendation version/event summaries. |
| `Issues` | Copied structured issue/gate list. |
| `Boundary` | Exact string `Read-only SDBR planning evaluation; no ERP order, inventory authority, or operational reservation write.` |

Rows expose business quantities, `StandardTargetReceiptAt=None`, source type, statuses, and gate messages. IDs/fingerprints live only under `TechnicalDetails`. Reject malformed graph identities rather than undercounting. Never return package/config payloads, evidence refs, capacity/material rows, or a generic `Payload` key.

- [ ] **Step 3: Run and commit**

```powershell
pytest tests/test_ddmrp_replenishment_view.py -q --basetemp .tmp/pytest-ddmrp-view -p no:cacheprovider
git add sdbr/ddmrp_replenishment_view.py tests/test_ddmrp_replenishment_view.py
git commit -m "feat: project safe DDMRP workbench rows"
```

---

### Task 8: Server-Built Evaluation And Read API

**Files:**
- Modify: `sdbr/api.py` near current DDMRP payloads/routes and `persist_successful_writes`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces `POST /planner/workbench/ddmrp/evaluations` and `GET /planner/workbench/ddmrp/workbench`.
- Uses the existing response wrapper `{Endpoint, StatusCode, Data}` and `X-Workbench-Revision`.
- Accepts no advice type, target, BOM, capacity, material, actor, or timestamp override.

- [ ] **Step 1: Add exact API models**

```python
class DdmrpEvaluationCreatePayload(BaseModel):
    EvaluationRequestID: str = Field(min_length=1)
    RuntimePlanningInputPackageID: str = Field(min_length=1)
```

There are no mutable list defaults and no client actor/time fields.

- [ ] **Step 2: Write RED API/RBAC/rollback tests**

Extend the module traceability comment for each test and use exact names:

```text
test_be_ddmrp_007_evaluation_api_references_stored_validated_package_only
test_be_ddmrp_007_evaluation_api_rejects_raw_authority_fields
test_be_ddmrp_007_evaluation_api_uses_server_actor_and_server_time
test_be_ddmrp_007_evaluation_api_exact_retry_and_changed_request_conflict
test_be_ddmrp_007_evaluation_api_public_demo_is_read_only
test_be_ddmrp_007_workbench_api_uses_standard_wrapper_and_safe_shape
test_be_ddmrp_007_write_revision_and_save_failure_restore_every_ledger
test_be_ddmrp_007_ddmrp_routes_enforce_viewer_planner_admin_rbac
```

The raw-authority test posts extra fields such as `AdviceType`, `TargetReceiptAt`, `CapacityRequests`, or `MaterialRequests` and expects Pydantic `422` because the model is strict (`model_config = ConfigDict(extra="forbid")`). RBAC expectations: Viewer may GET but not POST; Planner/Admin may GET/POST; Worker may not access this planner page; missing identity is 401 when auth is enabled.

- [ ] **Step 3: Extend auth and bind ledgers**

Add the `/planner/workbench/ddmrp` prefix to middleware authorization. Add a DDMRP-specific branch to `_planning_run_authorization_error`: GET permits `Viewer`, `Planner`, `Admin`; writes permit `Planner`, `Admin`. Keep existing Planning Run/reservation behavior unchanged.

Bind the seven new store collections in `create_app`.

- [ ] **Step 4: Implement thin server-owned orchestration**

The POST route must:

1. Look up `RuntimePlanningInputPackageID` in `ddsop_runtime_planning_input_packages` and its referenced configuration in `operating_model_configurations`.
2. Require stored `ProcessingStatus="Accepted"`; never process request-body runtime rows.
3. Use `actor_id = _effective_actor_id(request, "local-planner")` and `recorded_at = server_utc_now()`.
4. Call `evaluate_ddmrp_runtime_signals_from_package`, `build_read_only_authority_signature`, `prepare_ddmrp_evaluation`, `stage_ddmrp_evaluation`, and `apply_staged_ddmrp_evaluation`.
5. Return the wrapper below; let middleware own revision admission, save, and complete rollback.

```python
{
    "Endpoint": "/planner/workbench/ddmrp/evaluations",
    "StatusCode": 200,
    "Data": {
        "Status": "Created" | "Duplicate",
        "EvaluationID": evaluation_id,
        "RecommendationIDs": recommendation_ids,
        "OperationalActionAllowed": False,
        "Workbench": workbench,
    },
}
```

The GET route returns:

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

Map unknown package/config to 404, contract/signature/domain conflicts to structured 409, and schema extras to 422.

- [ ] **Step 5: Run GREEN and commit**

```powershell
pytest tests/test_api.py tests/test_ddmrp_replenishment.py tests/test_ddmrp_replenishment_view.py tests/test_state_store.py -q -k "be_ddmrp_007" --basetemp .tmp/pytest-ddmrp-api-green -p no:cacheprovider
python -m compileall -q sdbr
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
