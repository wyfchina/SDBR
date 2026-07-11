# DDMRP Runtime Replenishment Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the operational DDMRP replenishment line by turning frozen runtime net-flow results into planner-confirmed Buy/Make advice, with confirmed Make advice atomically creating a planned manufacturing candidate, CCR capacity reservations, and lower-level material planning allocations.

**Architecture:** Keep `sdbr/ddmrp.py` as the pure net-flow engine and use the existing `DDSOP-RUNTIME-PLANNING-INPUT-V1` consumer as the only DDAE-backed runtime input path. Add a focused replenishment domain module for immutable evaluations, versioned recommendations, supersession, confirmation, and idempotency; extend the shared Phase 0 reservation write set only enough to carry one MTA planned manufacturing candidate. Persist the new ledgers in the existing whole-state JSON store, expose safe FastAPI read/action models, and upgrade the existing Materials Planning page without exposing raw DDAE, ERP/MRP, capacity, or material payloads.

**Tech Stack:** Python 3.11+ (current project runtime/tests use Python 3.12), FastAPI, Pydantic v2, dataclasses, existing in-memory/SQLite `WorkbenchStateStore`, pytest, vanilla HTML/CSS/JavaScript.

## Global Constraints

- SDBR remains a DDOM / S-DBR execution system; DDAE/DDS&OP owns Buffer Profiles, adjustment factors, decoupling-point design, and master-setting approval.
- Consume the existing frozen `OperatingModelConfigurationID`, `OperatingModelFingerprint`, `DDMRPConfigurationID`, DLT, zone tops, MOQ/order multiple, and qualification semantics. Do not add or infer DDAE contract fields.
- Use the accepted `DDSOP-RUNTIME-PLANNING-INPUT-V1` package and its frozen configuration for inventory, quality, demand, supply, UOM, source timestamps, and traceability.
- A separate explicit ERP/MRP-origin planning-advice envelope supplies `Buy` versus `Make`, routing, CCR load lines, and lower-level material requirement lines. Missing evidence blocks confirmation; no local defaults or routing/BOM inference are allowed.
- Calculate `StandardTargetReceiptAt = EvaluatedAt + FrozenDLTMinutes`; this is a planning target, not a production or supplier promise.
- Only Red and Yellow net-flow rows create replenishment recommendations. Green and AboveGreen remain zero-quantity monitor rows.
- Planner confirmation is mandatory for both Buy and Make. Buy confirmation records an internal decision only. Make confirmation creates one MTA demand commitment, one planned manufacturing candidate, one reservation batch, one or more CCR reservations, and one or more lower-level material allocations in one atomic write.
- ERP/MRP remains authoritative for formal production orders, purchase orders, supplier execution, BOM/source governance, and external order acceptance. ERP/WMS/QMS remains authoritative for inventory balances, allocations, receipts, and quality state.
- Do not implement Transfer advice, substitute material, batch/lot/expiry, split/merge rules, production purchase orders, automatic external order creation, Mock ERP delivery/ACK, or automatic schedule/release changes in this plan.
- Do not expose raw JSON master-data, DDAE payloads, ERP/MRP evidence rows, or reservation request rows in the normal planner workflow.
- Preserve OR-Tools CP-SAT as the only executable solver for new Planning Runs. This plan does not change solver behavior or Simio scope.
- Every backend test and acceptance record must cite `BE-DDMRP-007`, `BE-DDMRP-008`, or `BE-DDMRP-009` as applicable, plus shared `BE-SDBR-006` through `BE-SDBR-009` where the reservation foundation is exercised.
- Update specifications before implementation; do not mark a capability `[VERIFIED]` until repeatable evidence exists. Never mark `UI-DDMRP-003` `用户已确认` without explicit user confirmation.
- The UI work is a new acceptance unit and must be the final implementation task. After it is implemented and verified, stop and request user confirmation.
- Do not track or modify `nofinish/`.

---

## File Structure

- Modify `docs/backend-specification.md`
  - Add `BE-DDMRP-007` through `BE-DDMRP-009`, preserve the existing verified `BE-DDMRP-001` through `BE-DDMRP-006` boundary, and record shared-ledger progress without overstating ERP/MRP authority.
- Modify `docs/ui-specification.md`
  - Add `UI-DDMRP-003` as a new acceptance unit on the existing Materials Planning page and preserve `UI-DDMRP-002` as the verified read-only baseline.
- Modify `sdbr/ddmrp.py`
  - Preserve the V1 formula while exposing qualified on-hand, source identifiers, and the standard target receipt timestamp in each line.
- Modify `sdbr/ddsop_runtime_planning_input.py`
  - Map accepted runtime-package inventory/quality/UOM/evidence into the pure engine without changing the DDAE contract.
- Create `sdbr/ddmrp_replenishment.py`
  - Own immutable evaluation and recommendation write sets, recommendation supersession, Buy/Make confirmation, stale/fingerprint gates, and DDMRP action idempotency.
- Modify `sdbr/planning_reservations.py`
  - Extend the shared atomic write set with an optional MTA planned manufacturing candidate while keeping existing MTO/no-candidate fingerprints and callers compatible.
- Create `sdbr/ddmrp_replenishment_view.py`
  - Build the safe latest-evaluation/recommendation/candidate/reservation workbench model; never return raw frozen payloads.
- Modify `sdbr/state_store.py`
  - Persist evaluation runs, recommendations, planned manufacturing candidates, DDMRP events, and processed action keys through memory/SQLite save, load, rollback, clear, and health paths.
- Modify `sdbr/api.py`
  - Add evaluation, workbench, and confirmation endpoints under `/planner/workbench/ddmrp`; keep domain rules out of route handlers.
- Modify `sdbr/web/planner-workbench.html`
  - Add evaluation freshness, advice/target/status columns, business confirmation actions, and candidate/reservation summaries to the existing Materials Planning page.
- Modify `sdbr/web/planner-workbench.js`
  - Consume the new safe workbench API, retain the returned state revision, confirm through the shared dialog, send `If-Match`, handle stale/conflict responses, and reload the page state.
- Modify `sdbr/web/planner-workbench.css`
  - Add compact recommendation/action/evidence layouts and responsive rules without nested cards or horizontal clipping.
- Modify `tests/test_ddmrp.py`
  - Protect the net-flow formula, target-date calculation, source-component traceability, and zero Green/AboveGreen recommendation behavior.
- Modify `tests/test_ddsop_runtime_planning_input.py`
  - Prove qualified available inventory and quality/UOM/source evidence come from the existing frozen runtime package.
- Create `tests/test_ddmrp_replenishment.py`
  - Cover immutable evaluation records, Red/Yellow recommendation creation, blocked evidence, supersession, stale confirmation, Buy confirmation, Make atomicity, replay, and conflict behavior.
- Modify `tests/test_planning_reservations.py`
  - Cover optional manufacturing-candidate construction, deterministic identity, candidate-aware replay, preflight, and legacy/no-candidate compatibility.
- Create `tests/test_ddmrp_replenishment_view.py`
  - Cover safe projection, summaries, technical-detail boundaries, and candidate/reservation linkage.
- Modify `tests/test_state_store.py`
  - Cover SQLite round trip, clear, health counts, and complete rollback for all new collections.
- Modify `tests/test_api.py`
  - Cover API happy paths, missing/stale references, action idempotency, save/revision rollback, safe response shape, and UI static contract.

---

### Task 1: Specification-First Capability Boundary

**Files:**
- Modify: `docs/backend-specification.md`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes: `BE-DDMRP-001` through `BE-DDMRP-006`, `BE-SDBR-006` through `BE-SDBR-009`, `BE-RUN-011`, `BE-INT-003`, `UI-DDMRP-001`, and `UI-DDMRP-002`.
- Produces: `BE-DDMRP-007`, `BE-DDMRP-008`, `BE-DDMRP-009`, and `UI-DDMRP-003`, which every later test/acceptance note cites.

- [ ] **Step 1: Add backend capability targets before code**

Add these rows after `BE-DDMRP-006`; use `[NOT-STARTED]` because only design evidence exists at this point:

```markdown
| `BE-DDMRP-007` | Frozen operational DDMRP evaluation ledger | `[NOT-STARTED]` | `D` `docs/superpowers/specs/2026-07-10-ddmrp-runtime-replenishment-closure-design.md`; `D` `docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md` | Consume an accepted `DDSOP-RUNTIME-PLANNING-INPUT-V1` package and its exact frozen operating-model fingerprint; persist immutable evaluation results, input fingerprints, issues, and replacement links without adding DDAE fields. |
| `BE-DDMRP-008` | Versioned Buy/Make replenishment advice and planner confirmation | `[NOT-STARTED]` | `D` `docs/superpowers/specs/2026-07-10-ddmrp-runtime-replenishment-closure-design.md`; `D` `docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md` | Red/Yellow rows produce versioned advice with `StandardTargetReceiptAt = EvaluatedAt + FrozenDLTMinutes`; Green/AboveGreen produce no advice; planner confirmation is explicit and idempotent; no external order is created automatically. |
| `BE-DDMRP-009` | Atomic MTA Make candidate and shared planning reservations | `[NOT-STARTED]` | `D` `docs/superpowers/specs/2026-07-10-mto-mta-shared-planning-reservation-foundation-design.md`; `D` `docs/superpowers/plans/2026-07-11-ddmrp-runtime-replenishment-closure.md` | Confirmed Make advice atomically creates one planned manufacturing candidate, CCR plan reservations, and lower-level material planning allocations through `BE-SDBR-006` through `BE-SDBR-009`; these are SDBR planning objects, not formal ERP production orders or inventory allocations. |
```

In the `BE-SDBR-007` through `BE-SDBR-009` gap text, add one sentence saying the MTA caller will be supplied by `BE-DDMRP-009` while MTO and external authority handoff remain separate completion boundaries. Do not change those shared capabilities from `[PARTIAL]`.

- [ ] **Step 2: Add the UI acceptance target and ordering gate**

After `UI-DDMRP-002`, add:

```markdown
### UI-DDMRP-003 DDMRP 补货建议确认

**状态：待实现**

页面位置：现有独立导航页 `物料计划 / Materials Planning`。

页面显示：

- 最新不可变评估时间、运行包、冻结配置版本和数据新鲜度；
- Red/Yellow Buy/Make 建议、标准目标到位时间、建议状态和阻塞原因；
- Make 建议的计划制造候选、CCR 计划预留和下级物料计划分配摘要；
- 技术 ID 和 fingerprint 默认放入可展开技术详情，不显示原始 JSON。

交互边界：

- 计划员逐条确认 Buy 或 Make 建议；确认前显示数量、目标时间和影响摘要；
- Buy 只记录内部已确认建议，不建立采购单、不投递外部系统；
- Make 通过同一确认事务创建计划制造候选、CCR 预留和下级物料计划分配；
- 输入版本变化、建议已替代、证据缺失或并发 revision 变化时拒绝确认并要求刷新；
- 不提供 Buffer Profile、DLT、调整因子、解耦点、替代料、批次或外部订单配置。
```

Revise the `UI-DDMRP-002` read-only boundary to say its baseline remains read-only and `UI-DDMRP-003` exclusively owns confirmation actions. Add acceptance unit 13 to section 16:

```markdown
| 13 | DDMRP 补货确认 | UI-DDMRP-003 | 是 |
```

Record that the user's explicit request authorizes unit 13 work while older DDMRP read-only items remain `已验证待用户确认`; do not change any prior item to `用户已确认`.

- [ ] **Step 3: Add start records without claiming implementation**

Set the backend document header to the next version after the latest changelog row (currently `2.80`) and add:

```markdown
| 2.80 | 2026-07-11 | 启动 DDMRP 运行补货收口：新增冻结评估、Buy/Make 人工确认和 Make 计划制造候选/共享预留验收目标；不新增 DDAE 字段，不建立正式外部订单 |
```

Set the UI document header to the next version after the latest changelog row (currently `5.35`) and add:

```markdown
| 5.35 | 2026-07-11 | 新增 `UI-DDMRP-003` DDMRP 补货建议确认验收单元：在物料计划页逐条确认 Buy/Make；Make 创建计划候选与共享预留；不提供参数治理或外部订单创建 |
```

- [ ] **Step 4: Verify the specification boundary**

Run:

```powershell
rg -n "BE-DDMRP-007|BE-DDMRP-008|BE-DDMRP-009|UI-DDMRP-003|DDMRP 补货确认|不建立正式外部订单" docs/backend-specification.md docs/ui-specification.md
git diff --check
```

Expected: all four new IDs and both no-external-order boundaries appear; `BE-DDMRP-007` through `009` are `[NOT-STARTED]`; `UI-DDMRP-003` is `待实现`; no prior item is newly marked `用户已确认`.

- [ ] **Step 5: Commit the specification targets**

```powershell
git add docs/backend-specification.md docs/ui-specification.md
git commit -m "docs: specify DDMRP replenishment closure"
```

---

### Task 2: Qualified Runtime Net Flow and Standard Target

**Files:**
- Modify: `sdbr/ddmrp.py`
- Modify: `sdbr/ddsop_runtime_planning_input.py`
- Modify: `tests/test_ddmrp.py`
- Modify: `tests/test_ddsop_runtime_planning_input.py`

**Interfaces:**
- Consumes: accepted runtime-package `InventoryPositions`, `DemandSignals`, `OpenSupplySignals`, and frozen DDAE `DDMRPConfiguration` already supported by `evaluate_ddmrp_runtime_signals_from_package(...)`.
- Produces:
  - Existing `evaluate_ddmrp_net_flow(...) -> dict[str, object]`, backward compatible.
  - Every line adds `QualifiedOnHandQty` and `StandardTargetReceiptAt`.
  - Demand/supply components preserve existing contract source IDs and UOM when present.
  - Contract-backed lines add `PhysicalOnHandQty`, `AuthorityAllocatedQty`, `QualityState`, and `Uom` without changing the DDAE schema.
  - A structured failure when a runtime spike requires SDBR qualification but the frozen contract does not provide enough threshold evidence; no local threshold is invented.

- [ ] **Step 1: Write failing pure-engine tests**

Extend `tests/test_ddmrp.py` with explicit `BE-DDMRP-007`/`008` comments and these assertions:

```python
def test_ddmrp_line_exposes_qualified_on_hand_and_standard_target_from_frozen_dlt():
    evaluated_at = datetime(2026, 7, 11, 8, 0, tzinfo=timezone.utc)
    result = evaluate_ddmrp_net_flow(
        decoupling_points=[
            DecouplingPoint("FG-1", "MAIN", "BP-1", dlt_minutes=2880)
        ],
        stock_buffers=[InventoryBufferPolicy("FG-1", "MAIN", 25, 20, 30, 50)],
        demand_signals=[
            DemandSignal(
                "FG-1",
                "MAIN",
                20,
                evaluated_at,
                demand_id="DEM-1",
                uom="EA",
            )
        ],
        open_supply=[
            OpenSupply(
                "FG-1",
                "MAIN",
                5,
                evaluated_at + timedelta(hours=1),
                supply_id="SUP-1",
                uom="EA",
            )
        ],
        evaluated_at=evaluated_at,
    )

    line = result["Lines"][0]
    assert line["QualifiedOnHandQty"] == 25
    assert line["StandardTargetReceiptAt"] == "2026-07-13T08:00:00+00:00"
    assert line["DemandComponents"][0]["DemandID"] == "DEM-1"
    assert line["SupplyComponents"][0]["SupplyID"] == "SUP-1"
```

Also extend the existing Green and AboveGreen tests to assert both `SuggestedReplenishmentQty == 0` and no implied advice marker is returned.

- [ ] **Step 2: Write the failing contract-backed qualified inventory test**

In `tests/test_ddsop_runtime_planning_input.py`, clone the accepted package fixture, set its first inventory row to `OnHandQty=42`, `AllocatedQty=8`, `AvailableQty=34`, `QualityState="Released"`, and assert:

```python
def test_runtime_ddmrp_uses_authority_available_qty_and_preserves_inventory_context():
    message = _runtime_message(status="AcceptedForBoundedPlanning")
    accepted_config = _accepted_configuration_for(message)
    package = _accepted_result(message).package_record
    assert package is not None

    result = evaluate_ddmrp_runtime_signals_from_package(
        package,
        accepted_config,
        evaluated_at=datetime.fromisoformat("2026-06-30T09:00:00+08:00"),
    )

    line = result["Lines"][0]
    assert line["PhysicalOnHandQty"] == 42
    assert line["AuthorityAllocatedQty"] == 8
    assert line["QualifiedOnHandQty"] == 34
    assert line["OnHandQty"] == 34
    assert line["QualityState"] == "Released"
    assert line["Uom"] == "EA"
```

Add a second case with `QualityState="InspectionHold"` and `AvailableQty=0` to prove held stock does not enter planning or execution status.

Add a third case with `DemandType="SpikeCandidate"`, `SpikeQualificationStatus="RequiresSDBRQualification"`, and `SpikeQualificationMode="CalculatedBySDBR"`. Because the current frozen DDAE contract exposes a horizon but no spike threshold, assert `evaluate_ddmrp_runtime_signals_from_package` raises `ValueError` containing `SPIKE_QUALIFICATION_INPUT_INSUFFICIENT`; do not assert zero demand.

- [ ] **Step 3: Run the tests and verify RED**

Run:

```powershell
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py -q -k "standard_target or authority_available_qty or inspection_hold or spike_qualification" --basetemp .tmp/pytest-ddmrp-qualified-red -p no:cacheprovider
```

Expected: FAIL because the new fields and optional source identifiers do not exist, the runtime adapter still passes physical on-hand, and the insufficient spike case is silently treated as unqualified.

- [ ] **Step 4: Extend the pure dataclasses and output without changing the formula**

In `sdbr/ddmrp.py`, append optional fields after existing defaulted fields so current positional callers remain valid:

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

In `_evaluate_point`, keep the existing net-flow/status/rounding calculations exactly and add:

```python
"QualifiedOnHandQty": buffer.on_hand_qty,
"StandardTargetReceiptAt": (
    evaluated_at + timedelta(minutes=point.dlt_minutes)
).isoformat(),
```

Add `DemandID`/`Uom` and `SupplyID`/`Uom` to component dictionaries. Keep legacy `OnHandQty`, `EvaluationMode="DDMRPNetFlowV1"`, and all existing keys so `/net-flow/evaluate` and `/status` remain compatible.

- [ ] **Step 5: Map only existing runtime-contract fields**

In `evaluate_ddmrp_runtime_signals_from_package`:

```python
qualified_on_hand = (
    float(inventory["AvailableQty"])
    if inventory.get("QualityState") == "Released"
    else 0.0
)
```

Before building `DemandSignal`, accept a spike as qualified only when the row says `QualifiedByDDSOP` with `ProvidedByDDSOP`. Exclude an explicitly `Rejected` spike. If the row says `RequiresSDBRQualification`/`CalculatedBySDBR` and the frozen configuration lacks a contract-defined threshold, raise `ValueError("SPIKE_QUALIFICATION_INPUT_INSUFFICIENT: frozen DDAE inputs do not define a spike threshold.")`; do not derive one from buffer zones, DLT, or local UI data. Record this as a Contract Agent change-request prerequisite for enabling that mode, outside this repository plan.

Pass `qualified_on_hand` as `InventoryBufferPolicy.on_hand_qty`. Populate `DemandSignal.demand_id/uom` from `DemandID/UnitOfMeasure` and `OpenSupply.supply_id/uom` from `SupplyID/UnitOfMeasure`. After evaluation, join each result line back to its already-validated inventory row and add only:

```python
{
    "PhysicalOnHandQty": float(inventory["OnHandQty"]),
    "AuthorityAllocatedQty": float(inventory["AllocatedQty"]),
    "QualityState": str(inventory["QualityState"]),
    "Uom": str(inventory["UnitOfMeasure"]),
}
```

Do not add fields to `DDSOP-RUNTIME-PLANNING-INPUT-V1`, recalculate profile values, infer quality, or modify the stored package.

- [ ] **Step 6: Run focused and compatibility tests**

```powershell
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_api.py -q -k "ddmrp" --basetemp .tmp/pytest-ddmrp-qualified-green -p no:cacheprovider
python -m compileall -q sdbr
```

Expected: all selected tests pass; legacy endpoint assertions still see `DDMRPNetFlowV1`, `OnHandQty`, and unchanged Red/Yellow/Green/AboveGreen behavior.

- [ ] **Step 7: Commit the qualified runtime calculation**

```powershell
git add sdbr/ddmrp.py sdbr/ddsop_runtime_planning_input.py tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py
git commit -m "feat: qualify operational DDMRP inputs"
```

---

### Task 3: Immutable Evaluation and Recommendation Ledger

**Files:**
- Create: `sdbr/ddmrp_replenishment.py`
- Create: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Consumes: `evaluate_ddmrp_runtime_signals_from_package(...)` output, accepted runtime-package/configuration records, explicit ERP/MRP planning-advice rows, existing recommendation records, and current shared capacity/material ledgers.
- Produces:
  - `DdmrpReplenishmentConflict(ValueError)` with `status = "DdmrpReplenishmentConflict"`.
  - `DdmrpEvaluationWriteSet`.
  - `prepare_ddmrp_evaluation(...) -> DdmrpEvaluationWriteSet`.
  - `apply_ddmrp_evaluation(...) -> Literal["Created", "Duplicate"]`.
  - Stable evaluation/recommendation/event IDs and payload fingerprints.

- [ ] **Step 1: Write failing evaluation/recommendation tests**

Create `tests/test_ddmrp_replenishment.py` with small helpers for one Red, one Yellow, one Green, and one AboveGreen runtime line. The first tests must assert:

```python
def test_evaluation_creates_only_red_and_yellow_recommendations_with_frozen_target():
    write_set = prepare_ddmrp_evaluation(
        evaluation_id="DDE-20260711-001",
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=timezone.utc),
        requested_by="planner-1",
        runtime_result=_runtime_result_with_four_zones(),
        runtime_package=_runtime_package(),
        operating_model_configuration=_configuration(),
        planning_advice_lines=[
            _buy_advice("FG-RED"),
            _make_advice("FG-YELLOW"),
        ],
        existing_recommendations={},
        capacity_reservations={},
        material_allocations={},
    )

    assert [row["PlanningStatus"] for row in write_set.recommendations] == [
        "Red",
        "Yellow",
    ]
    assert [row["AdviceType"] for row in write_set.recommendations] == [
        "Buy",
        "Make",
    ]
    assert all(row["Status"] == "PendingReview" for row in write_set.recommendations)
    assert write_set.evaluation_run["OperatingModelFingerprint"] == "sha256:omc-1"
    assert write_set.evaluation_run["InputFingerprint"].startswith("sha256:")


def test_missing_or_incomplete_planning_evidence_blocks_but_preserves_recommendation():
    write_set = prepare_ddmrp_evaluation(
        evaluation_id="DDE-20260711-002",
        evaluated_at=datetime(2026, 7, 11, 8, tzinfo=timezone.utc),
        requested_by="planner-1",
        runtime_result=_runtime_result_with_red_only(),
        runtime_package=_runtime_package(),
        operating_model_configuration=_configuration(),
        planning_advice_lines=[],
        existing_recommendations={},
        capacity_reservations={},
        material_allocations={},
    )

    recommendation = write_set.recommendations[0]
    assert recommendation["Status"] == "Blocked"
    assert recommendation["AdviceType"] is None
    assert recommendation["BlockingCodes"] == ["PLANNING_ADVICE_MISSING"]
```

Add tests for duplicate advice keys, unsupported `Transfer`, Buy rows containing capacity/material requests, Make rows missing routing/capacity/material, naive times, non-finite quantities/minutes, and a planning-evidence source missing `SourceSystem`, `SourceObjectID`, or `SourceObjectVersion`.

- [ ] **Step 2: Write failing supersession and idempotency tests**

Add tests that apply one evaluation, create a second evaluation for the same item/location, and assert only the prior `PendingReview`/`Blocked` recommendation becomes `Superseded`; a prior `Confirmed` recommendation stays unchanged. Reapplying the exact first write set returns `Duplicate`; reusing its evaluation ID or action key with changed content raises `DdmrpReplenishmentConflict` before any collection changes.

- [ ] **Step 3: Run RED tests**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "evaluation or recommendation or supersed or evidence" --basetemp .tmp/pytest-ddmrp-evaluation-red -p no:cacheprovider
```

Expected: collection fails because `sdbr.ddmrp_replenishment` does not exist.

- [ ] **Step 4: Implement canonical records and validation**

Create `sdbr/ddmrp_replenishment.py` with these public shapes:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping, MutableMapping, MutableSequence, MutableSet


class DdmrpReplenishmentConflict(ValueError):
    status = "DdmrpReplenishmentConflict"


@dataclass(frozen=True, slots=True)
class DdmrpEvaluationWriteSet:
    idempotency_key: str
    payload_fingerprint: str
    evaluation_run: dict[str, object]
    recommendations: tuple[dict[str, object], ...]
    superseded_recommendations: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]
```

Public signatures:

```text
def prepare_ddmrp_evaluation(
    *,
    evaluation_id: str,
    evaluated_at: datetime,
    requested_by: str,
    runtime_result: Mapping[str, object],
    runtime_package: Mapping[str, object],
    operating_model_configuration: Mapping[str, object],
    planning_advice_lines: list[Mapping[str, object]],
    existing_recommendations: Mapping[str, dict[str, object]],
    capacity_reservations: Mapping[str, dict[str, object]],
    material_allocations: Mapping[str, dict[str, object]],
) -> DdmrpEvaluationWriteSet


def apply_ddmrp_evaluation(
    *,
    write_set: DdmrpEvaluationWriteSet,
    evaluation_runs: MutableMapping[str, dict[str, object]],
    recommendations: MutableMapping[str, dict[str, object]],
    events: MutableSequence[dict[str, object]],
    processed_action_keys: MutableSet[str],
) -> Literal["Created", "Duplicate"]
```

Implement those signatures with the validation/build/apply rules below.

The implementation must use canonical JSON (`ensure_ascii=True`, `sort_keys=True`, compact separators) and SHA-256 for all fingerprints/IDs. It must:

- require timezone-aware `evaluated_at`, non-empty IDs/actors/source references, finite positive recommendation quantities, and one unique advice row per item/location;
- accept only `Buy` and `Make`;
- reject any mismatch among package/config `OperatingModelConfigurationID`, `OperatingModelFingerprint`, and `DDMRPConfigurationID`;
- require advice `Uom` to match the runtime line and compute a `PlanningLedgerFingerprint` from active capacity/material rows relevant to the advice resources and component item/locations;
- create recommendation records only when `PlanningStatus in {"Red", "Yellow"}` and `SuggestedReplenishmentQty > 0`;
- copy `StandardTargetReceiptAt` from the evaluated line and freeze the advice row plus `PlanningEvidenceFingerprint` inside the recommendation;
- create a blocked recommendation, not a false success, when an actionable line has missing evidence;
- require Buy evidence to have no routing/capacity/material rows;
- require Make evidence to have `RoutingID`, at least one capacity row, and at least one lower-level material row;
- set `RecommendationID = "DDR-" + sha256(f"{evaluation_id}|{item_id}|{location_id}")[:20]`, `RecommendationVersion=1`, and `Status="PendingReview"` or `"Blocked"`;
- store only immutable outputs/references/fingerprints in the evaluation record, not a mutable pointer to source lists;
- prepare `Superseded` copies with `SupersededByEvaluationID`, `SupersededAt`, and incremented `RecordVersion`; never mutate confirmed rows;
- preflight every target record/event/fingerprint before mutation and add the processed key last.

Use private helpers named `_fingerprint`, `_stable_id`, `_require_aware`, `_normalize_advice_lines`, `_recommendation_from_line`, and `_assert_replay_matches`, each fully covered by public behavior tests.

- [ ] **Step 5: Run evaluation domain tests**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "evaluation or recommendation or supersed or evidence" --basetemp .tmp/pytest-ddmrp-evaluation-green -p no:cacheprovider
```

Expected: all selected tests pass; Green/AboveGreen never appear in `recommendations`; blocked evidence never becomes `PendingReview`.

- [ ] **Step 6: Commit immutable evaluation and advice**

```powershell
git add sdbr/ddmrp_replenishment.py tests/test_ddmrp_replenishment.py
git commit -m "feat: add DDMRP evaluation recommendations"
```

---

### Task 4: Optional Planned Manufacturing Candidate in the Shared Atomic Write Set

**Files:**
- Modify: `sdbr/planning_reservations.py`
- Modify: `tests/test_planning_reservations.py`

**Interfaces:**
- Consumes: existing canonical MTA demand commitment, confirmation identity, capacity/material request rows, and an optional Make candidate request.
- Produces:
  - `PlanningReservationWriteSet.manufacturing_candidate: dict[str, object] | None`.
  - Optional `manufacturing_candidate_request` on `prepare_reservation_confirmation(...)`.
  - Optional `planned_manufacturing_candidates` ledger on `apply_reservation_write_set(...)`.
  - Candidate ID in batch/result/event only for Make; no-candidate payload fingerprints remain byte-for-byte compatible.

- [ ] **Step 1: Write failing candidate construction tests**

Extend the existing `_prepare`/`_apply` helpers only with optional candidate arguments so all old tests keep their current shape. Add:

```python
def test_mta_make_confirmation_builds_candidate_capacity_and_material_as_one_write_set():
    write_set = _prepare(
        manufacturing_candidate_request={
            "RecommendationID": "DDR-1",
            "EvaluationID": "DDE-1",
            "ItemID": "FG-1",
            "LocationID": "MAIN",
            "Quantity": 10,
            "Uom": "EA",
            "RoutingID": "ROUTE-FG-1",
            "StandardTargetReceiptAt": "2026-07-13T08:00:00+00:00",
            "AuthorityBoundary": "SDBRPlanningCandidateOnly",
        },
        capacity_requests=[
            {
                "ReservationLineID": "OP-10",
                "OperationID": "OP-10",
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-11T08:00:00+00:00",
                "WindowEndAt": "2026-07-13T08:00:00+00:00",
                "ReservedMinutes": 120,
                "LatestAllowedCompletionAt": "2026-07-13T08:00:00+00:00",
            }
        ],
        material_requests=[_material_request()],
    )

    candidate = write_set.manufacturing_candidate
    assert candidate is not None
    assert candidate["Status"] == "AwaitingPlanningRun"
    assert candidate["AuthorityBoundary"] == "SDBRPlanningCandidateOnly"
    assert write_set.batch["PlannedManufacturingCandidateID"] == candidate[
        "PlannedManufacturingCandidateID"
    ]
    assert write_set.capacity_reservations[0]["OrderID"] == candidate[
        "PlannedManufacturingCandidateID"
    ]
```

Add tests that a candidate is rejected for non-MTA demand, an incomplete candidate is rejected, capacity request `OrderID` cannot override the generated candidate ID, a candidate target before/other than the demand `RequiredAt` is rejected, and every capacity `LatestAllowedCompletionAt` must be no later than the standard target.

- [ ] **Step 2: Write failing atomic/replay compatibility tests**

Add tests proving:

- candidate/capacity/material/batch/commitment target conflicts leave all seven collections unchanged;
- exact Make replay verifies the persisted candidate immutable content;
- a missing or drifted candidate on replay returns `ReservationLegacyMigrationRequired` or `ReservationConflict` as appropriate;
- old no-candidate `_prepare()` returns `manufacturing_candidate is None`, keeps the current fixture fingerprint exactly `sha256:9d5b69614f983a66d6ee4121ba187a081bdb7286d4b40cc0844fc14d5d301533`, and works when `planned_manufacturing_candidates` is omitted.

- [ ] **Step 3: Run RED tests**

```powershell
pytest tests/test_planning_reservations.py -q -k "manufacturing_candidate or no_candidate" --basetemp .tmp/pytest-make-candidate-red -p no:cacheprovider
```

Expected: FAIL because the write set and prepare/apply functions do not support a candidate.

- [ ] **Step 4: Extend the write set compatibly**

Add the field after existing non-default dataclass fields:

```python
@dataclass(frozen=True, slots=True)
class PlanningReservationWriteSet:
    idempotency_key: str
    payload_fingerprint: str
    demand_commitment: dict[str, object]
    batch: dict[str, object]
    capacity_reservations: tuple[dict[str, object], ...]
    material_allocations: tuple[dict[str, object], ...]
    events: tuple[dict[str, object], ...]
    manufacturing_candidate: dict[str, object] | None = None
```

Add keyword-only parameters with defaults:

```python
manufacturing_candidate_request: Mapping[str, object] | None = None
```

to `prepare_reservation_confirmation`, and:

```python
planned_manufacturing_candidates: MutableMapping[str, dict[str, object]] | None = None
```

to `apply_reservation_write_set`.

When a candidate request is present, require canonical MTA demand identity, derive `PlannedManufacturingCandidateID = _stable_id("PMC", confirmation_id)`, inject that value as every capacity row's `OrderID`, and create:

```python
{
    **validated_request,
    "PlannedManufacturingCandidateID": candidate_id,
    "DemandCommitmentID": demand_id,
    "ReservationBatchID": batch_id,
    "Status": "AwaitingPlanningRun",
    "RecordVersion": 1,
}
```

Add `PlannedManufacturingCandidateID` to the batch/result/event. Include `ManufacturingCandidate` in business fingerprint payload only when non-`None`; this conditional is mandatory so existing no-candidate replay fingerprints remain stable. Extend duplicate-ID preflight, target conflict checks, deep-copy apply, and replay verification before adding the idempotency key.

- [ ] **Step 5: Run shared-foundation regression**

```powershell
pytest tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_planning_run_reservation_bridge.py -q --basetemp .tmp/pytest-make-candidate-green -p no:cacheprovider
```

Expected: all tests pass; every pre-existing no-candidate test remains green.

- [ ] **Step 6: Commit the shared candidate extension**

```powershell
git add sdbr/planning_reservations.py tests/test_planning_reservations.py
git commit -m "feat: add atomic manufacturing candidates"
```

---

### Task 5: Planner Buy/Make Confirmation Orchestration

**Files:**
- Modify: `sdbr/ddmrp_replenishment.py`
- Modify: `tests/test_ddmrp_replenishment.py`

**Interfaces:**
- Consumes: one persisted recommendation, latest evaluation ID for its item/location, existing demand commitments, current shared capacity/material ledgers, and the shared reservation/candidate service from Task 4.
- Produces:
  - `DdmrpConfirmationWriteSet`.
  - `prepare_ddmrp_confirmation(...) -> DdmrpConfirmationWriteSet`.
  - `apply_ddmrp_confirmation(...) -> Literal["Confirmed", "Duplicate"]`.
  - Buy result with no demand/reservation/candidate side effects.
  - Make result with linked demand, candidate, batch, capacity, and material identities.

- [ ] **Step 1: Write failing Buy confirmation tests**

Add tests that a `PendingReview` Buy recommendation becomes `Confirmed` with `ConfirmedAction="Buy"`, actor/time/reason, event, and result IDs; no demand commitment, candidate, batch, capacity reservation, or material allocation is created. Exact replay returns `Duplicate`; a second action or changed payload with the same `ConfirmationID` conflicts.

```python
def test_buy_confirmation_records_decision_without_external_or_reservation_objects():
    confirmation = prepare_ddmrp_confirmation(
        recommendation=_pending_buy_recommendation(),
        latest_evaluation_id="DDE-1",
        confirmation_id="DDC-BUY-1",
        confirmed_action="Buy",
        confirmed_by="planner-1",
        confirmed_at=datetime(2026, 7, 11, 9, tzinfo=timezone.utc),
        reason="补充库存缓冲",
        existing_commitments={},
        capacity_reservations={},
        material_allocations={},
    )
    assert confirmation.reservation_write_set is None
    assert confirmation.updated_recommendation["Status"] == "Confirmed"
    assert confirmation.updated_recommendation["ConfirmedAction"] == "Buy"
```

- [ ] **Step 2: Write failing Make confirmation and atomicity tests**

Add a valid Make test asserting:

```python
def test_make_confirmation_creates_mta_demand_candidate_capacity_and_material_atomically():
    confirmation = prepare_ddmrp_confirmation(
        recommendation=_pending_make_recommendation(),
        latest_evaluation_id="DDE-1",
        confirmation_id="DDC-MAKE-1",
        confirmed_action="Make",
        confirmed_by="planner-1",
        confirmed_at=datetime(2026, 7, 11, 9, tzinfo=timezone.utc),
        reason="恢复黄区库存缓冲",
        existing_commitments={},
        capacity_reservations={},
        material_allocations={},
    )
    reservation = confirmation.reservation_write_set
    assert reservation is not None
    assert reservation.demand_commitment["DemandSourceType"] == "MTAReplenishment"
    assert reservation.demand_commitment["DemandClass"] == "MTA"
    assert reservation.demand_commitment["RequiredAt"] == (
        confirmation.updated_recommendation["StandardTargetReceiptAt"]
    )
    assert reservation.manufacturing_candidate is not None
    assert reservation.capacity_reservations
    assert reservation.material_allocations
```

Apply it to empty ledgers and assert all linked IDs exist. Seed a conflicting candidate/capacity/material record and assert `apply_ddmrp_confirmation` leaves the recommendation, DDMRP events/keys, commitments, batches, candidates, capacities, materials, planning events, and planning keys byte-for-byte unchanged.

- [ ] **Step 3: Write failing stale/fingerprint/domain-gate tests**

Add tests for:

- recommendation `EvaluationID != latest_evaluation_id`;
- `Blocked`, `Superseded`, or already `Confirmed` recommendation;
- `confirmed_action != AdviceType`;
- changed frozen planning evidence that no longer matches `PlanningEvidenceFingerprint`;
- active capacity/material rows whose relevant `PlanningLedgerFingerprint` no longer matches the evaluation snapshot;
- naive confirmation time or blank actor/reason/confirmation ID;
- Make standard target earlier than confirmation time;
- repeated Make confirmation producing no duplicate candidate/reservation/allocation.

Each failure must raise `DdmrpReplenishmentConflict` before any write.

- [ ] **Step 4: Run RED tests**

```powershell
pytest tests/test_ddmrp_replenishment.py -q -k "confirmation or stale or atomic" --basetemp .tmp/pytest-ddmrp-confirm-red -p no:cacheprovider
```

Expected: FAIL because confirmation interfaces are not implemented.

- [ ] **Step 5: Implement the confirmation write set and preflight**

Add:

```python
@dataclass(frozen=True, slots=True)
class DdmrpConfirmationWriteSet:
    idempotency_key: str
    payload_fingerprint: str
    recommendation_id: str
    updated_recommendation: dict[str, object]
    reservation_write_set: PlanningReservationWriteSet | None
    events: tuple[dict[str, object], ...]
```

Public signatures:

```text
def prepare_ddmrp_confirmation(
    *,
    recommendation: Mapping[str, object],
    latest_evaluation_id: str,
    confirmation_id: str,
    confirmed_action: str,
    confirmed_by: str,
    confirmed_at: datetime,
    reason: str,
    existing_commitments: Mapping[str, dict[str, object]],
    capacity_reservations: Mapping[str, dict[str, object]],
    material_allocations: Mapping[str, dict[str, object]],
) -> DdmrpConfirmationWriteSet


def apply_ddmrp_confirmation(
    *,
    write_set: DdmrpConfirmationWriteSet,
    recommendations: MutableMapping[str, dict[str, object]],
    ddmrp_events: MutableSequence[dict[str, object]],
    processed_ddmrp_action_keys: MutableSet[str],
    commitments: MutableMapping[str, dict[str, object]],
    batches: MutableMapping[str, dict[str, object]],
    planned_manufacturing_candidates: MutableMapping[str, dict[str, object]],
    capacity_reservations: MutableMapping[str, dict[str, object]],
    material_allocations: MutableMapping[str, dict[str, object]],
    planning_events: MutableSequence[dict[str, object]],
    processed_planning_event_keys: MutableSet[str],
) -> Literal["Confirmed", "Duplicate"]
```

Implement those signatures using the exact Make/Buy construction and preflight sequence below.

For Make, create a demand with the existing `create_demand_commitment` using:

```python
{
    "demand_source_type": "MTAReplenishment",
    "source_system": "SDBR",
    "source_object_type": "DdmrpReplenishmentRecommendation",
    "source_object_id": recommendation["RecommendationID"],
    "source_object_version": str(recommendation["RecommendationVersion"]),
    "demand_line_id": f"{recommendation['ItemID']}@{recommendation['LocationID']}",
    "item_or_product_id": recommendation["ItemID"],
    "location_id": recommendation["LocationID"],
    "quantity": recommendation["SuggestedReplenishmentQty"],
    "uom": recommendation["Uom"],
    "required_at": datetime.fromisoformat(recommendation["StandardTargetReceiptAt"]),
    "demand_class": "MTA",
    "trace_id": recommendation["TraceID"],
}
```

For Make, recompute the relevant active capacity/material `PlanningLedgerFingerprint` before constructing any write and reject drift with a reevaluation-required conflict. Then pass the recommendation's frozen Make capacity/material evidence and a candidate request to `prepare_reservation_confirmation`. Preflight the DDMRP recommendation/event/replay and every reservation target before applying either domain. Apply the shared write set first only after all remaining DDMRP mutations are guaranteed non-failing; then replace the recommendation, append the DDMRP event, and add the DDMRP processed key last. Exact replay must verify event fingerprint/result and all persisted shared children.

Keep Buy free of demand/reservation/candidate creation and include `ExternalOrderCreated=False` in its event result.

- [ ] **Step 6: Run confirmation and shared regression tests**

```powershell
pytest tests/test_ddmrp_replenishment.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py -q --basetemp .tmp/pytest-ddmrp-confirm-green -p no:cacheprovider
```

Expected: all tests pass; atomic failure tests show no partial objects; Buy has no shared-ledger side effects.

- [ ] **Step 7: Commit confirmation orchestration**

```powershell
git add sdbr/ddmrp_replenishment.py tests/test_ddmrp_replenishment.py
git commit -m "feat: confirm DDMRP Buy and Make advice"
```

---

### Task 6: Persistence and Safe Replenishment Read Model

**Files:**
- Modify: `sdbr/state_store.py`
- Create: `sdbr/ddmrp_replenishment_view.py`
- Modify: `tests/test_state_store.py`
- Create: `tests/test_ddmrp_replenishment_view.py`

**Interfaces:**
- Consumes: evaluation/recommendation/candidate/event ledgers plus shared demand/batch/capacity/material ledgers.
- Produces:
  - Five new state collections and health counts.
  - `build_ddmrp_replenishment_workbench(...) -> dict[str, object]`.
  - A safe read model containing summaries and business rows only.

- [ ] **Step 1: Write failing SQLite round-trip/clear/rollback tests**

Extend `tests/test_state_store.py` to seed and assert equality/health/clear for:

```python
store.ddmrp_evaluation_runs["DDE-1"] = {"EvaluationID": "DDE-1"}
store.ddmrp_replenishment_recommendations["DDR-1"] = {
    "RecommendationID": "DDR-1",
    "Status": "PendingReview",
}
store.planned_manufacturing_candidates["PMC-1"] = {
    "PlannedManufacturingCandidateID": "PMC-1",
    "Status": "AwaitingPlanningRun",
}
store.ddmrp_replenishment_events.append({"EventID": "DRE-1"})
store.processed_ddmrp_action_keys.add("DdmrpEvaluationCreated:DDE-1")
```

Health names must be `DdmrpEvaluationRuns`, `DdmrpReplenishmentRecommendations`, `PlannedManufacturingCandidates`, `DdmrpReplenishmentEvents`, and `ProcessedDdmrpActionKeys`. Add these fields to an existing complete-state rollback test so a simulated save failure restores all five.

- [ ] **Step 2: Write failing safe-view tests**

Create `tests/test_ddmrp_replenishment_view.py`. Seed one latest evaluation with Red Buy, Yellow Make, Green monitor, one confirmed candidate/batch/capacity/material graph, and an older superseded evaluation. Assert:

```python
def test_workbench_returns_latest_business_rows_and_linked_planning_summaries_only():
    result = build_ddmrp_replenishment_workbench(
        evaluation_runs=_evaluations(),
        recommendations=_recommendations(),
        planned_manufacturing_candidates=_candidates(),
        reservation_batches=_batches(),
        capacity_reservations=_capacities(),
        material_allocations=_materials(),
    )

    assert result["Evaluation"]["EvaluationID"] == "DDE-LATEST"
    assert result["Summary"]["PendingReviewCount"] == 1
    assert result["Summary"]["ConfirmedMakeCount"] == 1
    make = next(row for row in result["Rows"] if row["AdviceType"] == "Make")
    assert make["PlanningObjects"] == {
        "PlannedManufacturingCandidateID": "PMC-1",
        "ReservationBatchID": "PRB-1",
        "CapacityReservationCount": 1,
        "MaterialAllocationCount": 1,
    }
    assert "FrozenPlanningEvidence" not in make
    assert "Payload" not in str(result)
```

Add empty-state, blocked-evidence, unknown/orphan link, duplicate identity, copied-output (caller mutation cannot mutate store), and deterministic sort tests.

- [ ] **Step 3: Run RED tests**

```powershell
pytest tests/test_state_store.py tests/test_ddmrp_replenishment_view.py -q -k "ddmrp or manufacturing_candidate" --basetemp .tmp/pytest-ddmrp-store-view-red -p no:cacheprovider
```

Expected: FAIL because the state fields and view module do not exist.

- [ ] **Step 4: Persist all five collections through every store boundary**

Add these dataclass fields to `WorkbenchStateStore`:

```python
ddmrp_evaluation_runs: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_recommendations: dict[str, dict[str, object]] = field(default_factory=dict)
planned_manufacturing_candidates: dict[str, dict[str, object]] = field(default_factory=dict)
ddmrp_replenishment_events: list[dict[str, object]] = field(default_factory=list)
processed_ddmrp_action_keys: set[str] = field(default_factory=set)
```

Add them to `_state_payloads`, `_replace_loaded_state`, `_clear`, and `_state_counts`; serialize the set as a sorted list. Keep `SCHEMA_VERSION = 1` because the relational schema is unchanged and missing JSON keys load as empty collections. The existing dataclass-driven complete snapshot/restore must include them automatically; the new rollback test proves that contract.

- [ ] **Step 5: Implement the safe workbench projection**

Create `sdbr/ddmrp_replenishment_view.py` with:

```text
def build_ddmrp_replenishment_workbench(
    *,
    evaluation_runs: dict[str, dict[str, object]],
    recommendations: dict[str, dict[str, object]],
    planned_manufacturing_candidates: dict[str, dict[str, object]],
    reservation_batches: dict[str, dict[str, object]],
    capacity_reservations: dict[str, dict[str, object]],
    material_allocations: dict[str, dict[str, object]],
) -> dict[str, object]
```

Implement that signature with the selection, validation, copy, and projection rules below.

Select the latest evaluation by parsed timezone-aware `EvaluatedAt`, then stable `EvaluationID`. Return an `Evaluation` object with exactly `EvaluationID`, `EvaluatedAt`, `RuntimePlanningInputPackageID`, `OperatingModelConfigurationID`, `OperatingModelFingerprint`, `DDMRPConfigurationID`, and `Status`; a `Summary` object containing the frozen evaluation summary plus `PendingReviewCount`, `BlockedCount`, `ConfirmedBuyCount`, and `ConfirmedMakeCount`; copied `Rows` and `Issues` lists; and `Boundary="SDBR planning advice only; no ERP order or inventory authority."`.

Each row may expose business quantities/statuses, `StandardTargetReceiptAt`, source summary, blocking codes, and linked object IDs/counts. Put fingerprints/trace IDs under `TechnicalDetails`; never include frozen evidence collections, raw package/config payloads, capacity request rows, or material request rows. Reject malformed duplicate/orphan graph identities instead of silently undercounting.

- [ ] **Step 6: Run persistence/view tests**

```powershell
pytest tests/test_state_store.py tests/test_ddmrp_replenishment_view.py -q --basetemp .tmp/pytest-ddmrp-store-view-green -p no:cacheprovider
```

Expected: all tests pass for memory and SQLite stores; safe view contains no raw payload/evidence keys.

- [ ] **Step 7: Commit persistence and read model**

```powershell
git add sdbr/state_store.py sdbr/ddmrp_replenishment_view.py tests/test_state_store.py tests/test_ddmrp_replenishment_view.py
git commit -m "feat: persist DDMRP replenishment state"
```

---

### Task 7: Operational DDMRP API and Atomic Store Integration

**Files:**
- Modify: `sdbr/api.py`
- Modify: `tests/test_api.py`
- Modify: `docs/backend-specification.md`

**Interfaces:**
- Consumes: stored accepted runtime packages/configurations, Task 3/5 domain write sets, Task 6 state collections/read model, and middleware `If-Match`/whole-state rollback.
- Produces:
  - `POST /planner/workbench/ddmrp/evaluations`.
  - `GET /planner/workbench/ddmrp/workbench`.
  - `POST /planner/workbench/ddmrp/recommendations/{recommendation_id}/confirm`.

- [ ] **Step 1: Write failing evaluation API tests**

In `tests/test_api.py`, add a helper that seeds one accepted runtime package and matching operating-model configuration in `WorkbenchStateStore`. Post:

```python
{
    "EvaluationID": "DDE-API-1",
    "RuntimePlanningInputPackageID": "RPI-1",
    "EvaluatedAt": "2026-07-11T08:00:00+00:00",
    "RequestedBy": "planner-1",
    "PlanningAdviceLines": [
        {
            "ItemID": "FG-1",
            "LocationID": "MAIN",
            "Uom": "EA",
            "AdviceType": "Make",
            "SourceSystem": "ERP-MRP",
            "SourceObjectType": "MaterialPlanningAdvice",
            "SourceObjectID": "MRP-ADV-1",
            "SourceObjectVersion": "1",
            "RoutingID": "ROUTE-FG-1",
            "CapacityRequests": [
                {
                    "ReservationLineID": "OP-10",
                    "OperationID": "OP-10",
                    "ResourceID": "CCR-1",
                    "WindowStartAt": "2026-07-11T08:00:00+00:00",
                    "WindowEndAt": "2026-07-13T08:00:00+00:00",
                    "ReservedMinutes": 120,
                    "LatestAllowedCompletionAt": "2026-07-13T08:00:00+00:00"
                }
            ],
            "MaterialRequests": [
                {
                    "RequirementLineID": "RM-1",
                    "ItemID": "RM-1",
                    "LocationID": "MAIN",
                    "Uom": "EA",
                    "AllocatedQty": 20,
                    "SupplySourceType": "AuthorityAvailable",
                    "MaterialSnapshotID": "MAT-SNAP-1"
                }
            ]
        }
    ]
}
```

Assert 200, immutable evaluation/recommendation persistence, `StandardTargetReceiptAt`, exact frozen configuration references, and a duplicate response for exact replay. Add 404/409 tests for missing package/config, unacceptable package status/execution mode, package/config fingerprint mismatch, changed replay payload, and malformed planning evidence. Every test cites `BE-DDMRP-007`/`008`.

- [ ] **Step 2: Write failing confirmation API tests**

Create one Buy and one Make evaluation through the API, then post:

```python
{
    "ConfirmationID": "DDC-API-MAKE-1",
    "ActionType": "Make",
    "ConfirmedBy": "planner-1",
    "ConfirmedAt": "2026-07-11T09:00:00+00:00",
    "Reason": "恢复黄区库存缓冲"
}
```

Assert the Make response contains recommendation, demand, candidate, batch, capacity IDs, and material IDs; all corresponding store records exist and link exactly. Assert Buy returns `ExternalOrderCreated is False` and creates none of those shared objects. Add exact replay, action mismatch, stale/superseded/blocked recommendation, and unknown recommendation tests.

Create two pending Make recommendations whose evidence touches the same CCR/material scope. Confirm the first, then assert the second returns 409 `reevaluation required` because its frozen `PlanningLedgerFingerprint` no longer matches; verify no second candidate/reservation/allocation appears.

- [ ] **Step 3: Write failing revision/save atomicity and safe-read tests**

Add tests that:

- GET workbench returns `X-Workbench-Revision` and no `Payload`, `FrozenPlanningEvidence`, raw capacity requests, or raw material requests;
- confirmation with a stale `If-Match` returns 409 and leaves every DDMRP/shared collection unchanged;
- monkeypatched `store.save()` failure restores recommendation, demand, candidate, batch, capacity, material, both event ledgers, and both processed-key sets;
- SQLite restart restores a confirmed Make graph and the same workbench summary.

- [ ] **Step 4: Run RED API tests**

```powershell
pytest tests/test_api.py -q -k "ddmrp_evaluation or ddmrp_recommendation or ddmrp_workbench" --basetemp .tmp/pytest-ddmrp-api-red -p no:cacheprovider
```

Expected: FAIL because the new payload models/routes are absent.

- [ ] **Step 5: Add exact Pydantic request models**

Add models near existing DDMRP payloads:

```python
class DdmrpMakeCapacityRequestPayload(BaseModel):
    ReservationLineID: str
    OperationID: str
    ResourceID: str
    WindowStartAt: AwareDatetime
    WindowEndAt: AwareDatetime
    ReservedMinutes: float = Field(gt=0)
    LatestAllowedCompletionAt: AwareDatetime


class DdmrpMaterialPlanningRequestPayload(BaseModel):
    RequirementLineID: str
    ItemID: str
    LocationID: str
    Uom: str
    AllocatedQty: float = Field(gt=0)
    SupplySourceType: str
    MaterialSnapshotID: str
    SupplyReference: str | None = None


class DdmrpPlanningAdvicePayload(BaseModel):
    ItemID: str
    LocationID: str
    Uom: str
    AdviceType: Literal["Buy", "Make"]
    SourceSystem: str
    SourceObjectType: str
    SourceObjectID: str
    SourceObjectVersion: str
    RoutingID: str | None = None
    CapacityRequests: list[DdmrpMakeCapacityRequestPayload] = []
    MaterialRequests: list[DdmrpMaterialPlanningRequestPayload] = []


class DdmrpEvaluationCreatePayload(BaseModel):
    EvaluationID: str
    RuntimePlanningInputPackageID: str
    EvaluatedAt: AwareDatetime
    RequestedBy: str
    PlanningAdviceLines: list[DdmrpPlanningAdvicePayload] = []


class DdmrpRecommendationConfirmPayload(BaseModel):
    ConfirmationID: str
    ActionType: Literal["Buy", "Make"]
    ConfirmedBy: str
    ConfirmedAt: AwareDatetime
    Reason: str
```

Use `Field(default_factory=list)` instead of shared mutable list defaults if required by the local Pydantic version/style.

- [ ] **Step 6: Bind state and implement thin route orchestration**

Bind the five new collections beside current DDMRP/shared collections in `create_app`. The evaluation route must:

1. load the package and its referenced configuration;
2. require `ProcessingStatus="Accepted"`, `PackageStatus="AcceptedForBoundedPlanning"`, and `ExecutionMode in {"DDMRPExecution", "DDMRPAndBoundedScheduling"}`;
3. verify exact configuration IDs/fingerprint;
4. call `evaluate_ddmrp_runtime_signals_from_package`;
5. pass current shared capacity/material ledgers to `prepare_ddmrp_evaluation`, then call `apply_ddmrp_evaluation`;
6. return only evaluation/recommendation IDs, result status, and the safe workbench model.

Convert each `DdmrpPlanningAdvicePayload` with `model_dump(mode="json")` before domain calls so nested aware datetimes become canonical ISO strings expected by `planning_reservations.py`. The confirmation route must find the latest evaluation for the same item/location, pass current shared capacity/material ledgers into the confirmation preflight, prepare/apply the confirmation, and return only safe result IDs plus `ExternalOrderCreated=False`. The GET route calls only `build_ddmrp_replenishment_workbench`. Map unknown IDs to 404 and all domain/reference/revision conflicts to structured 409 responses. Let the existing write middleware own state admission, `If-Match`, save, and complete rollback; do not call `save()` inside these normal route handlers.

- [ ] **Step 7: Run API/domain/store regression**

```powershell
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_ddmrp_replenishment.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_ddmrp_replenishment_view.py tests/test_state_store.py tests/test_api.py -q -k "ddmrp or planning_commitment or planning_reservation or state_store" --basetemp .tmp/pytest-ddmrp-api-green -p no:cacheprovider
python -m compileall -q sdbr
```

Expected: all selected tests pass; the only acceptable warning is the already-known Starlette `TestClient` deprecation if still present.

- [ ] **Step 8: Update backend evidence only after green tests**

Change `BE-DDMRP-007` through `BE-DDMRP-009` to `[VERIFIED]` with exact `C/A/T` files/endpoints and the actual commands/pass counts. Update `BE-SDBR-006` through `BE-SDBR-009` evidence to cite the MTA caller while retaining `[PARTIAL]` for the remaining MTO/external-authority boundaries. Add backend changelog version `2.81` with the verified scope and explicit exclusions.

- [ ] **Step 9: Commit the operational API and backend evidence**

```powershell
git add sdbr/api.py tests/test_api.py docs/backend-specification.md
git commit -m "feat: expose DDMRP replenishment operations"
```

---

### Task 8: UI-DDMRP-003 Materials Planning Confirmation Unit

**Files:**
- Modify: `sdbr/web/planner-workbench.html`
- Modify: `sdbr/web/planner-workbench.js`
- Modify: `sdbr/web/planner-workbench.css`
- Modify: `tests/test_api.py`
- Modify: `docs/ui-specification.md`

**Interfaces:**
- Consumes: `GET /planner/workbench/ddmrp/workbench`, confirmation endpoint, `X-Workbench-Revision`, existing `confirmAction(...)`, shared notifications/status chips, and existing Materials Planning filters/details.
- Produces: `UI-DDMRP-003` implemented and verified as `已验证待用户确认`; no later acceptance unit may start before explicit user response.

- [ ] **Step 1: Write failing UI static-contract tests**

Extend `test_planner_workbench_page_exposes_ddmrp_material_planning_workbench` or add a focused `test_ui_ddmrp_003_exposes_business_confirmation_without_raw_payloads`. Assert HTML has:

```python
assert 'data-material-summary="PendingReviewCount"' in html
assert 'data-material-summary="ConfirmedMakeCount"' in html
assert 'data-i18n="standardTargetReceipt"' in html
assert 'data-i18n="adviceType"' in html
assert 'data-i18n="recommendationStatus"' in html
assert 'id="confirm-material-recommendation"' in html
assert 'id="material-planning-technical-details"' in html
```

Assert JavaScript contains the new workbench/confirm endpoints, `If-Match`, `confirmAction`, revision storage, conflict refresh, and bilingual Buy/Make/candidate/reservation labels. Assert HTML/JS does not contain an ERP order creation button, raw JSON viewer, Buffer Profile editor, substitute/batch fields, `APPROVE ALL`, or automatic confirmation copy.

- [ ] **Step 2: Run RED UI test and syntax check**

```powershell
pytest tests/test_api.py -q -k "ui_ddmrp_003" --basetemp .tmp/pytest-ui-ddmrp-red -p no:cacheprovider
node --check sdbr/web/planner-workbench.js
```

Expected: UI test fails on missing controls; existing JavaScript still parses.

- [ ] **Step 3: Upgrade the existing Materials Planning markup**

Keep the page as the first operational screen, not a marketing/parameter page. Add two compact summary cells for pending review and confirmed Make. Add table columns for standard target, advice type, recommendation status, and action. In the detail panel add:

- evaluation/source freshness and qualified-versus-physical inventory;
- standard target receipt and Buy/Make advice;
- blocking reasons or candidate/batch/capacity/material counts;
- one `button.primary` with `id="confirm-material-recommendation"`;
- one collapsed `<details id="material-planning-technical-details">` containing IDs/fingerprints only.

The confirm button is hidden unless a selected row has `Status="PendingReview"` and `AdviceType in {"Buy", "Make"}`. Blocked, superseded, and confirmed rows display business status without an action.

- [ ] **Step 4: Implement revision-aware load and confirmation**

Replace the Materials Planning fetch path with `/planner/workbench/ddmrp/workbench`. Capture the response header:

```javascript
materialPlanningRevision = response.headers.get("X-Workbench-Revision");
```

Implement:

```javascript
async function confirmMaterialRecommendation() {
  const selected = materialPlanningRows().find(
    (row) => row.RowKey === selectedMaterialPlanningKey
  );
  if (!selected || selected.Status !== "PendingReview") return;
  const accepted = await confirmAction({
    message: translate(
      selected.AdviceType === "Make" ? "confirmMakeAdvice" : "confirmBuyAdvice"
    ),
    context: `${selected.ItemID} · ${selected.LocationID} · ${formatNumber(selected.SuggestedReplenishmentQty)} ${selected.Uom}`,
  });
  if (!accepted) return;

  const headers = { "Content-Type": "application/json" };
  if (materialPlanningRevision) headers["If-Match"] = materialPlanningRevision;
  const response = await fetch(
    `/planner/workbench/ddmrp/recommendations/${encodeURIComponent(selected.RecommendationID)}/confirm`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        ConfirmationID: `DDC-${selected.RecommendationID}-${Date.now()}`,
        ActionType: selected.AdviceType,
        ConfirmedBy: "planner",
        ConfirmedAt: new Date().toISOString(),
        Reason: translate("ddmrpConfirmationReason"),
      }),
    }
  );
  if (!response.ok) {
    await loadMaterialPlanning();
    throw new Error(response.status === 409 ? translate("dataUpdated") : translate("actionFailed"));
  }
  notify(translate("ddmrpAdviceConfirmed"), "success");
  await loadMaterialPlanning();
}
```

Wire the action once during startup. Render from `payload.Rows`; do not reconstruct advice, targets, candidate IDs, or reservation counts in JavaScript. Preserve current search/zone/sort behavior and make row keys use `RecommendationID` when present so repeat evaluations cannot collide.

- [ ] **Step 5: Add compact responsive styling**

Extend existing `.material-*` styles. Keep card radii at the existing token (8px or less), avoid nested cards, and use stable grid/table constraints. At the existing mobile breakpoint, stack summary/action metadata and keep all controls full-width; the table may use its existing horizontal scroll container, but the page itself must have no horizontal overflow. Use existing red/yellow/green/status colors and no new purple, beige/tan, dark-blue/slate, or brown/orange theme.

- [ ] **Step 6: Run UI/API focused tests**

```powershell
node --check sdbr/web/planner-workbench.js
pytest tests/test_api.py tests/test_ddmrp_replenishment_view.py -q -k "ui_ddmrp_003 or ddmrp_workbench or ddmrp_recommendation" --basetemp .tmp/pytest-ui-ddmrp-green -p no:cacheprovider
```

Expected: JavaScript parses and all selected tests pass.

- [ ] **Step 7: Perform browser acceptance verification**

Start the app on an unused local port:

```powershell
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8000
```

Use the in-app browser with seeded test state to verify at 1280x720 and 390x844:

1. latest evaluation/source/target/status are visible without raw payloads;
2. search, zone filter, sort, row selection, and details still work;
3. Buy confirmation dialog explains that no external order is created;
4. Make confirmation creates and then displays candidate/batch/capacity/material summaries;
5. stale `If-Match` produces a clear refresh message and no partial visual state;
6. blocked/superseded/confirmed rows have no active confirm button;
7. Chinese/English switching, keyboard focus, dialog close/cancel, loading, empty, and error states work;
8. no overlap, clipping, page-level horizontal overflow, or layout shift occurs.

Capture desktop and mobile screenshots in the implementation report/evidence location used by the executing worker; do not add binary screenshots to Git unless explicitly requested.

- [ ] **Step 8: Run full verification**

```powershell
python -m compileall -q sdbr
node --check sdbr/web/planner-workbench.js
pytest tests/test_ddmrp.py tests/test_ddsop_runtime_planning_input.py tests/test_ddmrp_replenishment.py tests/test_planning_commitments.py tests/test_planning_reservations.py tests/test_planning_reservation_view.py tests/test_ddmrp_replenishment_view.py tests/test_state_store.py tests/test_api.py -q --basetemp .tmp/pytest-ddmrp-closure-focused -p no:cacheprovider
pytest -q --basetemp .tmp/pytest-ddmrp-closure-full -p no:cacheprovider
git diff --check
```

Expected: compile and Node checks exit 0; focused and full suites pass; any warning is recorded exactly and does not hide a failure.

- [ ] **Step 9: Update UI acceptance evidence without claiming user confirmation**

Change `UI-DDMRP-003` to `已验证待用户确认`. Add the exact implementation files, API dependencies, test commands/pass counts, desktop/mobile browser evidence, and these remaining boundaries: no DDAE parameter governance, no Transfer, no substitutes/batches, no ERP purchase/production order, no supplier execution, no inventory/quality authority, and no automatic external delivery. Add UI changelog `5.36`. Do not write `用户已确认`.

- [ ] **Step 10: Commit the UI acceptance unit**

```powershell
git add sdbr/web/planner-workbench.html sdbr/web/planner-workbench.js sdbr/web/planner-workbench.css tests/test_api.py docs/ui-specification.md
git commit -m "feat: add DDMRP replenishment workbench"
```

- [ ] **Step 11: Stop at the mandatory confirmation gate**

Report `UI-DDMRP-003`, exact tests, browser URL/evidence, and commit. Ask the user to confirm the acceptance unit. Do not start another UI unit or mark this one `用户已确认` until the user explicitly responds.

---

## Execution Checkpoints

1. After Task 2, confirm the accepted runtime package is still the source of DDAE parameters and runtime facts; no DDAE schema or payload builder changed.
2. After Task 3, review immutable IDs/fingerprints, Red/Yellow-only advice, blocked evidence, and supersession before confirmation depends on them.
3. After Task 4, review no-candidate fingerprint compatibility and candidate/capacity/material preflight before wiring the MTA caller.
4. After Task 5, review Buy's zero side effects and Make's all-or-nothing graph before persistence/API work.
5. After Task 7, verify stale `If-Match`, SQLite save conflicts, and domain conflicts leave no partial recommendation/reservation state.
6. Task 8 is the final acceptance unit. Stop for explicit user confirmation after it passes.

## Requirements Traceability

| Agreed requirement | Plan coverage |
| --- | --- |
| Consume frozen DDAE parameters; no profile configuration | Tasks 1, 2, 7; `BE-DDMRP-007`; Global Constraints |
| Qualified demand/net flow/stock execution state | Task 2; existing `BE-DDMRP-003`/`004`; new contract-backed tests |
| Red/Yellow replenishment only | Tasks 2 and 3; Green/AboveGreen zero/advice exclusion tests |
| Planner confirms Buy/Make | Tasks 5, 7, 8; `BE-DDMRP-008`; `UI-DDMRP-003` |
| Confirmed Make creates candidate, CCR reservation, lower-level allocations immediately | Tasks 4 and 5; `BE-DDMRP-009`; atomic failure/replay tests |
| Standard target equals evaluation time plus frozen DLT | Tasks 2 and 3; explicit timestamp assertion |
| ERP/MRP remains production/supplier authority; ERP/WMS/QMS inventory/quality authority | Global Constraints, Tasks 1, 2, 3, 8; safe boundary strings |
| No DDAE fields, substitute/batch rules, production PO, or automatic external order | Global Constraints, spec rows, API/UI negative assertions, final acceptance evidence |

## Explicit Deferred Work

- Transfer recommendation and transfer-order governance.
- BOM explosion, substitute materials, batch/lot/expiry, split/merge, and source-selection governance.
- Make candidate conversion into a formal ERP production order or automatic Planning Run order.
- Buy recommendation conversion into a purchase order, supplier dispatch, delivery promise, ACK, retry, or dead-letter flow.
- ERP/WMS formal allocation handoff, QMS quality mutation, receipt/issue/completion feedback, and automatic event reevaluation.
- Earliest-feasible completion simulation, automatic schedule changes, release authorization, MES dispatch, or Simio validation from a replenishment recommendation.
